"""
Servicio de Analista: traduce preguntas en lenguaje natural a SQL
y genera respuestas narrativas usando Google Gemini API.
"""
import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from google import genai
from google.genai import types
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)

DB_SCHEMA = """
Base de datos PostgreSQL de una empresa de ventas/retail (moneda COP - pesos colombianos).

Tablas disponibles:

1. reportes_ventas_30dias — Ventas de los últimos 30 días (una fila por línea de venta)
   Columnas:
   - nombre TEXT           -- nombre del producto
   - precio NUMERIC        -- precio unitario de venta
   - cantidad INTEGER      -- unidades vendidas en esta transacción
   - fecha_venta DATE      -- fecha de la venta
   - total_venta NUMERIC   -- precio * cantidad (total de la línea)
   - vendedor TEXT         -- nombre del vendedor
   - familia TEXT          -- categoría/familia del producto
   - metodo TEXT           -- método de pago (Efectivo, Tarjeta, etc.)
   - proveedor_moda TEXT   -- proveedor principal del producto
   - precio_promedio_compra NUMERIC -- costo promedio de compra del producto
   - margen NUMERIC        -- margen por unidad (precio - precio_promedio_compra)
   - margen_porcentaje NUMERIC -- porcentaje de margen sobre precio de venta

2. items — Inventario actual de productos
   Columnas:
   - nombre TEXT           -- nombre del producto
   - cantidad_disponible INTEGER -- stock actual en unidades
   - familia TEXT          -- categoría/familia del producto
   - precio NUMERIC        -- precio de venta actual

3. facturas — Historial de ventas de los últimos 40 meses (una fila por línea de factura)
   Columnas:
   - nombre TEXT           -- nombre del producto
   - fecha DATE            -- fecha de la factura
   - cantidad INTEGER      -- unidades vendidas
   - precio NUMERIC        -- precio unitario

4. facturas_proveedor — Facturas de compra a proveedores
   Columnas:
   - nombre TEXT           -- nombre del producto
   - proveedor TEXT        -- nombre del proveedor
   - precio NUMERIC        -- precio de compra unitario
   - fecha DATE            -- fecha de la factura del proveedor
"""

SYSTEM_PROMPT_SQL = f"""Eres un analista de datos experto en SQL PostgreSQL.
Tu tarea es generar UNA SOLA consulta SQL SELECT basada en la pregunta del usuario.

{DB_SCHEMA}

REGLAS ESTRICTAS:
1. SOLO puedes generar sentencias SELECT. Nunca INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, ni ningún DDL/DML.
2. No uses subconsultas correlacionadas innecesarias. Prefiere JOINs y CTEs.
3. Incluye LIMIT si el resultado puede ser grande (máximo 100 filas).
4. Usa alias descriptivos en español para las columnas.
5. Si la pregunta no se puede responder con las tablas disponibles, responde SOLO con: NO_SQL_POSSIBLE
6. Los valores de texto en WHERE deben usar ILIKE para búsqueda insensible a mayúsculas.
7. Para fechas relativas como "esta semana", "este mes", usa CURRENT_DATE y funciones de PostgreSQL.
8. Responde SOLO con el SQL, sin explicación, sin markdown, sin bloques de código."""

SYSTEM_PROMPT_ANSWER = """Eres un analista de negocios experto que responde preguntas sobre datos de ventas.
Responde en español, de forma clara y concisa. Usa formato Markdown cuando sea útil (negritas, listas, tablas).
Si los datos incluyen valores numéricos monetarios, formatea como pesos colombianos (COP) con separador de miles.
No inventes datos que no estén en los resultados proporcionados.
Si los resultados están vacíos, indica que no se encontraron datos para esa consulta.
Sé conversacional pero profesional. Incluye insights o sugerencias cuando sea relevante."""

MAX_ROWS = 100
MAX_CONVERSATION_HISTORY = 6


class AnalistaService:
    """Servicio para el analista de datos con IA."""

    def __init__(self, db: AsyncSession):
        self.db = db
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def ask(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Procesa una pregunta del usuario:
        1. Genera SQL con Gemini
        2. Ejecuta la query (solo SELECT)
        3. Genera respuesta narrativa con Gemini
        """
        sql_query = self._generate_sql(question, conversation_history)

        if sql_query == "NO_SQL_POSSIBLE":
            return {
                "respuesta": "Lo siento, no puedo responder esa pregunta con los datos disponibles en la base de datos.",
                "sql": None,
                "datos": None,
                "error": None,
            }

        self._validate_sql(sql_query)
        sql_query = self._enforce_limit(sql_query)

        rows, columns = await self._execute_query(sql_query)

        answer = self._generate_answer(question, sql_query, rows, columns)

        data = [dict(zip(columns, row)) for row in rows] if rows else None

        return {
            "respuesta": answer,
            "sql": sql_query,
            "datos": data,
            "error": None,
        }

    def _generate_sql(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Genera SQL a partir de la pregunta usando Gemini."""
        contents = []

        if conversation_history:
            for msg in conversation_history[-MAX_CONVERSATION_HISTORY:]:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg["content"])],
                    )
                )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=question)],
            )
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_SQL,
                temperature=0.0,
            ),
        )

        sql = response.text.strip()
        sql = re.sub(r"^```(?:sql)?\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()

    def _validate_sql(self, sql: str) -> None:
        """Valida que el SQL sea una consulta SELECT segura."""
        normalized = sql.upper().strip()

        if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
            raise ValueError("Solo se permiten consultas SELECT.")

        forbidden = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
            "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
            "COPY", "\\COPY", "pg_", "information_schema",
        ]
        for keyword in forbidden:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, normalized):
                raise ValueError(
                    f"Consulta no permitida: contiene '{keyword}'."
                )

    def _enforce_limit(self, sql: str) -> str:
        """Asegura que la query tenga LIMIT."""
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";")
            sql += f" LIMIT {MAX_ROWS}"
        return sql

    async def _execute_query(self, sql: str) -> Tuple[List[tuple], List[str]]:
        """Ejecuta una consulta SQL de solo lectura."""
        result = await self.db.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchall()
        return rows, columns

    def _generate_answer(
        self,
        question: str,
        sql: str,
        rows: List[tuple],
        columns: List[str],
    ) -> str:
        """Genera una respuesta en lenguaje natural a partir de los resultados."""
        if not rows:
            data_summary = "La consulta no devolvió resultados."
        else:
            data_dicts = [dict(zip(columns, row)) for row in rows[:50]]
            data_summary = json.dumps(data_dicts, default=str, ensure_ascii=False)

        user_message = (
            f"Pregunta del usuario: {question}\n\n"
            f"SQL ejecutado: {sql}\n\n"
            f"Resultados ({len(rows)} filas):\n{data_summary}"
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_ANSWER,
                temperature=0.3,
            ),
        )

        return response.text

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

=== TABLAS ===

1. reportes_ventas_30dias — Ventas de los últimos 30 días (una fila por línea de venta)
   - nombre TEXT              -- nombre del producto (PK lógica junto con fecha_venta)
   - precio NUMERIC           -- precio unitario de venta
   - cantidad INTEGER         -- unidades vendidas en esta transacción
   - fecha_venta DATE         -- fecha de la venta
   - total_venta NUMERIC      -- precio * cantidad
   - vendedor TEXT            -- nombre del vendedor
   - familia TEXT             -- categoría/familia del producto
   - metodo TEXT              -- método de pago (Efectivo, Tarjeta, Transferencia, etc.)
   - proveedor_moda TEXT      -- proveedor principal (el más frecuente) del producto
   - precio_promedio_compra NUMERIC -- costo promedio de compra al proveedor
   - margen NUMERIC           -- ganancia por unidad = precio - precio_promedio_compra
   - margen_porcentaje NUMERIC -- % de margen = (margen / precio) * 100

2. items — Inventario actual (una fila por producto)
   - nombre TEXT              -- nombre del producto (PK lógica, une con las demás tablas)
   - cantidad_disponible INTEGER -- stock actual en unidades
   - familia TEXT             -- categoría/familia
   - precio NUMERIC           -- precio de venta actual

3. facturas — Historial de ventas ~40 meses (una fila por línea de factura)
   - nombre TEXT              -- nombre del producto
   - fecha DATE               -- fecha de la factura
   - cantidad INTEGER         -- unidades vendidas
   - precio NUMERIC           -- precio unitario de venta

4. facturas_proveedor — Historial de compras a proveedores
   - nombre TEXT              -- nombre del producto
   - proveedor TEXT           -- nombre del proveedor (ej: JALTECH, INTCOMEX, etc.)
   - precio NUMERIC           -- precio de compra unitario
   - fecha DATE               -- fecha de la compra

=== RELACIONES ENTRE TABLAS ===

- La columna "nombre" es la clave de unión entre TODAS las tablas.
  items.nombre = reportes_ventas_30dias.nombre = facturas.nombre = facturas_proveedor.nombre
- reportes_ventas_30dias.proveedor_moda corresponde a facturas_proveedor.proveedor (proveedor principal de cada producto).
- Para saber qué productos suministra un proveedor, consulta facturas_proveedor filtrando por proveedor.
- Para cruzar stock actual con ventas, une items con reportes_ventas_30dias por nombre.

=== FÓRMULAS DE NEGOCIO ===

1. VELOCIDAD DE VENTA DIARIA de un producto (últimos 30 días):
   SUM(rv.cantidad)::numeric / GREATEST(COUNT(DISTINCT rv.fecha_venta), 1)
   desde reportes_ventas_30dias rv

2. DÍAS DE STOCK (cobertura):
   items.cantidad_disponible / NULLIF(velocidad_diaria, 0)

3. CLASIFICACIÓN DE URGENCIA DE COMPRA (por días de stock):
   - dias_stock <= 7   → 'URGENTE'
   - dias_stock <= 14  → 'ALTA'
   - dias_stock <= 30  → 'MEDIA'
   - dias_stock > 30   → 'OK'

4. CANTIDAD SUGERIDA DE COMPRA:
   GREATEST(0, ROUND(velocidad_diaria * cobertura_objetivo) - stock_actual)
   Cobertura objetivo por clasificación ABC:
   - Clase A (80% del valor de ventas acumulado): 45 días
   - Clase B (80%-95%): 30 días
   - Clase C (>95%): 21 días
   Simplificación: usar 30 días como cobertura genérica si no se necesita ABC.

5. MARGEN DE UN PRODUCTO:
   precio_venta - precio_promedio_compra (columnas ya en reportes_ventas_30dias)

6. ÚLTIMO PRECIO DE COMPRA a un proveedor:
   SELECT DISTINCT ON (nombre, proveedor) nombre, proveedor, precio, fecha
   FROM facturas_proveedor ORDER BY nombre, proveedor, fecha DESC

7. ESTADO DE STOCK:
   - dias_stock <= 3  → 'Crítico'
   - dias_stock <= 7  → 'Bajo'
   - dias_stock <= 60 → 'Normal'
   - dias_stock > 60  → 'Exceso'

8. TENDENCIA (comparar últimos 3 meses vs 3 anteriores):
   ratio = promedio_reciente / promedio_anterior
   - ratio > 1.2 → 'Creciente'
   - ratio < 0.8 → 'Decreciente'
   - else        → 'Estable'
"""

SYSTEM_PROMPT_SQL = f"""Eres un analista de datos experto en SQL PostgreSQL para una empresa de retail/ventas.
Tu trabajo: generar UNA SOLA consulta SQL SELECT que responda la pregunta del usuario.

{DB_SCHEMA}

=== EJEMPLOS DE QUERIES COMPLEJAS ===

PREGUNTA: "¿Qué debo comprarle a [PROVEEDOR]?"
QUERY:
WITH productos_proveedor AS (
  SELECT DISTINCT ON (fp.nombre)
    fp.nombre, fp.precio AS precio_compra, fp.fecha AS ultima_compra
  FROM facturas_proveedor fp
  WHERE fp.proveedor ILIKE '%PROVEEDOR%'
  ORDER BY fp.nombre, fp.fecha DESC
),
velocidad AS (
  SELECT rv.nombre,
    SUM(rv.cantidad)::numeric / GREATEST(COUNT(DISTINCT rv.fecha_venta), 1) AS venta_diaria
  FROM reportes_ventas_30dias rv
  GROUP BY rv.nombre
),
stock AS (
  SELECT nombre, cantidad_disponible FROM items
)
SELECT
  pp.nombre AS producto,
  COALESCE(s.cantidad_disponible, 0) AS stock_actual,
  COALESCE(ROUND(v.venta_diaria, 2), 0) AS venta_diaria,
  CASE WHEN v.venta_diaria > 0 THEN ROUND(COALESCE(s.cantidad_disponible, 0) / v.venta_diaria, 1) ELSE NULL END AS dias_stock,
  CASE
    WHEN v.venta_diaria > 0 AND COALESCE(s.cantidad_disponible, 0) / v.venta_diaria <= 7 THEN 'URGENTE'
    WHEN v.venta_diaria > 0 AND COALESCE(s.cantidad_disponible, 0) / v.venta_diaria <= 14 THEN 'ALTA'
    WHEN v.venta_diaria > 0 AND COALESCE(s.cantidad_disponible, 0) / v.venta_diaria <= 30 THEN 'MEDIA'
    ELSE 'OK'
  END AS urgencia,
  GREATEST(0, ROUND(COALESCE(v.venta_diaria, 0) * 30) - COALESCE(s.cantidad_disponible, 0)) AS cantidad_sugerida,
  pp.precio_compra AS ultimo_precio_compra,
  ROUND(GREATEST(0, COALESCE(v.venta_diaria, 0) * 30 - COALESCE(s.cantidad_disponible, 0)) * pp.precio_compra) AS inversion_estimada
FROM productos_proveedor pp
LEFT JOIN velocidad v ON v.nombre = pp.nombre
LEFT JOIN stock s ON s.nombre = pp.nombre
WHERE COALESCE(v.venta_diaria, 0) > 0
ORDER BY
  CASE
    WHEN v.venta_diaria > 0 AND COALESCE(s.cantidad_disponible, 0) / v.venta_diaria <= 7 THEN 1
    WHEN v.venta_diaria > 0 AND COALESCE(s.cantidad_disponible, 0) / v.venta_diaria <= 14 THEN 2
    WHEN v.venta_diaria > 0 AND COALESCE(s.cantidad_disponible, 0) / v.venta_diaria <= 30 THEN 3
    ELSE 4
  END,
  v.venta_diaria DESC
LIMIT 100

PREGUNTA: "¿Qué productos están en riesgo de agotarse?"
QUERY:
WITH velocidad AS (
  SELECT rv.nombre,
    SUM(rv.cantidad)::numeric / GREATEST(COUNT(DISTINCT rv.fecha_venta), 1) AS venta_diaria
  FROM reportes_ventas_30dias rv
  GROUP BY rv.nombre
)
SELECT
  i.nombre AS producto,
  i.cantidad_disponible AS stock_actual,
  ROUND(v.venta_diaria, 2) AS venta_diaria,
  ROUND(i.cantidad_disponible / NULLIF(v.venta_diaria, 0), 1) AS dias_stock,
  CASE
    WHEN i.cantidad_disponible / NULLIF(v.venta_diaria, 0) <= 3 THEN 'CRITICO'
    WHEN i.cantidad_disponible / NULLIF(v.venta_diaria, 0) <= 7 THEN 'BAJO'
    ELSE 'NORMAL'
  END AS estado,
  i.familia
FROM items i
JOIN velocidad v ON v.nombre = i.nombre
WHERE v.venta_diaria > 0
  AND i.cantidad_disponible / NULLIF(v.venta_diaria, 0) <= 14
ORDER BY i.cantidad_disponible / NULLIF(v.venta_diaria, 0) ASC
LIMIT 50

PREGUNTA: "¿Qué proveedor tiene mejor precio para [PRODUCTO]?"
QUERY:
SELECT DISTINCT ON (fp.proveedor)
  fp.proveedor, fp.precio AS precio_compra, fp.fecha AS ultima_fecha
FROM facturas_proveedor fp
WHERE fp.nombre ILIKE '%PRODUCTO%'
ORDER BY fp.proveedor, fp.fecha DESC

PREGUNTA: "¿Cómo van las ventas por mes este año?"
QUERY:
SELECT
  EXTRACT(MONTH FROM f.fecha)::int AS mes,
  TO_CHAR(DATE_TRUNC('month', f.fecha), 'Mon YYYY') AS periodo,
  SUM(f.cantidad) AS unidades,
  ROUND(SUM(f.precio * f.cantidad)) AS total_ventas
FROM facturas f
WHERE f.fecha >= DATE_TRUNC('year', CURRENT_DATE)
GROUP BY EXTRACT(MONTH FROM f.fecha), DATE_TRUNC('month', f.fecha)
ORDER BY mes

=== REGLAS ===
1. SOLO sentencias SELECT. Nunca INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE.
2. Usa CTEs (WITH) para queries complejas con múltiples tablas.
3. Usa ILIKE para comparaciones de texto. Usa NULLIF(x, 0) para evitar division por cero.
4. Incluye LIMIT (máximo 100) si el resultado puede ser grande.
5. Usa alias descriptivos en español.
6. Si la pregunta no se puede responder, responde SOLO: NO_SQL_POSSIBLE
7. Para fechas relativas usa CURRENT_DATE y funciones de PostgreSQL.
8. Responde SOLO con el SQL, sin explicación, sin markdown, sin bloques de código.
9. Une tablas siempre por la columna "nombre" (nombre del producto).
10. Usa COALESCE para manejar NULLs en JOINs. Usa GREATEST(x, 0) para cantidades negativas."""

SYSTEM_PROMPT_ANSWER = """Eres un analista de negocios experto de una empresa de retail colombiana.
Respondes preguntas sobre ventas, inventario, proveedores, márgenes y compras.

REGLAS:
- Responde en español, claro y conciso. Usa Markdown: **negritas**, listas, tablas cuando ayuden.
- Valores monetarios en COP con separador de miles (ej: $1.250.000).
- No inventes datos que no estén en los resultados. Si están vacíos, dilo.
- Sé conversacional pero profesional.
- Incluye insights, alertas o recomendaciones accionables cuando los datos lo sugieran.
- Si ves urgencias de compra, destaca los productos críticos.
- Si ves márgenes negativos, alerta sobre ellos.
- Cuando sea una lista de compras, organiza por urgencia y sugiere un plan de acción."""

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

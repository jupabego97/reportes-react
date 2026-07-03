"""
Servicio de inventario perpetuo (Fase 1).

Principio: el stock no es un número que alguien escribe, es la suma de un
libro de movimientos auditables. Todo cambio de inventario pasa por
`movimientos_inventario`; los conteos cíclicos miden qué tan confiable es
el libro (exactitud) y generan el ajuste correspondiente.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica

TIPOS_MOVIMIENTO = {
    "venta",
    "compra",
    "ajuste_conteo",
    "merma",
    "devolucion",
    "transferencia_in",
    "transferencia_out",
    "carga_inicial",
}


class InventarioPerpetuoService:
    """Libro de inventario perpetuo, conteos cíclicos y exactitud."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --------------------------------------------------------------- utilidades

    async def _producto_id(self, nombre: str) -> Optional[int]:
        result = await self.db.execute(
            text("SELECT id FROM productos WHERE nombre = :n"),
            {"n": semantica.normalizar_nombre(nombre)},
        )
        row = result.fetchone()
        return int(row[0]) if row else None

    async def _tienda_id_default(self) -> int:
        result = await self.db.execute(
            text("SELECT id FROM tiendas WHERE activa ORDER BY id LIMIT 1")
        )
        row = result.fetchone()
        if not row:
            raise ValueError("No hay tiendas activas registradas")
        return int(row[0])

    # ------------------------------------------------------------ carga inicial

    async def cargar_stock_inicial(self) -> Dict[str, Any]:
        """Crea movimientos `carga_inicial` desde items.cantidad_disponible.

        Solo para productos sin ningún movimiento previo: es el punto de
        partida del libro, no un mecanismo de corrección (para eso están
        los conteos).
        """
        tienda_id = await self._tienda_id_default()
        query = """
            INSERT INTO movimientos_inventario
                (producto_id, tienda_id, tipo, cantidad, costo_unitario, referencia)
            SELECT
                p.id,
                :tienda_id,
                'carga_inicial',
                COALESCE(i.cantidad_disponible, 0),
                p.costo_unitario,
                'carga inicial desde items'
            FROM productos p
            JOIN items i ON UPPER(TRIM(i.nombre)) = p.nombre
            WHERE COALESCE(i.cantidad_disponible, 0) <> 0
              AND NOT EXISTS (
                  SELECT 1 FROM movimientos_inventario m WHERE m.producto_id = p.id
              )
        """
        result = await self.db.execute(text(query), {"tienda_id": tienda_id})
        await self.db.commit()
        return {"movimientos_creados": result.rowcount}

    # ----------------------------------------------------------- movimientos

    async def registrar_movimiento(
        self,
        nombre_producto: str,
        tipo: str,
        cantidad: float,
        costo_unitario: Optional[float] = None,
        referencia: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra un movimiento en el libro. Cantidad con signo:
        positiva entra stock (compra, devolución), negativa sale (venta, merma)."""
        if tipo not in TIPOS_MOVIMIENTO:
            raise ValueError(f"Tipo de movimiento inválido: {tipo}")

        producto_id = await self._producto_id(nombre_producto)
        if producto_id is None:
            raise ValueError(f"Producto no existe en el maestro: {nombre_producto}")

        tienda_id = await self._tienda_id_default()
        await self.db.execute(
            text(
                """
                INSERT INTO movimientos_inventario
                    (producto_id, tienda_id, tipo, cantidad, costo_unitario, referencia, usuario)
                VALUES (:p, :t, :tipo, :cant, :costo, :ref, :usr)
                """
            ),
            {
                "p": producto_id,
                "t": tienda_id,
                "tipo": tipo,
                "cant": cantidad,
                "costo": costo_unitario,
                "ref": referencia,
                "usr": usuario,
            },
        )
        await self.db.commit()
        stock = await self.get_stock_perpetuo(nombre_producto)
        return {"producto_id": producto_id, "stock_perpetuo": stock}

    async def get_stock_perpetuo(self, nombre_producto: str) -> Optional[float]:
        """Stock según el libro = suma de todos los movimientos."""
        producto_id = await self._producto_id(nombre_producto)
        if producto_id is None:
            return None
        result = await self.db.execute(
            text(
                "SELECT COALESCE(SUM(cantidad), 0) FROM movimientos_inventario WHERE producto_id = :p"
            ),
            {"p": producto_id},
        )
        return float(result.scalar() or 0)

    # -------------------------------------------------------------- conteos

    async def registrar_conteo(
        self,
        nombre_producto: str,
        stock_fisico: float,
        usuario: Optional[str] = None,
        motivo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra un conteo físico, evalúa exactitud y ajusta el libro.

        El stock del sistema que se congela es el perpetuo (el libro), y si
        el libro está vacío para el producto, el de items como respaldo.
        """
        producto_id = await self._producto_id(nombre_producto)
        if producto_id is None:
            raise ValueError(f"Producto no existe en el maestro: {nombre_producto}")

        stock_sistema = await self.get_stock_perpetuo(nombre_producto) or 0.0

        result = await self.db.execute(
            text("SELECT costo_unitario FROM productos WHERE id = :p"), {"p": producto_id}
        )
        row = result.fetchone()
        costo = float(row[0]) if row and row[0] is not None else None

        diferencia = float(stock_fisico) - stock_sistema
        es_exacto = semantica.conteo_es_exacto(stock_sistema, stock_fisico)
        valor_diferencia = semantica.merma_valor(stock_sistema, stock_fisico, costo)

        tienda_id = await self._tienda_id_default()
        await self.db.execute(
            text(
                """
                INSERT INTO conteos_ciclicos
                    (producto_id, tienda_id, stock_sistema, stock_fisico,
                     diferencia, valor_diferencia, es_exacto, motivo, usuario)
                VALUES (:p, :t, :sist, :fis, :dif, :val, :ex, :motivo, :usr)
                """
            ),
            {
                "p": producto_id,
                "t": tienda_id,
                "sist": stock_sistema,
                "fis": stock_fisico,
                "dif": diferencia,
                "val": valor_diferencia,
                "ex": es_exacto,
                "motivo": motivo,
                "usr": usuario,
            },
        )

        # El conteo físico manda: el libro se ajusta a la realidad
        if diferencia != 0:
            await self.db.execute(
                text(
                    """
                    INSERT INTO movimientos_inventario
                        (producto_id, tienda_id, tipo, cantidad, costo_unitario, referencia, usuario)
                    VALUES (:p, :t, 'ajuste_conteo', :cant, :costo, 'ajuste por conteo cíclico', :usr)
                    """
                ),
                {"p": producto_id, "t": tienda_id, "cant": diferencia, "costo": costo, "usr": usuario},
            )

        await self.db.commit()
        return {
            "producto": semantica.normalizar_nombre(nombre_producto),
            "stock_sistema": stock_sistema,
            "stock_fisico": float(stock_fisico),
            "diferencia": diferencia,
            "valor_diferencia": valor_diferencia,
            "es_exacto": es_exacto,
        }

    async def get_exactitud(self, dias: int = 30) -> Dict[str, Any]:
        """Exactitud de inventario de los últimos N días.

        World-class: > 97%. Bajo 95% NO se automatiza el reabastecimiento
        (regla de la Fase 1).
        """
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        result = await self.db.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE es_exacto) as exactos,
                    COALESCE(SUM(ABS(valor_diferencia)), 0) as valor_discrepancia
                FROM conteos_ciclicos
                WHERE fecha >= :desde
                """
            ),
            {"desde": desde},
        )
        row = result.fetchone()
        total = int(row[0] or 0)
        exactos = int(row[1] or 0)
        exactitud = semantica.exactitud_inventario(exactos, total)
        return {
            "dias_ventana": dias,
            "conteos_totales": total,
            "conteos_exactos": exactos,
            "exactitud_pct": round(exactitud, 1) if exactitud is not None else None,
            "valor_discrepancia_absoluta": float(row[2] or 0),
            "apto_para_automatizar": exactitud is not None and exactitud >= 95.0,
        }

    async def get_plan_conteos(self, limite: int = 20) -> List[Dict[str, Any]]:
        """Conteos dirigidos del día, priorizados por riesgo (no calendario ciego).

        Score = valor de inventario × (1 + discrepancia histórica) × antigüedad
        del último conteo — definido en la capa semántica.
        """
        query = """
            WITH stock AS (
                SELECT producto_id, COALESCE(SUM(cantidad), 0) as stock_perpetuo
                FROM movimientos_inventario
                GROUP BY producto_id
            ),
            historial AS (
                SELECT
                    producto_id,
                    MAX(fecha) as ultimo_conteo,
                    AVG(
                        CASE WHEN stock_sistema <> 0
                             THEN ABS(diferencia) / ABS(stock_sistema) * 100
                             ELSE 0 END
                    ) as discrepancia_hist_pct
                FROM conteos_ciclicos
                GROUP BY producto_id
            )
            SELECT
                p.nombre,
                s.stock_perpetuo,
                p.costo_unitario,
                h.ultimo_conteo,
                COALESCE(h.discrepancia_hist_pct, 0) as discrepancia_hist_pct
            FROM productos p
            JOIN stock s ON s.producto_id = p.id
            LEFT JOIN historial h ON h.producto_id = p.id
            WHERE p.activo AND s.stock_perpetuo > 0
        """
        result = await self.db.execute(text(query))
        filas = [dict(r._asdict()) for r in result.fetchall()]

        hoy = date.today()
        plan = []
        for fila in filas:
            costo = float(fila["costo_unitario"]) if fila["costo_unitario"] is not None else None
            valor = semantica.valor_inventario_costo(float(fila["stock_perpetuo"]), costo)
            ultimo = fila.get("ultimo_conteo")
            if ultimo is not None:
                dias_sin_conteo = (hoy - ultimo.date()).days
            else:
                dias_sin_conteo = 365  # nunca contado: máxima antigüedad
            score = semantica.prioridad_conteo(
                valor, float(fila["discrepancia_hist_pct"] or 0), dias_sin_conteo
            )
            plan.append(
                {
                    "nombre": fila["nombre"],
                    "stock_perpetuo": float(fila["stock_perpetuo"]),
                    "valor_inventario": valor,
                    "dias_sin_conteo": dias_sin_conteo,
                    "discrepancia_historica_pct": round(float(fila["discrepancia_hist_pct"] or 0), 1),
                    "score": round(score, 2),
                }
            )

        plan.sort(key=lambda x: x["score"], reverse=True)
        return plan[:limite]

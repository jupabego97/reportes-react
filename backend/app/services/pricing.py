"""
Servicio de pricing (Fase 4).

Consolida historial de precios, estima elasticidad aproximada (solo con
variación observada) y genera markdowns para inventario muerto/exceso.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class PricingService:
    """Historial de precios, elasticidad y oportunidades de markdown."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def consolidar_precios(self) -> Dict[str, Any]:
        """Upsert diario de precios desde ventas + snapshot del maestro."""
        from app.services.maestros import MaestrosService

        maestros = await MaestrosService(self.db).sincronizar()

        query_ventas = """
            INSERT INTO precios_historicos (producto_id, fecha, precio_venta, costo_unitario, fuente)
            SELECT
                p.id,
                v.fecha_venta,
                AVG(v.precio),
                AVG(v.precio_promedio_compra),
                'ventas'
            FROM reportes_ventas_30dias v
            JOIN productos p
              ON p.nombre = REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g')
            WHERE v.fecha_venta IS NOT NULL AND v.precio > 0
            GROUP BY p.id, v.fecha_venta
            ON CONFLICT (producto_id, fecha) DO UPDATE SET
                precio_venta = EXCLUDED.precio_venta,
                costo_unitario = COALESCE(EXCLUDED.costo_unitario, precios_historicos.costo_unitario),
                fuente = EXCLUDED.fuente
        """
        r1 = await self.db.execute(text(query_ventas))

        query_snapshot = """
            INSERT INTO precios_historicos (producto_id, fecha, precio_venta, costo_unitario, fuente)
            SELECT p.id, CURRENT_DATE, p.precio_venta, p.costo_unitario, 'maestro'
            FROM productos p
            WHERE p.precio_venta IS NOT NULL AND p.activo
            ON CONFLICT (producto_id, fecha) DO UPDATE SET
                precio_venta = COALESCE(EXCLUDED.precio_venta, precios_historicos.precio_venta),
                costo_unitario = COALESCE(EXCLUDED.costo_unitario, precios_historicos.costo_unitario)
        """
        r2 = await self.db.execute(text(query_snapshot))
        await self.db.commit()

        rango = await self.db.execute(
            text(
                """
                SELECT MIN(fecha), MAX(fecha), COUNT(DISTINCT producto_id)
                FROM precios_historicos
                """
            )
        )
        fila = rango.fetchone()
        return {
            "filas_ventas": r1.rowcount,
            "filas_snapshot": r2.rowcount,
            "historia_desde": str(fila[0]) if fila and fila[0] else None,
            "historia_hasta": str(fila[1]) if fila and fila[1] else None,
            "productos_con_precio": int(fila[2] or 0) if fila else 0,
            "maestros_sincronizados": maestros.get("productos_desde_items", 0)
            + maestros.get("productos_solo_en_ventas", 0),
        }

    async def estimar_elasticidades(self) -> List[Dict[str, Any]]:
        """Elasticidad log-log por producto con historia y variación de precio."""
        query = """
            SELECT
                ph.producto_id,
                p.nombre,
                ph.fecha,
                ph.precio_venta,
                COALESCE(h.unidades, 0) as unidades
            FROM precios_historicos ph
            JOIN productos p ON p.id = ph.producto_id
            LEFT JOIN ventas_diarias_historicas h
                   ON h.producto_id = ph.producto_id AND h.fecha = ph.fecha
            WHERE ph.precio_venta > 0
            ORDER BY ph.producto_id, ph.fecha
        """
        result = await self.db.execute(text(query))
        por_producto: Dict[int, Dict[str, Any]] = {}
        for r in result.fetchall():
            pid = int(r[0])
            if pid not in por_producto:
                por_producto[pid] = {"nombre": r[1], "precios": [], "cantidades": []}
            por_producto[pid]["precios"].append(float(r[3]))
            por_producto[pid]["cantidades"].append(float(r[4] or 0))

        elasticidades = []
        for pid, datos in por_producto.items():
            precios = datos["precios"]
            cantidades = datos["cantidades"]
            elast = semantica.elasticidad_loglog(precios, cantidades)
            if elast is None:
                continue
            media_p = sum(precios) / len(precios)
            cv = (max(precios) - min(precios)) / media_p if media_p > 0 else 0
            elasticidades.append(
                {
                    "producto_id": pid,
                    "nombre": datos["nombre"],
                    "elasticidad": round(elast, 4),
                    "confianza": semantica.confianza_elasticidad(len(precios), cv),
                    "observaciones": len(precios),
                }
            )
        elasticidades.sort(key=lambda x: abs(x["elasticidad"]), reverse=True)
        return elasticidades

    async def sugerir_markdowns(self) -> Dict[str, Any]:
        """Genera recomendaciones de markdown para inventario muerto y exceso."""
        query_muerto = """
            SELECT
                p.id as producto_id,
                p.nombre,
                COALESCE(i.cantidad_disponible, 0) as stock,
                p.precio_venta,
                p.costo_unitario,
                30 as dias_sin_venta
            FROM items i
            JOIN productos p ON p.nombre = UPPER(TRIM(i.nombre))
            WHERE COALESCE(i.cantidad_disponible, 0) > 0
              AND NOT EXISTS (
                  SELECT 1 FROM reportes_ventas_30dias v
                  WHERE REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g') = p.nombre
                    AND v.fecha_venta >= CURRENT_DATE - CAST(30 AS INTEGER)
              )
        """
        query_exceso = """
            WITH ventas AS (
                SELECT
                    p.id as producto_id,
                    p.nombre,
                    SUM(v.cantidad) as unidades,
                    COUNT(DISTINCT v.fecha_venta) as dias_con_venta
                FROM productos p
                JOIN reportes_ventas_30dias v
                  ON REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g') = p.nombre
                WHERE v.fecha_venta >= CURRENT_DATE - CAST(30 AS INTEGER)
                GROUP BY p.id, p.nombre
            )
            SELECT
                p.id,
                p.nombre,
                COALESCE(i.cantidad_disponible, 0) as stock,
                p.precio_venta,
                p.costo_unitario,
                CASE WHEN COALESCE(vent.unidades, 0) > 0
                     THEN COALESCE(i.cantidad_disponible, 0) / (vent.unidades / 30.0)
                     ELSE 999 END as cobertura
            FROM productos p
            JOIN items i ON UPPER(TRIM(i.nombre)) = p.nombre
            LEFT JOIN ventas vent ON vent.producto_id = p.id
            WHERE COALESCE(i.cantidad_disponible, 0) > 0
              AND (
                  COALESCE(vent.unidades, 0) = 0
                  OR COALESCE(i.cantidad_disponible, 0) / NULLIF(vent.unidades / 30.0, 0) > 60
              )
        """
        candidatos: Dict[int, Dict[str, Any]] = {}
        for q, es_muerto in ((query_muerto, True), (query_exceso, False)):
            try:
                result = await self.db.execute(text(q))
                for r in result.fetchall():
                    pid = int(r[0])
                    if pid in candidatos:
                        continue
                    precio = float(r[3]) if r[3] is not None else None
                    costo = float(r[4]) if r[4] is not None else None
                    if not precio:
                        continue
                    dias_sv = int(r[5]) if es_muerto else 0
                    cobertura = None if es_muerto else float(r[5] or 0)
                    sugerido = semantica.precio_markdown_optimo(
                        precio, costo, dias_sin_venta=dias_sv, cobertura=cobertura
                    )
                    if sugerido is None or sugerido >= precio:
                        continue
                    stock = float(r[2] or 0)
                    valor_atrapado = semantica.valor_inventario_costo(stock, costo) or 0
                    candidatos[pid] = {
                        "producto_id": pid,
                        "nombre": r[1],
                        "precio_actual": precio,
                        "precio_sugerido": sugerido,
                        "stock": stock,
                        "impacto_estimado": round(valor_atrapado, 2),
                        "motivo": (
                            "Sin venta en 30 días"
                            if es_muerto
                            else f"Exceso de cobertura ({cobertura:.0f} días)"
                        ),
                    }
            except Exception:
                await self.db.rollback()

        emitidas = 0
        for c in sorted(candidatos.values(), key=lambda x: x["impacto_estimado"], reverse=True):
            clave = f"markdown:{c['producto_id']}:{date.today():%Y-%m}"
            existe = await self.db.execute(
                text(
                    """
                    SELECT 1 FROM recomendaciones_precio
                    WHERE clave_dedup = :clave AND estado = 'pendiente' LIMIT 1
                    """
                ),
                {"clave": clave},
            )
            if existe.fetchone():
                continue
            await self.db.execute(
                text(
                    """
                    INSERT INTO recomendaciones_precio
                        (producto_id, tipo, precio_actual, precio_sugerido,
                         impacto_estimado, motivo, clave_dedup)
                    VALUES (:pid, 'markdown', :actual, :sugerido, :impacto, :motivo, :clave)
                    """
                ),
                {
                    "pid": c["producto_id"],
                    "actual": c["precio_actual"],
                    "sugerido": c["precio_sugerido"],
                    "impacto": c["impacto_estimado"],
                    "motivo": c["motivo"],
                    "clave": clave,
                },
            )
            emitidas += 1
        await self.db.commit()
        return {"recomendaciones_emitidas": emitidas, "candidatos": len(candidatos)}

    async def get_oportunidades_precio(self, limite: int = 50) -> List[Dict[str, Any]]:
        """Lista accionable de recomendaciones de precio pendientes."""
        query = """
            SELECT r.id, r.tipo, r.precio_actual, r.precio_sugerido, r.elasticidad,
                   r.confianza, r.impacto_estimado, r.motivo, r.estado, r.created_at,
                   p.nombre, p.id as producto_id
            FROM recomendaciones_precio r
            JOIN productos p ON p.id = r.producto_id
            WHERE r.estado = 'pendiente'
            ORDER BY r.impacto_estimado DESC NULLS LAST, r.created_at DESC
            LIMIT :limite
        """
        result = await self.db.execute(text(query), {"limite": limite})
        filas = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            for k in ("precio_actual", "precio_sugerido", "elasticidad", "impacto_estimado"):
                fila[k] = float(fila[k]) if fila[k] is not None else None
            fila["created_at"] = str(fila["created_at"]) if fila["created_at"] else None
            if fila["precio_actual"] and fila["precio_sugerido"]:
                fila["descuento_pct"] = round(
                    (1 - fila["precio_sugerido"] / fila["precio_actual"]) * 100, 1
                )
            filas.append(fila)
        return filas

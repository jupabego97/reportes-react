"""
Servicio de surtido (Fase 4).

Matriz GMROI × velocidad para decidir potenciar / mantener / reducir /
eliminar SKUs. Usa inventario actual como proxy de inventario promedio
(documentado). Transferencia de demanda estimada por familia (proxy).
"""
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class SurtidoService:
    """Revisión de surtido basada en GMROI y velocidad relativa."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _metricas_productos(self, dias: int = 30) -> List[Dict[str, Any]]:
        """GMROI, velocidad y datos por producto activo."""
        query = """
            WITH ventas AS (
                SELECT
                    p.id as producto_id,
                    p.nombre,
                    p.familia_id,
                    f.nombre as familia,
                    SUM(v.cantidad) as unidades,
                    SUM(v.precio * v.cantidad) as venta_neta,
                    SUM((v.precio - COALESCE(v.precio_promedio_compra, p.costo_unitario, 0))
                        * v.cantidad) as margen_bruto,
                    COUNT(DISTINCT v.fecha_venta) as dias_con_venta
                FROM productos p
                LEFT JOIN familias f ON f.id = p.familia_id
                LEFT JOIN reportes_ventas_30dias v
                  ON REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g') = p.nombre
                 AND v.fecha_venta >= CURRENT_DATE - CAST(:dias AS INTEGER)
                WHERE p.activo
                GROUP BY p.id, p.nombre, p.familia_id, f.nombre
            )
            SELECT
                vent.producto_id,
                vent.nombre,
                vent.familia_id,
                vent.familia,
                COALESCE(vent.unidades, 0) as unidades,
                COALESCE(vent.venta_neta, 0) as venta_neta,
                COALESCE(vent.margen_bruto, 0) as margen_bruto,
                COALESCE(i.cantidad_disponible, 0) as stock,
                p.costo_unitario,
                p.precio_venta
            FROM ventas vent
            JOIN productos p ON p.id = vent.producto_id
            LEFT JOIN items i ON UPPER(TRIM(i.nombre)) = p.nombre
        """
        result = await self.db.execute(text(query), {"dias": dias})
        filas = [dict(r._asdict()) for r in result.fetchall()]
        if not filas:
            return []

        for f in filas:
            stock = float(f["stock"] or 0)
            costo = float(f["costo_unitario"]) if f["costo_unitario"] is not None else None
            inv_costo = semantica.valor_inventario_costo(stock, costo) or 0
            margen = float(f["margen_bruto"] or 0)
            # Proxy: inventario actual al costo (no promedio histórico)
            gmroi_val = semantica.gmroi(margen * (365.0 / dias), inv_costo)
            f["gmroi"] = round(gmroi_val, 2) if gmroi_val is not None else None
            f["velocidad_diaria"] = semantica.venta_diaria(float(f["unidades"] or 0), dias)
            f["inventario_costo"] = round(inv_costo, 2)

        velocidades = [f["velocidad_diaria"] for f in filas if f["velocidad_diaria"] > 0]
        mediana = sorted(velocidades)[len(velocidades) // 2] if velocidades else 1.0
        mediana = mediana or 1.0

        for f in filas:
            f["velocidad_relativa"] = round(f["velocidad_diaria"] / mediana, 2)
            f["accion"] = semantica.clasificar_surtido(f["gmroi"], f["velocidad_relativa"])

        return filas

    async def _transferencia_proxy(self, producto_id: int, familia_id: Optional[int]) -> float:
        """% de demanda capturable por otros SKUs de la misma familia (proxy)."""
        if familia_id is None:
            return 0.0
        query = """
            SELECT COUNT(DISTINCT p2.id)
            FROM productos p2
            JOIN reportes_ventas_30dias v
              ON REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g') = p2.nombre
            WHERE p2.familia_id = :familia
              AND p2.id <> :pid
              AND p2.activo
              AND v.fecha_venta >= CURRENT_DATE - CAST(30 AS INTEGER)
              AND v.cantidad > 0
        """
        result = await self.db.execute(
            text(query), {"familia": familia_id, "pid": producto_id}
        )
        sustitutos = int(result.scalar() or 0)
        if sustitutos >= 3:
            return 70.0
        if sustitutos >= 1:
            return 40.0
        return 10.0

    async def generar_revision(self) -> Dict[str, Any]:
        """Calcula y persiste recomendaciones de surtido."""
        metricas = await self._metricas_productos()
        emitidas = 0
        por_accion: Dict[str, int] = {}

        for m in metricas:
            accion = m["accion"]
            por_accion[accion] = por_accion.get(accion, 0) + 1
            if accion not in ("eliminar", "reducir", "potenciar"):
                continue

            transferencia = None
            if accion == "eliminar":
                transferencia = await self._transferencia_proxy(
                    m["producto_id"], m.get("familia_id")
                )

            impacto = m["inventario_costo"] if accion in ("eliminar", "reducir") else None
            clave = f"surtido:{m['producto_id']}:{accion}:{date.today():%Y-%m}"

            existe = await self.db.execute(
                text(
                    """
                    SELECT 1 FROM decisiones_surtido
                    WHERE clave_dedup = :clave AND estado = 'pendiente' LIMIT 1
                    """
                ),
                {"clave": clave},
            )
            if existe.fetchone():
                continue

            motivo = (
                f"GMROI {m['gmroi']}, velocidad relativa {m['velocidad_relativa']}x mediana"
                if m["gmroi"] is not None
                else f"Velocidad relativa {m['velocidad_relativa']}x mediana"
            )
            await self.db.execute(
                text(
                    """
                    INSERT INTO decisiones_surtido
                        (producto_id, accion, gmroi, velocidad_relativa,
                         impacto_estimado, transferencia_proxy_pct, motivo, clave_dedup)
                    VALUES (:pid, :accion, :gmroi, :vrel, :impacto, :transf, :motivo, :clave)
                    """
                ),
                {
                    "pid": m["producto_id"],
                    "accion": accion,
                    "gmroi": m["gmroi"],
                    "vrel": m["velocidad_relativa"],
                    "impacto": impacto,
                    "transf": transferencia,
                    "motivo": motivo,
                    "clave": clave,
                },
            )
            emitidas += 1

        await self.db.commit()
        return {
            "productos_analizados": len(metricas),
            "recomendaciones_emitidas": emitidas,
            "por_accion": por_accion,
        }

    async def get_revision_surtido(self, limite: int = 100) -> List[Dict[str, Any]]:
        """Recomendaciones de surtido pendientes + matriz completa en vivo."""
        metricas = await self._metricas_productos()
        metricas.sort(
            key=lambda m: (
                {"eliminar": 0, "reducir": 1, "potenciar": 2, "mantener": 3}.get(m["accion"], 9),
                -(m["inventario_costo"] or 0),
            )
        )
        for m in metricas[:limite]:
            if m["accion"] == "eliminar":
                m["transferencia_proxy_pct"] = await self._transferencia_proxy(
                    m["producto_id"], m.get("familia_id")
                )
        return metricas[:limite]

    async def aplicar_baja(self, producto_id: int) -> Dict[str, Any]:
        """Baja lógica de un SKU (activo=false). No borra historial."""
        result = await self.db.execute(
            text(
                """
                UPDATE productos SET activo = false, updated_at = NOW()
                WHERE id = :id AND activo
                RETURNING nombre
                """
            ),
            {"id": producto_id},
        )
        row = result.fetchone()
        if not row:
            raise ValueError("El producto no existe o ya está inactivo")

        await self.db.execute(
            text(
                """
                UPDATE decisiones_surtido SET estado = 'aplicada'
                WHERE producto_id = :id AND estado = 'pendiente' AND accion = 'eliminar'
                """
            ),
            {"id": producto_id},
        )
        await self.db.commit()
        return {"producto_id": producto_id, "nombre": row[0], "activo": False}

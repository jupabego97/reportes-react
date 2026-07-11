"""
Servicio de diagnóstico causal (Fase 4).

Descompone la variación de venta entre dos períodos en efectos de
volumen, precio y mix (productos que explican la desviación).
"""
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class DiagnosticoCausalService:
    """Descomposición volumen / precio / mix de la venta."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _agregar_periodo(self, dias_atras_inicio: int, dias_atras_fin: int) -> List[Dict]:
        """Agrega venta por producto en una ventana [fin, inicio] días atrás."""
        query = """
            SELECT
                REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g') as nombre,
                SUM(v.cantidad) as cantidad,
                CASE WHEN SUM(v.cantidad) > 0
                     THEN SUM(v.precio * v.cantidad) / SUM(v.cantidad)
                     ELSE AVG(v.precio) END as precio,
                SUM(v.precio * v.cantidad) as venta_neta,
                SUM((v.precio - COALESCE(v.precio_promedio_compra, 0)) * v.cantidad) as margen
            FROM reportes_ventas_30dias v
            WHERE v.fecha_venta >= CURRENT_DATE - CAST(:inicio AS INTEGER)
              AND v.fecha_venta < CURRENT_DATE - CAST(:fin AS INTEGER)
            GROUP BY REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g')
        """
        result = await self.db.execute(
            text(query), {"inicio": dias_atras_inicio, "fin": dias_atras_fin}
        )
        return [
            {
                "nombre": r[0],
                "cantidad": float(r[1] or 0),
                "precio": float(r[2] or 0),
                "venta_neta": float(r[3] or 0),
                "margen": float(r[4] or 0),
            }
            for r in result.fetchall()
        ]

    async def get_descomposicion(
        self,
        dias_reciente: int = 7,
        dias_previo: int = 7,
    ) -> Dict[str, Any]:
        """Compara ventana reciente vs ventana previa inmediata."""
        periodo_b = await self._agregar_periodo(dias_reciente, 0)
        periodo_a = await self._agregar_periodo(dias_reciente + dias_previo, dias_reciente)

        descomp = semantica.descomponer_varianza_venta(periodo_a, periodo_b)

        margen_a = sum(p["margen"] for p in periodo_a)
        margen_b = sum(p["margen"] for p in periodo_b)
        delta_margen = margen_b - margen_a

        descomp["margen_periodo_a"] = round(margen_a, 2)
        descomp["margen_periodo_b"] = round(margen_b, 2)
        descomp["delta_margen"] = round(delta_margen, 2)
        descomp["dias_reciente"] = dias_reciente
        descomp["dias_previo"] = dias_previo
        descomp["interpretacion"] = self._interpretar(descomp, delta_margen)
        descomp["detalle"] = descomp["detalle"][:20]
        return descomp

    def _interpretar(self, descomp: Dict[str, Any], delta_margen: float) -> str:
        delta_v = descomp.get("delta_venta", 0)
        ev = descomp.get("efecto_volumen", 0)
        ep = descomp.get("efecto_precio", 0)
        em = descomp.get("efecto_mix", 0)

        if abs(delta_v) < 1:
            return "La venta se mantuvo estable entre períodos."

        partes = []
        if abs(ev) >= abs(ep) and abs(ev) >= abs(em):
            partes.append(
                f"El volumen {'subió' if ev > 0 else 'bajó'} (${abs(ev):,.0f})"
            )
        if abs(ep) >= abs(ev) * 0.5:
            partes.append(
                f"el precio {'contribuyó positivamente' if ep > 0 else 'presionó'} (${abs(ep):,.0f})"
            )
        if abs(em) >= abs(ev) * 0.3:
            partes.append(f"el mix de productos cambió (${abs(em):,.0f})")

        texto = "La variación se explica principalmente porque " + ", ".join(partes) + "."
        if delta_margen < 0 and abs(ep) < abs(em):
            texto += " El margen cayó más que la venta: revisar mix hacia productos de bajo margen."
        return texto

"""
Servicio de reabastecimiento (Fase 2) — stock de seguridad dinámico y ROP.

Reemplaza los días fijos de cobertura de la Fase 1 por la fórmula estándar
de la industria: cada producto recibe el nivel de servicio de su clase ABC
(A: 99%, B: 97%, C: 92%) y un stock de seguridad calculado con la
variabilidad REAL de su demanda y el lead time de SU proveedor.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class ReabastecimientoService:
    """Sugerencias de reposición con SS dinámico y punto de reorden."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_sugerencias(
        self, dias_historia: int = 60, horizonte_cobertura_dias: int = 30
    ) -> List[Dict[str, Any]]:
        """Cálculo por producto activo con venta reciente:

        - demanda diaria y su desviación estándar (serie densa del historial)
        - clase ABC por contribución a la venta → nivel de servicio objetivo
        - lead time del proveedor (maestro) o default
        - SS = z × √(LT×σ²_d + d²×σ²_LT)  |  ROP = d×LT + SS
        - cantidad sugerida = demanda×horizonte + SS − stock actual
        """
        query = """
            WITH historia AS (
                SELECT
                    h.producto_id,
                    SUM(h.unidades) as unidades,
                    SUM(h.venta_neta) as venta_neta,
                    COUNT(*) as dias_con_venta,
                    MIN(h.fecha) as desde,
                    MAX(h.fecha) as hasta,
                    STDDEV_SAMP(h.unidades) as sigma_dias_con_venta,
                    AVG(h.unidades) as media_dias_con_venta
                FROM ventas_diarias_historicas h
                WHERE h.fecha >= CURRENT_DATE - CAST(:dias || ' days' AS INTERVAL)
                GROUP BY h.producto_id
                HAVING SUM(h.unidades) > 0
            )
            SELECT
                p.id, p.nombre, p.precio_venta, p.costo_unitario,
                prov.nombre as proveedor,
                COALESCE(prov.lead_time_dias, :lt_default) as lead_time,
                hist.unidades, hist.venta_neta, hist.dias_con_venta,
                hist.desde, hist.hasta,
                hist.sigma_dias_con_venta, hist.media_dias_con_venta,
                COALESCE(i.cantidad_disponible, 0) as stock_actual
            FROM historia hist
            JOIN productos p ON p.id = hist.producto_id
            LEFT JOIN proveedores prov ON prov.id = p.proveedor_principal_id
            LEFT JOIN items i ON UPPER(TRIM(i.nombre)) = p.nombre
            WHERE p.activo
        """
        result = await self.db.execute(
            text(query), {"dias": dias_historia, "lt_default": semantica.LEAD_TIME_DEFAULT}
        )
        filas = [dict(r._asdict()) for r in result.fetchall()]
        if not filas:
            return []

        # Clase ABC por contribución acumulada a la venta (80/95)
        filas.sort(key=lambda f: float(f["venta_neta"] or 0), reverse=True)
        venta_total = sum(float(f["venta_neta"] or 0) for f in filas) or 1.0
        acumulado = 0.0
        for f in filas:
            acumulado += float(f["venta_neta"] or 0)
            pct = acumulado / venta_total
            f["abc"] = "A" if pct <= 0.80 else ("B" if pct <= 0.95 else "C")

        sugerencias: List[Dict[str, Any]] = []
        for f in filas:
            dias_ventana = max((f["hasta"] - f["desde"]).days + 1, 1)
            demanda_d = semantica.venta_diaria(float(f["unidades"] or 0), dias_ventana)
            if demanda_d <= 0:
                continue

            # σ de la serie DENSA: la desviación reportada por SQL solo cubre
            # los días con venta; se corrige incorporando los días en cero.
            n_con_venta = int(f["dias_con_venta"] or 0)
            media_cv = float(f["media_dias_con_venta"] or 0)
            sigma_cv = float(f["sigma_dias_con_venta"] or 0)
            n = dias_ventana
            # var densa = E[x²] − media², con ceros en (n − n_con_venta) días
            e_x2 = (n_con_venta * (sigma_cv**2 + media_cv**2)) / n if n > 0 else 0.0
            var_densa = max(e_x2 - demanda_d**2, 0.0)
            sigma_d = var_densa**0.5

            nivel = semantica.NIVEL_SERVICIO_OBJETIVO.get(f["abc"], 0.92)
            lt = int(f["lead_time"] or semantica.LEAD_TIME_DEFAULT)
            ss = semantica.stock_seguridad(nivel, lt, sigma_d, demanda_d)
            rop = semantica.punto_reorden(demanda_d, lt, ss)

            stock = float(f["stock_actual"] or 0)
            objetivo = demanda_d * horizonte_cobertura_dias + ss
            cantidad = max(round(objetivo - stock), 0)
            cobertura = semantica.dias_cobertura(stock, demanda_d)

            if stock <= 0:
                urgencia = "quiebre"
            elif stock <= rop:
                urgencia = "pedir_ya"
            elif cobertura is not None and cobertura <= horizonte_cobertura_dias:
                urgencia = "planificar"
            else:
                urgencia = "ok"

            costo = float(f["costo_unitario"]) if f["costo_unitario"] is not None else None
            sugerencias.append(
                {
                    "nombre": f["nombre"],
                    "proveedor": f["proveedor"],
                    "abc": f["abc"],
                    "nivel_servicio_objetivo": nivel,
                    "stock_actual": stock,
                    "demanda_diaria": round(demanda_d, 2),
                    "sigma_demanda": round(sigma_d, 2),
                    "lead_time_dias": lt,
                    "stock_seguridad": round(ss, 1),
                    "punto_reorden": round(rop, 1),
                    "dias_cobertura": round(cobertura, 1) if cobertura is not None else None,
                    "cantidad_sugerida": int(cantidad),
                    "costo_estimado": round(cantidad * costo, 2) if costo is not None else None,
                    "urgencia": urgencia,
                }
            )

        orden = {"quiebre": 0, "pedir_ya": 1, "planificar": 2, "ok": 3}
        sugerencias.sort(
            key=lambda s: (orden.get(s["urgencia"], 9), -(s["costo_estimado"] or 0))
        )
        return sugerencias

    async def get_resumen(self) -> Dict[str, Any]:
        """Totales por urgencia para la cabecera de la UI."""
        sugerencias = await self.get_sugerencias()
        resumen: Dict[str, Any] = {
            "total_productos": len(sugerencias),
            "por_urgencia": {},
            "inversion_pedir_ya": 0.0,
        }
        for s in sugerencias:
            u = s["urgencia"]
            resumen["por_urgencia"][u] = resumen["por_urgencia"].get(u, 0) + 1
            if u in ("quiebre", "pedir_ya") and s["costo_estimado"]:
                resumen["inversion_pedir_ya"] += s["costo_estimado"]
        resumen["inversion_pedir_ya"] = round(resumen["inversion_pedir_ya"], 2)
        return resumen

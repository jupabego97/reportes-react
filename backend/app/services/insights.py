"""
Servicio de insights inteligentes para gestión de inventario.
Cruza información de ventas, compras (sugerencias) y ABC para generar insights accionables.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import FilterParams, SugerenciaCompraResponse
from app.services.ventas import VentasService
from app.services.compras import ComprasService
from app.services.predicciones import PrediccionesService
from app.services.margenes import MargenesService
from app.services.inventario import InventarioService


class InsightsService:
    """Servicio de insights de alto nivel."""

    def __init__(
        self,
        db: AsyncSession,
        ventas_service: VentasService,
        predicciones_service: Optional[PrediccionesService] = None,
    ):
        self.db = db
        self.ventas_service = ventas_service
        self.predicciones_service = predicciones_service or PrediccionesService(ventas_service)
        self.compras_service = ComprasService(
            db,
            ventas_service,
            self.predicciones_service,
        )

    def _serialize_sugerencias(self, items: List[Any], limit: int = 5) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for s in items[:limit]:
            if isinstance(s, SugerenciaCompraResponse):
                out.append(s.model_dump(mode="json"))
            elif hasattr(s, "model_dump"):
                out.append(s.model_dump(mode="json"))
            elif isinstance(s, dict):
                out.append(s)
        return out

    async def get_insights(self, filters: FilterParams) -> Dict[str, Any]:
        """
        Genera un conjunto de insights cruzando ABC + inventario + tendencias.

        Estructura de respuesta:
        {
            "productos_en_riesgo": [...],
            "oportunidades": [...],
            "sobre_stock": [...],
            "proveedores_en_riesgo": [...],
        }
        """
        sugerencias: List[SugerenciaCompraResponse] = await self.compras_service.get_sugerencias(filters)

        if not sugerencias:
            return {
                "productos_en_riesgo": [],
                "oportunidades": [],
                "sobre_stock": [],
                "proveedores_en_riesgo": [],
            }

        # Productos en riesgo: clase A con poco stock
        productos_en_riesgo = [
            s
            for s in sugerencias
            if (s.clasificacion_abc or "C") == "A" and s.dias_stock <= 7
        ]

        # Oportunidades: alto ROI estimado, stock bajo o en cero
        oportunidades = [
            s
            for s in sugerencias
            if (s.roi_estimado or 0) > 0 and s.cantidad_disponible <= s.cobertura_objetivo_dias * s.venta_diaria * 0.3
        ]
        oportunidades.sort(key=lambda x: (x.roi_estimado or 0), reverse=True)

        # Sobre-stock: clase C con muchos días de stock
        sobre_stock = [
            s
            for s in sugerencias
            if (s.clasificacion_abc or "C") == "C" and s.dias_stock >= 90
        ]

        # Productos que se van a agotar esta semana (todos los que tienen < 7 dias)
        productos_agotamiento_semana = [
            s for s in sugerencias if s.dias_stock < 7 and s.dias_stock >= 0
        ]
        productos_agotamiento_semana.sort(key=lambda x: x.dias_stock)

        # Costo de oportunidad: ventas perdidas estimadas por quiebre (stock=0)
        costo_oportunidad = 0.0
        for s in sugerencias:
            if s.cantidad_disponible <= 0 and s.venta_diaria > 0 and s.precio_compra:
                precio_venta_aprox = s.precio_compra * 1.4  # margen ~30%
                costo_oportunidad += s.venta_diaria * 7 * precio_venta_aprox

        # Proveedores en riesgo: muchos productos en riesgo por proveedor
        proveedores_map: Dict[str, Dict[str, Any]] = {}
        for s in productos_en_riesgo:
            if not s.proveedor:
                continue
            if s.proveedor not in proveedores_map:
                proveedores_map[s.proveedor] = {
                    "proveedor": s.proveedor,
                    "productos_en_riesgo": 0,
                    "costo_estimado": 0.0,
                }
            proveedores_map[s.proveedor]["productos_en_riesgo"] += 1
            proveedores_map[s.proveedor]["costo_estimado"] += s.costo_estimado

        proveedores_en_riesgo = sorted(
            proveedores_map.values(),
            key=lambda x: (x["productos_en_riesgo"], x["costo_estimado"]),
            reverse=True,
        )

        return {
            "productos_en_riesgo": productos_en_riesgo,
            "oportunidades": oportunidades[:20],
            "sobre_stock": sobre_stock[:20],
            "proveedores_en_riesgo": proveedores_en_riesgo,
            "productos_agotamiento_semana": [
                {
                    "nombre": s.nombre,
                    "proveedor": s.proveedor,
                    "dias_stock": s.dias_stock,
                    "venta_diaria": s.venta_diaria,
                    "cantidad_sugerida": s.cantidad_sugerida,
                    "prioridad": s.prioridad,
                }
                for s in productos_agotamiento_semana[:15]
            ],
            "costo_oportunidad_estimado": round(costo_oportunidad, 2),
        }

    def _build_insight_cards(self, insights_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Tarjetas cortas para vista CEO (no duplican tablas completas de /insights)."""
        cards: List[Dict[str, str]] = []
        pr = insights_data.get("productos_en_riesgo") or []
        if len(pr) > 0:
            cards.append(
                {
                    "tipo": "warning",
                    "icono": "🚨",
                    "titulo": f"{len(pr)} productos clase A en riesgo de quiebre",
                    "descripcion": "Stock bajo respecto a su rotación. Revisar compras prioritarias.",
                }
            )
        op = insights_data.get("oportunidades") or []
        if len(op) > 0:
            cards.append(
                {
                    "tipo": "positive",
                    "icono": "💡",
                    "titulo": f"{len(op)} oportunidades de reabasto con buen ROI",
                    "descripcion": "SKU con demanda y retorno estimado favorable.",
                }
            )
        ss = insights_data.get("sobre_stock") or []
        if len(ss) > 0:
            cards.append(
                {
                    "tipo": "info",
                    "icono": "📦",
                    "titulo": f"{len(ss)} posibles sobre-stock (clase C)",
                    "descripcion": "Capital inmovilizado; evaluar promociones o ajuste de pedidos.",
                }
            )
        prov = insights_data.get("proveedores_en_riesgo") or []
        if len(prov) > 0:
            top = prov[0]
            cards.append(
                {
                    "tipo": "warning",
                    "icono": "🚚",
                    "titulo": f"Proveedor {top.get('proveedor', '')} con más concentración de riesgo",
                    "descripcion": f"{top.get('productos_en_riesgo', 0)} SKU en alerta; costo estimado ${top.get('costo_estimado', 0):,.0f}.",
                }
            )
        co = insights_data.get("costo_oportunidad_estimado") or 0
        if co and float(co) > 0:
            cards.append(
                {
                    "tipo": "negative",
                    "icono": "💸",
                    "titulo": "Costo de oportunidad por roturas",
                    "descripcion": f"Estimado ~${float(co):,.0f} en 7 días por ventas no atendidas (SKU sin stock).",
                }
            )
        return cards[:8]

    async def get_kpis_ejecutivo(self, filters: FilterParams) -> Dict[str, Any]:
        """KPIs consolidados para CEO en una sola llamada (respeta filtros del período)."""
        today = date.today()
        f_hoy = filters.model_copy(update={"fecha_inicio": today, "fecha_fin": today})
        ayer = today - timedelta(days=1)
        f_ayer = filters.model_copy(update={"fecha_inicio": ayer, "fecha_fin": ayer})

        m_hoy = await self.ventas_service.get_metricas(f_hoy)
        m_ayer = await self.ventas_service.get_metricas(f_ayer)
        m_periodo = await self.ventas_service.get_metricas(filters)

        ventas_hoy = float(m_hoy.total_ventas or 0)
        transacciones_hoy = int(m_hoy.total_registros or 0)
        ventas_ayer = float(m_ayer.total_ventas or 0)
        if ventas_ayer > 0:
            delta_vs_ayer = round((ventas_hoy - ventas_ayer) / ventas_ayer * 100, 1)
        else:
            delta_vs_ayer = 0.0 if ventas_hoy == 0 else 100.0

        margenes_service = MargenesService(self.ventas_service)
        marg = await margenes_service.get_analisis_margenes(filters)
        margen_bruto_pct = (
            round((marg.margen_total / marg.ventas_con_margen_total) * 100, 2)
            if marg.ventas_con_margen_total and marg.ventas_con_margen_total > 0
            else 0.0
        )

        fams_sorted = sorted(
            marg.margenes_por_familia or [],
            key=lambda x: float(x.get("margen_total", 0) or 0),
            reverse=True,
        )
        top_familias_margen = fams_sorted[:3]

        inv_service = InventarioService(self.db)
        res_inv = await inv_service.get_resumen_inventario()
        stockout = await inv_service.get_stockout_rate()
        productos = await inv_service.get_inventario_completo()

        total_p = int(res_inv.get("total_productos", 0) or 0)
        normales = int(res_inv.get("productos_normales", 0) or 0)
        exceso = int(res_inv.get("productos_exceso", 0) or 0)
        salud_pct = round((normales + exceso) / total_p * 100, 1) if total_p > 0 else 100.0

        # Cobertura: menor y mayor (capital ocioso)
        with_cov = [p for p in productos if p.get("dias_cobertura") is not None and p.get("dias_cobertura", 999) < 999]
        by_cov = sorted(with_cov, key=lambda x: float(x.get("dias_cobertura") or 999))
        top_menor_cobertura = [
            {
                "nombre": p.get("nombre"),
                "dias_cobertura": p.get("dias_cobertura"),
                "proveedor": p.get("proveedor"),
            }
            for p in by_cov[:5]
        ]
        by_cov_desc = sorted(
            with_cov,
            key=lambda x: float(x.get("dias_cobertura") or 0),
            reverse=True,
        )
        top_mayor_cobertura = [
            {
                "nombre": p.get("nombre"),
                "dias_cobertura": p.get("dias_cobertura"),
                "proveedor": p.get("proveedor"),
            }
            for p in by_cov_desc[:5]
        ]

        # GMROI por familia (proxy: margen período / valor inventario actual por familia)
        valor_por_fam = {x["familia"]: float(x.get("valor") or 0) for x in await inv_service.get_valor_por_familia()}
        gmroi_rows: List[Dict[str, Any]] = []
        for row in fams_sorted:
            fam = row.get("familia") or "Sin familia"
            inv_val = valor_por_fam.get(fam, 0.0)
            mt = float(row.get("margen_total") or 0)
            gmroi = round(mt / inv_val, 3) if inv_val > 0 else None
            gmroi_rows.append(
                {
                    "familia": fam,
                    "gmroi": gmroi,
                    "margen_total": round(mt, 2),
                    "valor_inventario": round(inv_val, 2),
                }
            )
        gmroi_rows = [r for r in gmroi_rows if r.get("gmroi") is not None]
        gmroi_rows.sort(key=lambda x: float(x["gmroi"] or 0), reverse=True)
        gmroi_top = gmroi_rows[:5]

        # Concentración margen top 10 SKU
        top_m = marg.top_margen or []
        total_m = float(marg.margen_total or 0)
        top10_m = sum(float(x.get("total_margen") or 0) for x in top_m[:10])
        concentracion_margen_top10_pct = (
            round(top10_m / total_m * 100, 1) if total_m > 0 else 0.0
        )

        backtest = await self.predicciones_service.get_backtest_metricas(filters, semanas=4)
        wape_forecast = backtest.get("wape_promedio")
        mape_forecast = backtest.get("mape_promedio")

        insights_data = await self.get_insights(filters)
        prod_riesgo = insights_data.get("productos_en_riesgo") or []
        oportunidades = insights_data.get("oportunidades") or []

        delta_periodo_str = m_periodo.delta_ventas
        delta_periodo_num: Optional[float] = None
        if delta_periodo_str and isinstance(delta_periodo_str, str):
            try:
                delta_periodo_num = float(
                    delta_periodo_str.replace("%", "").replace("+", "").strip()
                )
            except ValueError:
                delta_periodo_num = None

        lineas_con_margen = int((marg.ventas_rentables or 0) + (marg.ventas_no_rentables or 0))

        return {
            "ventas_hoy": round(ventas_hoy, 2),
            "transacciones_hoy": transacciones_hoy,
            "delta_vs_ayer": delta_vs_ayer,
            "ventas_mes": round(float(m_periodo.total_ventas or 0), 2),
            "transacciones_mes": int(m_periodo.total_registros or 0),
            "delta_periodo_pct": delta_periodo_num,
            "delta_ventas_periodo_str": delta_periodo_str,
            "ticket_promedio_linea": round(float(m_periodo.precio_promedio or 0), 2),
            "margen_total": round(float(m_periodo.margen_total or 0), 2),
            "margen_bruto_pct": margen_bruto_pct,
            "productos_vendidos": lineas_con_margen,
            "top_familias_margen": top_familias_margen,
            "valor_inventario_total": res_inv.get("valor_total", 0),
            "valor_criticos": res_inv.get("valor_criticos", 0),
            "valor_exceso": res_inv.get("valor_exceso", 0),
            "salud_inventario_pct": salud_pct,
            "wape_forecast": wape_forecast,
            "mape_forecast": mape_forecast,
            "top_urgencias": self._serialize_sugerencias(prod_riesgo, 5),
            "top_oportunidades": self._serialize_sugerencias(oportunidades, 5),
            "costo_oportunidad_estimado": insights_data.get("costo_oportunidad_estimado"),
            "insight_cards": self._build_insight_cards(insights_data),
            "stockout_pct": stockout.get("stockout_pct"),
            "stockout_activos": stockout.get("activos"),
            "stockout_sin_stock": stockout.get("sin_stock"),
            "gmroi_top_familias": gmroi_top,
            "concentracion_margen_top10_pct": concentracion_margen_top10_pct,
            "top_menor_cobertura": top_menor_cobertura,
            "top_mayor_cobertura": top_mayor_cobertura,
        }

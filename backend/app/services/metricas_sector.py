"""Métricas retail estándar usando únicamente las tablas actuales."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import FilterParams, SectorMetric
from app.services.facturas_proveedor import FacturasProveedorService
from app.services.predicciones import PrediccionesService
from app.services.ventas import VentasService


class MetricasSectorService:
    """KPIs consolidados para el dashboard ejecutivo retail."""

    CONSUMIDOR_GENERICO = {
        "",
        "consumidor final",
        "cliente contado",
        "cliente",
        "sin cliente",
        "n/a",
        "na",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def metric(
        label: str,
        value: Optional[float | int | str | bool],
        formula: str,
        quality: str = "standard",
        source_note: str = "",
    ) -> SectorMetric:
        return SectorMetric(
            label=label,
            value=value,
            formula=formula,
            quality=quality,
            source_note=source_note,
        )

    @staticmethod
    def safe_pct(numerator: float, denominator: float) -> Optional[float]:
        if denominator <= 0:
            return None
        return round(numerator / denominator * 100, 2)

    @staticmethod
    def compute_ticket_metrics(invoice_rows: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calcula métricas por factura a partir de filas agrupadas por id."""
        facturas = len(invoice_rows)
        ventas = sum(float(r.get("total_factura") or 0) for r in invoice_rows)
        unidades = sum(float(r.get("unidades") or 0) for r in invoice_rows)
        lineas = sum(float(r.get("lineas") or 0) for r in invoice_rows)
        return {
            "ventas_totales": ventas,
            "facturas_totales": facturas,
            "ticket_promedio_real": ventas / facturas if facturas else 0,
            "unidades_por_ticket": unidades / facturas if facturas else 0,
            "lineas_por_ticket": lineas / facturas if facturas else 0,
            "asp": ventas / unidades if unidades else 0,
            "unidades_vendidas": unidades,
            "lineas_vendidas": lineas,
        }

    @staticmethod
    def resumen_ventana(invoice_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resumen de ventas para una ventana temporal."""
        m = MetricasSectorService.compute_ticket_metrics(invoice_rows)
        return {
            "ventas": round(m["ventas_totales"], 2),
            "facturas": int(m["facturas_totales"]),
            "unidades": round(m["unidades_vendidas"], 2),
            "lineas": int(m["lineas_vendidas"]),
            "ticket_promedio": round(m["ticket_promedio_real"], 2),
            "unidades_por_ticket": round(m["unidades_por_ticket"], 2),
            "lineas_por_ticket": round(m["lineas_por_ticket"], 2),
            "asp": round(m["asp"], 2),
        }

    @staticmethod
    def _parse_fecha(value: Any) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    @classmethod
    def filter_invoices(cls, invoice_rows: List[Dict[str, Any]], start: date, end: date) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for r in invoice_rows:
            fd = cls._parse_fecha(r.get("fecha"))
            if fd is not None and start <= fd <= end:
                out.append(r)
        return out

    @staticmethod
    def variacion_ventana(actual: Dict[str, Any], anterior: Dict[str, Any]) -> Dict[str, Optional[float]]:
        def chg(key: str) -> Optional[float]:
            prev = float(anterior.get(key) or 0)
            curr = float(actual.get(key) or 0)
            if prev <= 0:
                return 100.0 if curr > 0 else 0.0
            return round((curr - prev) / prev * 100, 2)

        return {
            "ventas_pct": chg("ventas"),
            "unidades_pct": chg("unidades"),
            "ticket_pct": chg("ticket_promedio"),
            "facturas_pct": chg("facturas"),
        }

    @staticmethod
    def _week_start(d: date) -> date:
        return d - timedelta(days=d.weekday())

    def _periodo(self, filters: FilterParams) -> Tuple[date, date]:
        fin = filters.fecha_fin or date.today()
        inicio = filters.fecha_inicio or (fin - timedelta(days=29))
        if inicio > fin:
            inicio, fin = fin, inicio
        return inicio, fin

    def _facturas_cte_sql(self, extra_select: str = "") -> str:
        sel = f", {extra_select}" if extra_select else ""
        return f"""
            WITH facturas_agrupadas AS (
                SELECT
                    f.id,
                    MIN(f.fecha) AS fecha,
                    MAX(f.hora) AS hora,
                    MAX(f.cliente) AS cliente,
                    MAX(f.metodo) AS metodo,
                    MAX(f.vendedor) AS vendedor,
                    COALESCE(MAX(f.totalfact), SUM(COALESCE(f.total, f.precio * f.cantidad))) AS total_factura,
                    SUM(COALESCE(f.cantidad, 0)) AS unidades,
                    COUNT(*) AS lineas
                    {sel}
                FROM facturas f
                LEFT JOIN items i ON i.nombre = f.nombre
                {{where}}
                GROUP BY f.id
            )
        """

    def _facturas_where(
        self,
        filters: FilterParams,
        inicio: Optional[date] = None,
        fin: Optional[date] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        where = "WHERE f.fecha BETWEEN :fecha_inicio AND :fecha_fin"
        p_inicio, p_fin = self._periodo(filters)
        if inicio is not None:
            p_inicio = inicio
        if fin is not None:
            p_fin = fin
        params: Dict[str, Any] = {"fecha_inicio": p_inicio, "fecha_fin": p_fin}

        if filters.productos:
            where += " AND f.nombre = ANY(:productos)"
            params["productos"] = filters.productos
        if filters.vendedores:
            where += " AND f.vendedor = ANY(:vendedores)"
            params["vendedores"] = filters.vendedores
        if filters.metodos:
            where += " AND f.metodo = ANY(:metodos)"
            params["metodos"] = filters.metodos
        if filters.familias:
            where += " AND i.familia = ANY(:familias)"
            params["familias"] = filters.familias
        if filters.proveedores:
            where += """
                AND f.nombre IN (
                    SELECT DISTINCT nombre
                    FROM reportes_ventas_30dias
                    WHERE proveedor_moda = ANY(:proveedores)
                )
            """
            params["proveedores"] = filters.proveedores
        if filters.precio_min is not None:
            where += " AND f.precio >= :precio_min"
            params["precio_min"] = filters.precio_min
        if filters.precio_max is not None:
            where += " AND f.precio <= :precio_max"
            params["precio_max"] = filters.precio_max
        if filters.cantidad_min is not None:
            where += " AND f.cantidad >= :cantidad_min"
            params["cantidad_min"] = filters.cantidad_min
        if filters.cantidad_max is not None:
            where += " AND f.cantidad <= :cantidad_max"
            params["cantidad_max"] = filters.cantidad_max
        return where, params

    async def _fetch_facturas_agrupadas(
        self,
        filters: FilterParams,
        inicio: Optional[date] = None,
        fin: Optional[date] = None,
        extra_select: str = "",
    ) -> List[Dict[str, Any]]:
        where, params = self._facturas_where(filters, inicio, fin)
        cte = self._facturas_cte_sql(extra_select).format(where=where)
        rows = await self._execute(f"{cte} SELECT * FROM facturas_agrupadas", params)
        return [dict(r._asdict()) for r in rows]

    def _bucket_series(
        self,
        invoices: List[Dict[str, Any]],
        inicio: date,
        fin: date,
        bucket: str,
    ) -> List[Dict[str, Any]]:
        """bucket: 'semana' | 'mes'"""
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for inv in invoices:
            fd = self._parse_fecha(inv.get("fecha"))
            if fd is None or fd < inicio or fd > fin:
                continue
            if bucket == "semana":
                key = str(self._week_start(fd))
            else:
                key = fd.strftime("%Y-%m")
            buckets.setdefault(key, []).append(inv)

        out: List[Dict[str, Any]] = []
        for periodo in sorted(buckets.keys()):
            res = self.resumen_ventana(buckets[periodo])
            res["periodo"] = periodo
            out.append(res)
        return out

    async def _resumen_temporal(self, filters: FilterParams) -> Dict[str, Any]:
        _, fin = self._periodo(filters)
        inicio_ext = fin - timedelta(days=59)
        invoices = await self._fetch_facturas_agrupadas(filters, inicio_ext, fin)

        hoy = fin
        ayer = fin - timedelta(days=1)
        d7_start = fin - timedelta(days=6)
        d7_prev_start = fin - timedelta(days=13)
        d7_prev_end = fin - timedelta(days=7)
        d30_start = fin - timedelta(days=29)
        d30_prev_start = fin - timedelta(days=59)
        d30_prev_end = fin - timedelta(days=30)

        res_hoy = self.resumen_ventana(self.filter_invoices(invoices, hoy, hoy))
        res_7d = self.resumen_ventana(self.filter_invoices(invoices, d7_start, fin))
        res_30d = self.resumen_ventana(self.filter_invoices(invoices, d30_start, fin))
        res_ayer = self.resumen_ventana(self.filter_invoices(invoices, ayer, ayer))
        res_7d_prev = self.resumen_ventana(self.filter_invoices(invoices, d7_prev_start, d7_prev_end))
        res_30d_prev = self.resumen_ventana(self.filter_invoices(invoices, d30_prev_start, d30_prev_end))

        return {
            "hoy": res_hoy,
            "ultimos_7d": res_7d,
            "ultimos_30d": res_30d,
            "variacion": {
                "hoy_vs_ayer": self.variacion_ventana(res_hoy, res_ayer),
                "ultimos_7d_vs_previos_7d": self.variacion_ventana(res_7d, res_7d_prev),
                "ultimos_30d_vs_previos_30d": self.variacion_ventana(res_30d, res_30d_prev),
            },
        }

    async def _precio_promedio_linea(self, filters: FilterParams) -> float:
        where, params = self._facturas_where(filters)
        rows = await self._execute(
            f"SELECT AVG(f.precio) AS avg_precio FROM facturas f LEFT JOIN items i ON i.nombre = f.nombre {where}",
            params,
        )
        if not rows:
            return 0.0
        return round(float(rows[0]._asdict().get("avg_precio") or 0), 2)

    async def _compras_por_proveedor_total(self, filters: FilterParams) -> float:
        inicio, fin = self._periodo(filters)
        rows = await self._execute(
            """
            SELECT COALESCE(SUM(precio * COALESCE(cantidad, 1)), 0) AS total
            FROM facturas_proveedor
            WHERE fecha BETWEEN :fecha_inicio AND :fecha_fin
            """,
            {"fecha_inicio": inicio, "fecha_fin": fin},
        )
        if not rows:
            return 0.0
        return round(float(rows[0]._asdict().get("total") or 0), 2)

    async def _variacion_vs_periodo_anterior(
        self, filters: FilterParams, ventas_actuales: float
    ) -> Optional[float]:
        inicio, fin = self._periodo(filters)
        dias = max((fin - inicio).days + 1, 1)
        prev_fin = inicio - timedelta(days=1)
        prev_inicio = prev_fin - timedelta(days=dias - 1)
        prev_rows = await self._fetch_facturas_agrupadas(filters, prev_inicio, prev_fin)
        ventas_prev = self.compute_ticket_metrics(prev_rows)["ventas_totales"]
        return self.safe_pct(ventas_actuales - ventas_prev, ventas_prev)

    async def _margen_diario(self, filters: FilterParams) -> List[Dict[str, Any]]:
        ventas_service = VentasService(self.db)
        ventas, _ = await ventas_service.get_ventas(filters, max_rows=50000)
        por_dia: Dict[date, Dict[str, float]] = {}
        for v in ventas:
            fd = v.fecha_venta
            if fd not in por_dia:
                por_dia[fd] = {"ventas": 0.0, "margen": 0.0, "ventas_costo": 0.0}
            por_dia[fd]["ventas"] += float(v.total_venta or 0)
            if v.precio_promedio_compra is not None:
                por_dia[fd]["ventas_costo"] += float(v.total_venta or 0)
                por_dia[fd]["margen"] += float(v.total_margen or 0)
        rows = []
        for fd in sorted(por_dia.keys()):
            d = por_dia[fd]
            rows.append(
                {
                    "fecha": str(fd),
                    "ventas": round(d["ventas"], 2),
                    "margen_bruto": round(d["margen"], 2),
                    "margen_bruto_pct": self.safe_pct(d["margen"], d["ventas_costo"]) or 0,
                }
            )
        return rows

    async def _execute(self, query: str, params: Optional[Dict[str, Any]] = None):
        try:
            result = await self.db.execute(text(query), params or {})
            return result.fetchall()
        except Exception:
            return []

    async def _ventas_tickets(self, filters: FilterParams) -> Dict[str, Any]:
        invoices = await self._fetch_facturas_agrupadas(filters)
        base = self.compute_ticket_metrics(invoices)

        dias_periodo = max((self._periodo(filters)[1] - self._periodo(filters)[0]).days + 1, 1)
        base["venta_diaria_promedio"] = base["ventas_totales"] / dias_periodo

        clientes_identificados = {}
        for row in invoices:
            cliente = str(row.get("cliente") or "").strip()
            if cliente.lower() in self.CONSUMIDOR_GENERICO:
                continue
            clientes_identificados.setdefault(cliente, 0)
            clientes_identificados[cliente] += 1
        recurrentes = len([c for c in clientes_identificados.values() if c > 1])
        base["clientes_identificados"] = len(clientes_identificados)
        base["repeat_customer_rate_proxy"] = (
            recurrentes / len(clientes_identificados) * 100 if clientes_identificados else 0
        )
        return base

    async def _series_ventas(self, filters: FilterParams) -> Dict[str, List[Dict[str, Any]]]:
        where, params = self._facturas_where(filters)
        rows = await self._execute(
            f"""
            WITH facturas_agrupadas AS (
                SELECT
                    f.id,
                    MIN(f.fecha) AS fecha,
                    MAX(f.vendedor) AS vendedor,
                    MAX(f.metodo) AS metodo,
                    COALESCE(MAX(f.totalfact), SUM(COALESCE(f.total, f.precio * f.cantidad))) AS total_factura,
                    SUM(COALESCE(f.cantidad, 0)) AS unidades,
                    COUNT(*) AS lineas
                FROM facturas f
                LEFT JOIN items i ON i.nombre = f.nombre
                {where}
                GROUP BY f.id
            )
            SELECT fecha, SUM(total_factura) AS ventas, COUNT(*) AS facturas,
                   SUM(unidades) AS unidades, SUM(lineas) AS lineas
            FROM facturas_agrupadas
            GROUP BY fecha
            ORDER BY fecha
            """,
            params,
        )
        ventas_diarias = []
        for idx, row in enumerate(rows):
            d = row._asdict()
            ventas = float(d.get("ventas") or 0)
            prev = ventas_diarias[max(0, idx - 6):idx]
            window_sum = sum(float(p["ventas"]) for p in prev) + ventas
            window_len = len(prev) + 1
            facturas_dia = int(d.get("facturas") or 0)
            lineas_dia = float(d.get("lineas") or 0)
            ventas_diarias.append(
                {
                    "fecha": str(d["fecha"]),
                    "ventas": round(ventas, 2),
                    "media_movil_7d": round(window_sum / window_len, 2),
                    "facturas": facturas_dia,
                    "unidades": float(d.get("unidades") or 0),
                    "lineas": lineas_dia,
                    "ticket_promedio": round(ventas / facturas_dia, 2) if facturas_dia else 0,
                }
            )
        ticket_diario = [
            {
                "fecha": r["fecha"],
                "ticket_promedio": r["ticket_promedio"],
                "unidades_por_ticket": round(r["unidades"] / r["facturas"], 2) if r["facturas"] else 0,
                "lineas": r["lineas"],
            }
            for r in ventas_diarias
        ]

        vendedor_rows = await self._execute(
            f"""
            WITH facturas_agrupadas AS (
                SELECT
                    f.id,
                    MAX(f.vendedor) AS vendedor,
                    COALESCE(MAX(f.totalfact), SUM(COALESCE(f.total, f.precio * f.cantidad))) AS total_factura,
                    SUM(COALESCE(f.cantidad, 0)) AS unidades,
                    COUNT(*) AS lineas
                FROM facturas f
                LEFT JOIN items i ON i.nombre = f.nombre
                {where}
                GROUP BY f.id
            )
            SELECT COALESCE(vendedor, 'Sin vendedor') AS vendedor,
                   COUNT(*) AS facturas,
                   SUM(total_factura) AS ventas,
                   SUM(unidades) AS unidades,
                   SUM(lineas) AS lineas
            FROM facturas_agrupadas
            GROUP BY vendedor
            ORDER BY ventas DESC
            LIMIT 12
            """,
            params,
        )
        por_vendedor = [
            {
                "vendedor": r._asdict()["vendedor"],
                "facturas": int(r._asdict().get("facturas") or 0),
                "ticket_promedio": round(float(r._asdict().get("ventas") or 0) / int(r._asdict().get("facturas") or 1), 2),
                "unidades_por_ticket": round(float(r._asdict().get("unidades") or 0) / int(r._asdict().get("facturas") or 1), 2),
                "lineas_por_ticket": round(float(r._asdict().get("lineas") or 0) / int(r._asdict().get("facturas") or 1), 2),
            }
            for r in vendedor_rows
        ]

        metodo_rows = await self._execute(
            f"""
            WITH facturas_agrupadas AS (
                SELECT
                    f.id,
                    MAX(f.metodo) AS metodo,
                    COALESCE(MAX(f.totalfact), SUM(COALESCE(f.total, f.precio * f.cantidad))) AS total_factura,
                    SUM(COALESCE(f.cantidad, 0)) AS unidades,
                    COUNT(*) AS lineas
                FROM facturas f
                LEFT JOIN items i ON i.nombre = f.nombre
                {where}
                GROUP BY f.id
            )
            SELECT COALESCE(metodo, 'Sin método') AS metodo,
                   COUNT(*) AS facturas,
                   SUM(total_factura) AS ventas,
                   SUM(unidades) AS unidades,
                   SUM(lineas) AS lineas
            FROM facturas_agrupadas
            GROUP BY metodo
            ORDER BY ventas DESC
            LIMIT 12
            """,
            params,
        )
        por_metodo = [
            {
                "metodo": r._asdict()["metodo"],
                "facturas": int(r._asdict().get("facturas") or 0),
                "ticket_promedio": round(float(r._asdict().get("ventas") or 0) / int(r._asdict().get("facturas") or 1), 2),
                "unidades_por_ticket": round(float(r._asdict().get("unidades") or 0) / int(r._asdict().get("facturas") or 1), 2),
                "lineas_por_ticket": round(float(r._asdict().get("lineas") or 0) / int(r._asdict().get("facturas") or 1), 2),
            }
            for r in metodo_rows
        ]
        inicio, fin = self._periodo(filters)
        period_invoices = await self._fetch_facturas_agrupadas(filters, inicio, fin)
        return {
            "ventas_diarias": ventas_diarias,
            "ticket_diario": ticket_diario,
            "ticket_por_vendedor": por_vendedor,
            "ticket_por_metodo": por_metodo,
            "ventas_por_semana": self._bucket_series(period_invoices, inicio, fin, "semana"),
            "ventas_por_mes": self._bucket_series(period_invoices, inicio, fin, "mes"),
        }

    async def _margenes(self, filters: FilterParams, ventas_totales: float) -> Dict[str, Any]:
        ventas_service = VentasService(self.db)
        ventas, _ = await ventas_service.get_ventas(filters, max_rows=50000)
        ventas_con_costo = [v for v in ventas if v.precio_promedio_compra is not None]
        ventas_con_costo_total = sum(float(v.total_venta or 0) for v in ventas_con_costo)
        cogs = sum(float(v.precio_promedio_compra or 0) * float(v.cantidad or 0) for v in ventas_con_costo)
        unidades_con_costo = sum(float(v.cantidad or 0) for v in ventas_con_costo)
        margen = ventas_con_costo_total - cogs
        margenes_pct = [float(v.margen_porcentaje) for v in ventas if v.margen_porcentaje is not None]
        margen_promedio_simple = round(sum(margenes_pct) / len(margenes_pct), 2) if margenes_pct else 0
        return {
            "ventas_con_costo": round(ventas_con_costo_total, 2),
            "cogs_estimado": round(cogs, 2),
            "margen_bruto": round(margen, 2),
            "margen_bruto_pct": self.safe_pct(margen, ventas_con_costo_total) or 0,
            "margen_unitario_promedio_ponderado": round(margen / unidades_con_costo, 2) if unidades_con_costo else 0,
            "cobertura_costo_pct": self.safe_pct(ventas_con_costo_total, ventas_totales) or 0,
            "margen_promedio_simple": margen_promedio_simple,
            "ventas_raw": ventas,
        }

    async def _ventas_por_familia(self, filters: FilterParams) -> List[Dict[str, Any]]:
        ventas_service = VentasService(self.db)
        ventas, _ = await ventas_service.get_ventas(filters, max_rows=50000)
        familias: Dict[str, Dict[str, float]] = {}
        for v in ventas:
            familia = v.familia or "Sin familia"
            familias.setdefault(familia, {"ventas": 0, "margen": 0, "cogs": 0})
            familias[familia]["ventas"] += float(v.total_venta or 0)
            if v.precio_promedio_compra is not None:
                familias[familia]["cogs"] += float(v.precio_promedio_compra or 0) * float(v.cantidad or 0)
                familias[familia]["margen"] += float(v.total_margen or 0)
        rows = []
        for familia, d in familias.items():
            rows.append(
                {
                    "familia": familia,
                    "ventas": round(d["ventas"], 2),
                    "margen_bruto": round(d["margen"], 2),
                    "margen_pct": self.safe_pct(d["margen"], d["ventas"]) or 0,
                }
            )
        rows.sort(key=lambda x: x["ventas"], reverse=True)
        return rows[:12]

    async def _inventario(self, margen_bruto: float, filters: Optional[FilterParams] = None) -> Dict[str, Any]:
        from app.services.inventario import InventarioService
        from app.services.abc import ABCService

        inv = InventarioService(self.db)
        productos = await inv.get_inventario_completo()
        abc_map: Dict[str, str] = {}
        if filters is not None:
            try:
                abc_result = await ABCService(VentasService(self.db)).get_analisis_abc(filters, "ventas")
                abc_map = {
                    p["nombre"]: p.get("categoria", "C")
                    for p in abc_result.get("productos", [])
                }
            except Exception:
                pass
        if not productos:
            return {
                "metrics": {
                    "valor_inventario_estimado": 0,
                    "stockout_rate_sku": 0,
                    "sell_through_proxy": 0,
                    "rotacion_unidades_proxy": 0,
                    "dead_stock_value_proxy": 0,
                    "excess_stock_value": 0,
                    "stock_sano_pct": 0,
                    "stock_riesgo_pct": 0,
                    "stock_exceso_pct": 0,
                    "gmroi_proxy": 0,
                },
                "scatter": [],
                "salud": {},
            }

        valor_total = sum(float(p.get("valor_inventario") or 0) for p in productos)
        activos = [p for p in productos if float(p.get("cantidad_vendida_30d") or 0) > 0]
        sin_stock = [p for p in activos if float(p.get("stock_actual") or 0) <= 0]
        unidades_30d = sum(float(p.get("cantidad_vendida_30d") or 0) for p in productos)
        stock_actual = sum(float(p.get("stock_actual") or 0) for p in productos)
        dead_stock = [
            p
            for p in productos
            if float(p.get("stock_actual") or 0) > 0 and float(p.get("cantidad_vendida_30d") or 0) == 0
        ]
        exceso = [p for p in productos if (p.get("dias_cobertura") is None or float(p.get("dias_cobertura") or 0) > 60)]
        riesgo = [p for p in productos if "Cr" in str(p.get("estado_stock")) or "Bajo" in str(p.get("estado_stock"))]
        sano = [
            p
            for p in productos
            if p not in riesgo and p not in exceso
        ]
        rotaciones = [float(p.get("rotacion") or 0) for p in productos if p.get("rotacion") is not None]
        metrics = {
            "valor_inventario_estimado": round(valor_total, 2),
            "stockout_rate_sku": self.safe_pct(len(sin_stock), len(activos)) or 0,
            "sell_through_proxy": self.safe_pct(unidades_30d, unidades_30d + stock_actual) or 0,
            "rotacion_unidades_proxy": round(sum(rotaciones) / len(rotaciones), 2) if rotaciones else 0,
            "dead_stock_value_proxy": round(sum(float(p.get("valor_inventario") or 0) for p in dead_stock), 2),
            "excess_stock_value": round(sum(float(p.get("valor_inventario") or 0) for p in exceso), 2),
            "stock_sano_pct": self.safe_pct(len(sano), len(productos)) or 0,
            "stock_riesgo_pct": self.safe_pct(len(riesgo), len(productos)) or 0,
            "stock_exceso_pct": self.safe_pct(len(exceso), len(productos)) or 0,
            "gmroi_proxy": round(margen_bruto / valor_total, 3) if valor_total > 0 else 0,
        }
        scatter = [
            {
                "nombre": p.get("nombre"),
                "dias_cobertura": p.get("dias_cobertura") or 999,
                "margen_pct": p.get("margen_porcentaje") or 0,
                "valor_inventario": p.get("valor_inventario") or 0,
                "estado": p.get("estado_stock"),
                "categoria": abc_map.get(p.get("nombre"), "C"),
            }
            for p in sorted(productos, key=lambda x: float(x.get("valor_inventario") or 0), reverse=True)[:120]
        ]
        return {"metrics": metrics, "scatter": scatter, "salud": {k: metrics[k] for k in ("stock_sano_pct", "stock_riesgo_pct", "stock_exceso_pct")}}

    async def _abc_pareto(self, filters: FilterParams) -> List[Dict[str, Any]]:
        from app.services.abc import ABCService

        result = await ABCService(VentasService(self.db)).get_analisis_abc(filters, "ventas")
        return [
            {
                "nombre": p.get("nombre"),
                "ventas": p.get("total_venta"),
                "porcentaje": p.get("porcentaje"),
                "acumulado": p.get("porcentaje_acumulado"),
                "categoria": p.get("categoria") or p.get("clasificacion"),
            }
            for p in result.get("productos", [])[:30]
        ]

    async def _proveedores(self) -> Dict[str, Any]:
        fact_service = FacturasProveedorService(self.db)
        resumen = await fact_service.get_resumen()
        por_proveedor = sorted(
            resumen.get("por_proveedor", []),
            key=lambda x: float(x.get("monto_vencido", 0) or 0) + float(x.get("monto_proximo", 0) or 0),
            reverse=True,
        )[:10]

        rows = await self._execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (nombre, proveedor)
                    nombre, proveedor, precio, fecha
                FROM facturas_proveedor
                WHERE nombre IS NOT NULL AND proveedor IS NOT NULL AND precio IS NOT NULL AND precio > 0
                ORDER BY nombre, proveedor, fecha DESC
            ),
            min_price AS (
                SELECT nombre, MIN(precio) AS precio_min
                FROM latest
                GROUP BY nombre
            )
            SELECT l.nombre, l.proveedor, l.precio AS precio_proveedor, m.precio_min,
                   CASE WHEN m.precio_min > 0 THEN ((l.precio - m.precio_min) / m.precio_min * 100) ELSE 0 END AS variance_pct
            FROM latest l
            JOIN min_price m ON m.nombre = l.nombre
            WHERE l.precio > m.precio_min
            ORDER BY variance_pct DESC
            LIMIT 10
            """
        )
        variance = [
            {
                "nombre": r._asdict().get("nombre"),
                "proveedor": r._asdict().get("proveedor"),
                "precio_proveedor": float(r._asdict().get("precio_proveedor") or 0),
                "precio_min": float(r._asdict().get("precio_min") or 0),
                "variance_pct": round(float(r._asdict().get("variance_pct") or 0), 2),
            }
            for r in rows
        ]
        return {"resumen": resumen, "por_proveedor": por_proveedor, "variance": variance}

    async def get_resumen(self, filters: FilterParams) -> Dict[str, Any]:
        inicio, fin = self._periodo(filters)
        tickets = await self._ventas_tickets(filters)
        series = await self._series_ventas(filters)
        margenes = await self._margenes(filters, float(tickets.get("ventas_totales") or 0))
        inv = await self._inventario(float(margenes.get("margen_bruto") or 0), filters)
        proveedores = await self._proveedores()
        forecast = await PrediccionesService(VentasService(self.db)).get_backtest_metricas(filters, semanas=4)
        resumen_temporal = await self._resumen_temporal(filters)
        precio_linea = await self._precio_promedio_linea(filters)
        compras_prov = await self._compras_por_proveedor_total(filters)
        variacion_periodo = await self._variacion_vs_periodo_anterior(
            filters, float(tickets.get("ventas_totales") or 0)
        )
        margen_diario = await self._margen_diario(filters)

        kpis: Dict[str, SectorMetric] = {
            "ventas_totales": self.metric("Ventas totales", round(tickets["ventas_totales"], 2), "SUM(facturas.total) o totalfact agrupado por id", "standard", "facturas"),
            "unidades_vendidas": self.metric("Unidades vendidas", int(tickets["unidades_vendidas"]), "SUM(cantidad)", "standard", "facturas"),
            "lineas_vendidas": self.metric("Líneas vendidas", int(tickets["lineas_vendidas"]), "COUNT(*)", "standard", "facturas"),
            "asp": self.metric("ASP", round(tickets["asp"], 2), "Ventas / unidades", "standard", "facturas"),
            "precio_promedio_linea": self.metric(
                "Precio promedio línea",
                precio_linea,
                "AVG(precio) por línea de factura",
                "standard",
                "No confundir con ASP ponderado",
            ),
            "variacion_vs_periodo_anterior": self.metric(
                "Variación vs periodo anterior",
                variacion_periodo,
                "(Ventas periodo - ventas periodo previo) / ventas periodo previo",
                "standard",
                "Periodo previo del mismo tamaño; fallback 30d",
            ),
            "compras_por_proveedor": self.metric(
                "Compras a proveedores",
                compras_prov,
                "SUM(precio * cantidad) facturas_proveedor",
                "standard",
                "facturas_proveedor",
            ),
            "facturas_totales": self.metric("Facturas", tickets["facturas_totales"], "COUNT(DISTINCT facturas.id)", "standard", "facturas.id"),
            "ticket_promedio_real": self.metric("Ticket promedio real", round(tickets["ticket_promedio_real"], 2), "SUM(totalfact por factura) / COUNT(DISTINCT id)", "standard", "facturas agrupadas por id"),
            "unidades_por_ticket": self.metric("Unidades por ticket", round(tickets["unidades_por_ticket"], 2), "SUM(cantidad) / COUNT(DISTINCT id)", "standard", "facturas"),
            "lineas_por_ticket": self.metric("Líneas por ticket", round(tickets["lineas_por_ticket"], 2), "COUNT(líneas) / COUNT(DISTINCT id)", "standard", "facturas"),
            "venta_diaria_promedio": self.metric("Venta diaria promedio", round(tickets["venta_diaria_promedio"], 2), "Ventas / días del periodo", "standard", "facturas"),
            "margen_promedio_simple": self.metric(
                "Margen % simple (debug)",
                margenes.get("margen_promedio_simple"),
                "AVG(margen_porcentaje) por línea",
                "proxy",
                "Secundario; usar margen bruto % ponderado",
            ),
            "ventas_con_costo": self.metric("Ventas con costo", margenes["ventas_con_costo"], "SUM(ventas con precio_promedio_compra)", "standard", "reportes_ventas_30dias"),
            "cogs_estimado": self.metric("COGS estimado", margenes["cogs_estimado"], "SUM(precio_promedio_compra * cantidad)", "standard", "reportes_ventas_30dias"),
            "margen_bruto": self.metric("Margen bruto", margenes["margen_bruto"], "Ventas con costo - COGS", "standard", "reportes_ventas_30dias"),
            "margen_bruto_pct": self.metric("Margen bruto %", margenes["margen_bruto_pct"], "Margen bruto / ventas con costo", "standard", "Solo ventas con costo"),
            "margen_unitario_promedio_ponderado": self.metric("Margen unitario ponderado", margenes["margen_unitario_promedio_ponderado"], "Margen bruto / unidades con costo", "standard", "reportes_ventas_30dias"),
            "cobertura_costo_pct": self.metric("Cobertura costo", margenes["cobertura_costo_pct"], "Ventas con costo / ventas totales", "standard", "Calidad de margen"),
            "clientes_identificados": self.metric("Clientes identificados", tickets["clientes_identificados"], "COUNT(DISTINCT cliente) excluyendo Consumidor final", "proxy", "La mayoría puede estar como Consumidor final"),
            "repeat_customer_rate_proxy": self.metric("Recompra proxy", round(tickets["repeat_customer_rate_proxy"], 2), "Clientes identificados con 2+ facturas / clientes identificados", "proxy", "Depende de captura de cliente"),
            "valor_inventario_estimado": self.metric("Valor inventario", inv["metrics"]["valor_inventario_estimado"], "Stock * costo; fallback precio venta", "proxy", "items + costo disponible"),
            "stockout_rate_sku": self.metric("Stockout SKU", inv["metrics"]["stockout_rate_sku"], "SKU activos sin stock / SKU activos", "proxy", "Aproxima quiebre por stock actual"),
            "sell_through_proxy": self.metric("Sell-through proxy", inv["metrics"]["sell_through_proxy"], "Unidades vendidas 30d / (vendidas 30d + stock actual)", "proxy", "Sin inventario inicial"),
            "rotacion_unidades_proxy": self.metric("Rotación unidades proxy", inv["metrics"]["rotacion_unidades_proxy"], "Unidades anualizadas / stock actual", "proxy", "Sin stock promedio histórico"),
            "dead_stock_value_proxy": self.metric("Dead stock proxy", inv["metrics"]["dead_stock_value_proxy"], "Valor con stock y ventas 0 en 30d", "proxy", "Ventana de 30 días"),
            "excess_stock_value": self.metric("Exceso inventario", inv["metrics"]["excess_stock_value"], "Valor con cobertura > 60 días", "proxy", "Cobertura por venta reciente"),
            "stock_sano_pct": self.metric("Stock sano", inv["metrics"]["stock_sano_pct"], "SKU normal / SKU totales", "proxy", "Clasificación por cobertura"),
            "stock_riesgo_pct": self.metric("Stock en riesgo", inv["metrics"]["stock_riesgo_pct"], "SKU crítico+bajo / SKU totales", "proxy", "Clasificación por cobertura"),
            "stock_exceso_pct": self.metric("Stock en exceso", inv["metrics"]["stock_exceso_pct"], "SKU exceso / SKU totales", "proxy", "Clasificación por cobertura"),
            "gmroi_proxy": self.metric("GMROI proxy", inv["metrics"]["gmroi_proxy"], "Margen bruto periodo / valor inventario actual", "proxy", "Sin inventario promedio histórico"),
            "monto_vencido": self.metric("Monto vencido proveedores", proveedores["resumen"].get("monto_vencido", 0), "SUM facturas proveedor vencidas", "standard", "facturas_proveedor"),
            "monto_proximo": self.metric("Monto próximo proveedores", proveedores["resumen"].get("monto_proximo", 0), "SUM facturas proveedor próximas", "standard", "facturas_proveedor"),
            "facturas_vencidas": self.metric("Facturas vencidas", proveedores["resumen"].get("facturas_vencidas", 0), "COUNT facturas vencidas", "standard", "facturas_proveedor"),
            "wape_forecast": self.metric("WAPE forecast", forecast.get("wape_promedio"), "SUM(|real - pred|) / SUM(real)", "standard", "Backtest 4 semanas"),
            "mape_forecast": self.metric("MAPE forecast", forecast.get("mape_promedio"), "AVG(|real - pred| / real)", "standard", "Backtest 4 semanas"),
            "mae_forecast": self.metric("MAE forecast", forecast.get("mae_promedio"), "AVG(|real - pred|)", "standard", "Backtest 4 semanas"),
            "rmse_forecast": self.metric("RMSE forecast", forecast.get("rmse_promedio"), "SQRT(AVG(error^2))", "standard", "Backtest 4 semanas"),
            "bias_forecast_pct": self.metric("Bias forecast", forecast.get("bias_pct_promedio"), "SUM(pred - real) / SUM(real)", "standard", "Positivo = sobreestima"),
        }

        return {
            "periodo": {"fecha_inicio": str(inicio), "fecha_fin": str(fin)},
            "kpis": kpis,
            "resumen_temporal": resumen_temporal,
            "ventas_diarias": series["ventas_diarias"],
            "ticket_diario": series["ticket_diario"],
            "ventas_por_semana": series["ventas_por_semana"],
            "ventas_por_mes": series["ventas_por_mes"],
            "ventas_por_familia": await self._ventas_por_familia(filters),
            "margen_diario": margen_diario,
            "ticket_por_vendedor": series["ticket_por_vendedor"],
            "ticket_por_metodo": series["ticket_por_metodo"],
            "inventario_scatter": inv["scatter"],
            "salud_inventario": inv["salud"],
            "abc_pareto": await self._abc_pareto(filters),
            "forecast_backtest": forecast,
            "proveedores_vencimientos": proveedores["por_proveedor"],
            "supplier_price_variance": proveedores["variance"],
        }

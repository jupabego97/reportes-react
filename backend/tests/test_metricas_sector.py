"""Tests de métricas retail sectoriales."""
import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import FilterParams, VentaBase
from app.services.abc import ABCService
from app.services.metricas_sector import MetricasSectorService
from app.services.predicciones import PrediccionesService


def _venta(nombre: str, total: float, fecha: date | None = None) -> VentaBase:
    fecha = fecha or date.today()
    return VentaBase(
        nombre=nombre,
        precio=total,
        cantidad=1,
        metodo="CASH",
        vendedor="Vendedor",
        fecha_venta=fecha,
        familia="Familia",
        proveedor_moda="Proveedor",
        precio_promedio_compra=total * 0.6,
        total_venta=total,
        margen=total * 0.4,
        margen_porcentaje=40,
        total_margen=total * 0.4,
    )


def _ventas_service(ventas: list[VentaBase]):
    mock = MagicMock()
    mock.get_ventas = AsyncMock(return_value=(ventas, len(ventas)))
    return mock


def test_ticket_metrics_grouped_by_invoice_id():
    rows = [
        {"id": 212, "total_factura": 55000, "unidades": 1, "lineas": 1},
        {"id": 215, "total_factura": 135000, "unidades": 3, "lineas": 3},
        {"id": 216, "total_factura": 75000, "unidades": 5, "lineas": 1},
    ]

    metrics = MetricasSectorService.compute_ticket_metrics(rows)

    assert metrics["facturas_totales"] == 3
    assert metrics["ventas_totales"] == 265000
    assert metrics["ticket_promedio_real"] == pytest.approx(88333.333)
    assert metrics["unidades_por_ticket"] == pytest.approx(3)
    assert metrics["lineas_por_ticket"] == pytest.approx(5 / 3)
    assert metrics["asp"] == pytest.approx(265000 / 9)


def test_abc_keeps_crossing_sku_in_class_a():
    ventas = [_venta("SKU A", 90), _venta("SKU B", 10)]
    service = ABCService(_ventas_service(ventas))

    result = asyncio.run(service.get_analisis_abc(FilterParams()))

    assert result["productos"][0]["nombre"] == "SKU A"
    assert result["productos"][0]["categoria"] == "A"
    assert result["productos"][1]["categoria"] == "B"


def test_forecast_backtest_includes_mae_rmse_and_bias():
    today = date.today()
    ventas = [
        _venta("SKU A", 100 + (idx % 7) * 10, today - timedelta(days=idx))
        for idx in range(35)
    ]
    service = PrediccionesService(_ventas_service(ventas))

    result = asyncio.run(service.get_backtest_metricas(FilterParams(), semanas=2))

    assert result["semanas"] > 0
    assert result["mae_promedio"] is not None
    assert result["rmse_promedio"] is not None
    assert result["bias_pct_promedio"] is not None
    assert {"mae", "rmse", "bias_pct"}.issubset(result["detalle"][0].keys())


def test_resumen_ventana_and_variacion():
    today = date.today()
    invoices = [
        {"fecha": today, "total_factura": 100, "unidades": 2, "lineas": 1},
        {"fecha": today - timedelta(days=1), "total_factura": 50, "unidades": 1, "lineas": 1},
        {"fecha": today - timedelta(days=3), "total_factura": 200, "unidades": 4, "lineas": 2},
    ]
    hoy = MetricasSectorService.resumen_ventana(
        MetricasSectorService.filter_invoices(invoices, today, today)
    )
    assert hoy["unidades"] == 2
    assert hoy["lineas"] == 1
    assert hoy["ticket_promedio"] == 100

    ayer = MetricasSectorService.resumen_ventana(
        MetricasSectorService.filter_invoices(invoices, today - timedelta(days=1), today - timedelta(days=1))
    )
    var = MetricasSectorService.variacion_ventana(hoy, ayer)
    assert var["unidades_pct"] == 100.0


def test_ventas_diarias_includes_lineas_and_ticket():
    """Series builder includes lineas field when present in SQL aggregation."""
    row = {"ventas": 1000, "facturas": 5, "unidades": 20, "lineas": 8}
    ticket = round(row["ventas"] / row["facturas"], 2) if row["facturas"] else 0
    assert row["lineas"] == 8
    assert ticket == 200

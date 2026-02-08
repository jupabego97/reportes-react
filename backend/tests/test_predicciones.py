"""
Tests para el servicio de predicciones.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.predicciones import PrediccionesService
from app.models.schemas import FilterParams, VentaBase


def _make_venta(fecha: date, total: float, nombre: str = "Producto A") -> VentaBase:
    """Helper para crear ventas de prueba."""
    return VentaBase(
        nombre=nombre,
        precio=total,
        cantidad=1,
        metodo="Efectivo",
        vendedor="Vendedor 1",
        fecha_venta=fecha,
        familia="Familia A",
        proveedor_moda="Proveedor 1",
        precio_promedio_compra=total * 0.6,
        total_venta=total,
        margen=total * 0.4,
        margen_porcentaje=40.0,
        total_margen=total * 0.4,
    )


def _create_mock_ventas_service(ventas: list):
    """Crea un mock de VentasService que retorna las ventas dadas."""
    mock = MagicMock()
    mock.get_ventas = AsyncMock(return_value=(ventas, len(ventas)))
    return mock


@pytest.mark.asyncio
class TestPrediccionesService:
    """Tests para el servicio de predicciones."""

    async def test_empty_data_returns_zeros(self):
        service = PrediccionesService(_create_mock_ventas_service([]))
        result = await service.get_predicciones(FilterParams())
        
        assert result.venta_diaria_promedio == 0
        assert result.tendencia_diaria == 0
        assert result.prediccion_semanal == 0
        assert result.prediccion_mensual == 0
        assert result.historico == []
        assert result.predicciones == []

    async def test_insufficient_data_returns_basic_metrics(self):
        """Con menos de 7 días, no debe generar predicciones."""
        hoy = date.today()
        ventas = [_make_venta(hoy - timedelta(days=i), 100) for i in range(3)]
        
        service = PrediccionesService(_create_mock_ventas_service(ventas))
        result = await service.get_predicciones(FilterParams())
        
        assert result.venta_diaria_promedio > 0
        assert len(result.historico) == 3
        assert len(result.predicciones) == 0

    async def test_sufficient_data_generates_predictions(self):
        """Con 14+ días de datos, debe generar predicciones."""
        hoy = date.today()
        ventas = [_make_venta(hoy - timedelta(days=i), 100 + i * 5) for i in range(20)]
        
        service = PrediccionesService(_create_mock_ventas_service(ventas))
        result = await service.get_predicciones(FilterParams())
        
        assert result.venta_diaria_promedio > 0
        assert len(result.historico) == 20
        assert len(result.predicciones) == 14  # DIAS_PREDICCION
        assert len(result.predicciones_upper) == 14
        assert len(result.predicciones_lower) == 14

    async def test_predictions_are_non_negative(self):
        """Las predicciones nunca deben ser negativas."""
        hoy = date.today()
        ventas = [_make_venta(hoy - timedelta(days=i), 10 + i * 0.1) for i in range(15)]
        
        service = PrediccionesService(_create_mock_ventas_service(ventas))
        result = await service.get_predicciones(FilterParams())
        
        for pred in result.predicciones:
            assert pred.ventas >= 0
        for val in result.predicciones_lower:
            assert val >= 0

    async def test_confidence_band_grows_with_distance(self):
        """La banda de confianza debe crecer con la distancia de predicción."""
        hoy = date.today()
        ventas = [_make_venta(hoy - timedelta(days=i), 100 + i * 2) for i in range(20)]
        
        service = PrediccionesService(_create_mock_ventas_service(ventas))
        result = await service.get_predicciones(FilterParams())
        
        if len(result.predicciones_upper) >= 2 and len(result.predicciones_lower) >= 2:
            band_width_first = result.predicciones_upper[0] - result.predicciones_lower[0]
            band_width_last = result.predicciones_upper[-1] - result.predicciones_lower[-1]
            assert band_width_last >= band_width_first

    async def test_weekly_pattern_has_7_days(self):
        """Debe retornar patrón para los 7 días de la semana."""
        hoy = date.today()
        ventas = [_make_venta(hoy - timedelta(days=i), 100) for i in range(14)]
        
        service = PrediccionesService(_create_mock_ventas_service(ventas))
        result = await service.get_predicciones(FilterParams())
        
        assert len(result.ventas_por_dia_semana) == 7
        dias = [d["dia"] for d in result.ventas_por_dia_semana]
        assert "Lunes" in dias
        assert "Domingo" in dias

    async def test_historico_includes_media_movil(self):
        """El histórico debe incluir media móvil."""
        hoy = date.today()
        ventas = [_make_venta(hoy - timedelta(days=i), 100) for i in range(10)]
        
        service = PrediccionesService(_create_mock_ventas_service(ventas))
        result = await service.get_predicciones(FilterParams())
        
        # Todos los puntos históricos deben tener media móvil
        for punto in result.historico:
            assert punto.media_movil_7d is not None


class TestRegresionLinealPonderada:
    """Tests para la regresión lineal ponderada."""

    def test_constant_data_has_zero_slope(self):
        """Datos constantes deben tener pendiente cercana a 0."""
        pendiente, intercepto = PrediccionesService._regresion_lineal_ponderada(
            [100, 100, 100, 100, 100]
        )
        assert abs(pendiente) < 1  # Cercana a 0
        assert abs(intercepto - 100) < 5  # Cercana a 100

    def test_increasing_data_has_positive_slope(self):
        """Datos crecientes deben tener pendiente positiva."""
        pendiente, _ = PrediccionesService._regresion_lineal_ponderada(
            [10, 20, 30, 40, 50]
        )
        assert pendiente > 0

    def test_decreasing_data_has_negative_slope(self):
        """Datos decrecientes deben tener pendiente negativa."""
        pendiente, _ = PrediccionesService._regresion_lineal_ponderada(
            [50, 40, 30, 20, 10]
        )
        assert pendiente < 0

"""
Tests de los modelos de forecast (funciones puras) y del stock de seguridad.
"""
from datetime import date, timedelta

import pytest

from app import forecast_models as fm
from app import semantica


def _serie_constante(unidades: float, dias: int, fin: date) -> dict:
    """Serie con venta constante todos los días."""
    return {fin - timedelta(days=i): unidades for i in range(1, dias + 1)}


def _serie_intermitente(fin: date, dias: int = 60) -> dict:
    """Vende 10 unidades cada 10 días (90% de días en cero)."""
    return {
        fin - timedelta(days=i): (10.0 if i % 10 == 0 else 0.0)
        for i in range(1, dias + 1)
    }


class TestSerieDensa:
    def test_rellena_ceros(self):
        hoy = date(2026, 7, 3)
        ventas = {hoy - timedelta(days=5): 3.0, hoy - timedelta(days=1): 2.0}
        fechas, valores = fm.serie_densa(ventas)
        assert len(fechas) == 5  # días 5,4,3,2,1
        assert valores == [3.0, 0.0, 0.0, 0.0, 2.0]

    def test_vacia(self):
        assert fm.serie_densa({}) == ([], [])


class TestIntermitencia:
    def test_serie_regular_no_es_intermitente(self):
        assert fm.es_intermitente([5, 3, 4, 6, 5, 4]) is False

    def test_serie_mayoria_ceros_es_intermitente(self):
        assert fm.es_intermitente([0, 0, 0, 0, 0, 0, 0, 10, 0, 0]) is True


class TestMetricas:
    def test_wmape_perfecto_es_cero(self):
        assert fm.wmape([10, 20], [10, 20]) == 0.0

    def test_wmape_conocido(self):
        # error total 5 sobre real total 20 → 25%
        assert fm.wmape([10, 10], [12, 13]) == pytest.approx(0.25)

    def test_wmape_sin_ventas_es_none(self):
        assert fm.wmape([0, 0], [1, 2]) is None

    def test_sesgo_positivo_es_sobrepronostico(self):
        assert fm.sesgo_pct([10, 10], [11, 11]) == pytest.approx(10.0)


class TestTSB:
    def test_demanda_constante_intermitente(self):
        # 10 unidades cada 10 días → tasa esperada ~1/día
        serie = [10.0 if i % 10 == 0 else 0.0 for i in range(100)]
        tasa = fm.forecast_tsb(serie)
        assert 0.5 < tasa < 2.0

    def test_serie_vacia(self):
        assert fm.forecast_tsb([]) == 0.0
        assert fm.forecast_tsb([0, 0, 0]) == 0.0


class TestEstacionalidad:
    def test_factores_capturan_dia_fuerte(self):
        # Serie donde el sábado (weekday 5) vende el doble
        hoy = date(2026, 7, 3)
        fechas, valores = [], []
        for i in range(56):
            f = hoy - timedelta(days=i)
            fechas.append(f)
            valores.append(20.0 if f.weekday() == 5 else 10.0)
        factores = fm.factores_dia_semana(fechas, valores)
        assert factores[5] > factores[0]
        assert factores[5] > 1.2

    def test_serie_plana_da_factores_uno(self):
        hoy = date(2026, 7, 3)
        fechas = [hoy - timedelta(days=i) for i in range(28)]
        valores = [10.0] * 28
        factores = fm.factores_dia_semana(fechas, valores)
        for d in range(7):
            assert factores[d] == pytest.approx(1.0, abs=0.01)


class TestForecastProducto:
    def test_serie_constante_pronostica_cerca_del_nivel(self):
        hoy = date(2026, 7, 3)
        ventas = _serie_constante(10.0, 60, hoy)
        pronostico = fm.generar_forecast_producto(ventas, hoy, horizonte_dias=7)
        assert len(pronostico) == 7
        for fd in pronostico:
            assert fd.modelo == "estacional_dow"
            assert fd.p50 == pytest.approx(10.0, rel=0.15)
            assert fd.p10 <= fd.p50 <= fd.p90

    def test_serie_intermitente_usa_tsb(self):
        hoy = date(2026, 7, 3)
        ventas = _serie_intermitente(hoy)
        pronostico = fm.generar_forecast_producto(ventas, hoy, horizonte_dias=7)
        assert pronostico[0].modelo == "intermitente_tsb"
        assert pronostico[0].p10 == 0.0  # lo más probable un día dado: no vende
        assert pronostico[0].p90 >= pronostico[0].p50

    def test_historia_corta_usa_media(self):
        hoy = date(2026, 7, 3)
        ventas = _serie_constante(5.0, 5, hoy)
        pronostico = fm.generar_forecast_producto(ventas, hoy, horizonte_dias=3)
        assert pronostico[0].modelo == "media_movil"
        assert pronostico[0].p50 == pytest.approx(5.0)

    def test_sin_historia_lista_vacia(self):
        assert fm.generar_forecast_producto({}, date(2026, 7, 3)) == []

    def test_cuantiles_ordenados_siempre(self):
        hoy = date(2026, 7, 3)
        ventas = {hoy - timedelta(days=i): float(i % 7) for i in range(1, 40)}
        for fd in fm.generar_forecast_producto(ventas, hoy, horizonte_dias=14):
            assert fd.p10 <= fd.p50 <= fd.p90


class TestBaseline:
    def test_baseline_replica_dia_de_semana(self):
        hoy = date(2026, 7, 3)
        ventas = {}
        for i in range(1, 57):
            f = hoy - timedelta(days=i)
            ventas[f] = 30.0 if f.weekday() == 5 else 10.0
        baseline = fm.forecast_baseline_naive(ventas, hoy, horizonte_dias=7)
        fechas_futuras = [hoy + timedelta(days=i) for i in range(7)]
        for f, pred in zip(fechas_futuras, baseline):
            esperado = 30.0 if f.weekday() == 5 else 10.0
            assert pred == pytest.approx(esperado)


class TestStockSeguridad:
    def test_z_niveles_conocidos(self):
        # Valores de tabla normal estándar
        assert semantica.z_nivel_servicio(0.50) == pytest.approx(0.0, abs=1e-6)
        assert semantica.z_nivel_servicio(0.95) == pytest.approx(1.6449, abs=0.001)
        assert semantica.z_nivel_servicio(0.99) == pytest.approx(2.3263, abs=0.001)

    def test_ss_formula_clasica(self):
        # Sin variabilidad de lead time: SS = z × σ_d × √LT
        ss = semantica.stock_seguridad(0.95, 9, 2.0)
        assert ss == pytest.approx(1.6449 * 2.0 * 3.0, rel=0.001)

    def test_ss_sin_variabilidad_es_cero(self):
        assert semantica.stock_seguridad(0.99, 7, 0.0, 5.0, 0.0) == 0.0

    def test_ss_variabilidad_lead_time_aumenta_ss(self):
        sin_var_lt = semantica.stock_seguridad(0.97, 7, 2.0, 5.0, 0.0)
        con_var_lt = semantica.stock_seguridad(0.97, 7, 2.0, 5.0, 2.0)
        assert con_var_lt > sin_var_lt

    def test_nivel_mas_alto_mas_stock(self):
        ss_a = semantica.stock_seguridad(0.99, 7, 2.0)
        ss_c = semantica.stock_seguridad(0.92, 7, 2.0)
        assert ss_a > ss_c

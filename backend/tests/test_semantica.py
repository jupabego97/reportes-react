"""
Tests de la capa semántica — las definiciones canónicas del negocio.

Si un test de este archivo falla, cambió la definición de una métrica
para TODA la empresa: revisar con negocio antes de ajustar el test.
"""
from app import semantica


class TestMargen:
    def test_margen_unitario_basico(self):
        assert semantica.margen_unitario(100, 60) == 40

    def test_margen_sin_costo_es_none_no_cero(self):
        # Un margen desconocido nunca se reporta como 0
        assert semantica.margen_unitario(100, None) is None
        assert semantica.margen_pct(100, None) is None
        assert semantica.margen_total_linea(100, None, 5) is None

    def test_margen_pct_sobre_venta(self):
        assert semantica.margen_pct(100, 60) == 40.0

    def test_margen_negativo(self):
        assert semantica.margen_unitario(50, 60) == -10

    def test_venta_neta(self):
        assert semantica.venta_neta(10, 3) == 30


class TestInventario:
    def test_venta_diaria(self):
        assert semantica.venta_diaria(30, 30) == 1.0
        assert semantica.venta_diaria(0, 30) == 0.0
        assert semantica.venta_diaria(10, 0) == 0.0

    def test_dias_cobertura_sin_venta_es_none(self):
        # Cobertura indefinida, no "999"
        assert semantica.dias_cobertura(100, 0) is None

    def test_dias_cobertura(self):
        assert semantica.dias_cobertura(10, 2) == 5.0

    def test_estado_stock(self):
        assert semantica.estado_stock(None) == semantica.ESTADO_SIN_VENTA
        assert semantica.estado_stock(2) == semantica.ESTADO_CRITICO
        assert semantica.estado_stock(5) == semantica.ESTADO_BAJO
        assert semantica.estado_stock(30) == semantica.ESTADO_NORMAL
        assert semantica.estado_stock(90) == semantica.ESTADO_EXCESO

    def test_rotacion_anualiza_con_dias_reales(self):
        # 30 unidades en 30 días con stock promedio 30 → 365 unidades/año / 30
        rot = semantica.rotacion_anual(30, 30, 30)
        assert rot is not None
        assert abs(rot - 365 / 30) < 0.001

    def test_gmroi(self):
        assert semantica.gmroi(300, 100) == 3.0
        assert semantica.gmroi(300, 0) is None

    def test_valor_inventario_al_costo(self):
        assert semantica.valor_inventario_costo(10, 5) == 50
        assert semantica.valor_inventario_costo(10, None) is None

    def test_punto_reorden(self):
        # ROP = 2 uds/día × 7 días + 5 de seguridad
        assert semantica.punto_reorden(2, 7, 5) == 19


class TestVentaPerdida:
    def test_venta_perdida(self):
        # 3 uds/día × 5 días de quiebre × $10
        assert semantica.venta_perdida(3, 5, 10) == 150

    def test_margen_perdido_usa_margen_real(self):
        assert semantica.margen_perdido(3, 5, 10, 6) == 60.0

    def test_margen_perdido_sin_costo_es_none(self):
        # Sin costo no se inventa un margen fijo
        assert semantica.margen_perdido(3, 5, 10, None) is None


class TestConteos:
    def test_conteo_exacto(self):
        assert semantica.conteo_es_exacto(10, 10) is True
        assert semantica.conteo_es_exacto(10, 9) is False

    def test_exactitud_inventario(self):
        assert semantica.exactitud_inventario(97, 100) == 97.0
        assert semantica.exactitud_inventario(0, 0) is None

    def test_prioridad_conteo_mayor_valor_mayor_score(self):
        alto = semantica.prioridad_conteo(1000, 0, 0)
        bajo = semantica.prioridad_conteo(100, 0, 0)
        assert alto > bajo

    def test_prioridad_conteo_discrepancia_sube_score(self):
        con_disc = semantica.prioridad_conteo(100, 50, 0)
        sin_disc = semantica.prioridad_conteo(100, 0, 0)
        assert con_disc > sin_disc

    def test_prioridad_conteo_antiguedad_sube_score(self):
        viejo = semantica.prioridad_conteo(100, 0, 180)
        reciente = semantica.prioridad_conteo(100, 0, 1)
        assert viejo > reciente


class TestMerma:
    def test_merma_valor_positiva_es_perdida(self):
        assert semantica.merma_valor(10, 8, 5) == 10  # faltan 2 uds × $5

    def test_merma_sin_costo_es_none(self):
        assert semantica.merma_valor(10, 8, None) is None

    def test_merma_pct(self):
        assert semantica.merma_pct_sobre_venta(10, 1000) == 1.0
        assert semantica.merma_pct_sobre_venta(10, 0) is None


class TestNormalizacion:
    def test_normalizar_nombre(self):
        assert semantica.normalizar_nombre("  alberto   abs ") == "ALBERTO ABS"
        assert semantica.normalizar_nombre("") is None
        assert semantica.normalizar_nombre(None) is None

    def test_proveedor_placeholder_es_none(self):
        assert semantica.proveedor_canonico("VARIOS") is None
        assert semantica.proveedor_canonico(" n/a ") is None
        assert semantica.proveedor_canonico("ALBERTO ABS") == "ALBERTO ABS"

    def test_familia_placeholder_es_none(self):
        assert semantica.familia_canonica("SIN FAMILIA") is None
        assert semantica.familia_canonica("cables") == "CABLES"

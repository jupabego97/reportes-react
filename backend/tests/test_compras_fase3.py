"""
Tests de la lógica pura de Fase 3: restricciones de compra y desempeño
de proveedores (OTIF, fill rate).
"""
from app import semantica


class TestRedondeoEmpaque:
    def test_redondea_hacia_arriba_al_multiplo(self):
        assert semantica.redondear_a_empaque(13, 12) == 24
        assert semantica.redondear_a_empaque(12, 12) == 12
        assert semantica.redondear_a_empaque(1, 12) == 12

    def test_empaque_unitario_techo(self):
        assert semantica.redondear_a_empaque(3.2, 1) == 4
        assert semantica.redondear_a_empaque(3.0, 1) == 3

    def test_cantidad_cero_o_negativa_no_pide(self):
        assert semantica.redondear_a_empaque(0, 12) == 0
        assert semantica.redondear_a_empaque(-5, 12) == 0

    def test_empaque_invalido_se_trata_como_uno(self):
        assert semantica.redondear_a_empaque(3.5, 0) == 4
        assert semantica.redondear_a_empaque(3.5, None) == 4


class TestOtif:
    def test_otif_basico(self):
        assert semantica.otif_pct(9, 10) == 90.0
        assert semantica.otif_pct(10, 10) == 100.0
        assert semantica.otif_pct(0, 10) == 0.0

    def test_otif_sin_ordenes_es_none(self):
        # Sin datos no hay métrica, no "100%"
        assert semantica.otif_pct(0, 0) is None

    def test_fill_rate(self):
        assert semantica.fill_rate_pct(95, 100) == 95.0
        assert semantica.fill_rate_pct(100, 100) == 100.0

    def test_fill_rate_no_supera_cien(self):
        # Recibir de más no es mejor servicio
        assert semantica.fill_rate_pct(120, 100) == 100.0

    def test_fill_rate_sin_pedido_es_none(self):
        assert semantica.fill_rate_pct(10, 0) is None


class TestConstantesCompras:
    def test_causas_merma_canonicas(self):
        assert semantica.CAUSAS_MERMA == {
            "vencimiento",
            "dano",
            "robo_externo",
            "robo_interno",
            "error_administrativo",
        }

    def test_umbrales(self):
        assert semantica.OTIF_OBJETIVO_PCT == 95.0
        assert semantica.OTIF_CAIDA_ALERTA_PTS == 5.0
        assert semantica.MERMA_PCT_ALERTA == 1.0

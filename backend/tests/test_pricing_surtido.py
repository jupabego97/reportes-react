"""
Tests de lógica pura Fase 4: elasticidad, markdown, surtido y diagnóstico causal.
"""
from app import semantica


class TestElasticidad:
    def test_elasticidad_negativa_con_variacion(self):
        precios = [100, 105, 110, 115, 120]
        cantidades = [50, 48, 45, 42, 40]
        e = semantica.elasticidad_loglog(precios, cantidades)
        assert e is not None
        assert e < 0

    def test_sin_variacion_precio_retorna_none(self):
        precios = [100, 100, 100, 100, 100]
        cantidades = [50, 48, 45, 42, 40]
        assert semantica.elasticidad_loglog(precios, cantidades) is None

    def test_pocos_puntos_retorna_none(self):
        assert semantica.elasticidad_loglog([100, 110], [50, 45]) is None

    def test_confianza_baja_vs_media(self):
        assert semantica.confianza_elasticidad(5, 0.03) == "baja"
        assert semantica.confianza_elasticidad(20, 0.08) == "media"


class TestMarkdown:
    def test_markdown_escalonado(self):
        p10 = semantica.precio_markdown_optimo(100, 60, dias_sin_venta=10)
        p20 = semantica.precio_markdown_optimo(100, 60, dias_sin_venta=35)
        p30 = semantica.precio_markdown_optimo(100, 60, dias_sin_venta=65)
        assert p10 == 90.0
        assert p20 == 80.0
        assert p30 == 70.0

    def test_no_baja_del_costo(self):
        sugerido = semantica.precio_markdown_optimo(100, 95, dias_sin_venta=90)
        assert sugerido is not None
        assert sugerido >= 95 * 1.05

    def test_precio_cero_retorna_none(self):
        assert semantica.precio_markdown_optimo(0, 50) is None


class TestClasificarSurtido:
    def test_eliminar_gmroi_bajo(self):
        assert semantica.clasificar_surtido(0.3, 1.0) == "eliminar"

    def test_potenciar_gmroi_alto_velocidad_alta(self):
        assert semantica.clasificar_surtido(4.0, 2.0) == "potenciar"

    def test_reducir_velocidad_baja(self):
        assert semantica.clasificar_surtido(2.0, 0.1) == "reducir"

    def test_mantener_zona_media(self):
        assert semantica.clasificar_surtido(2.0, 1.0) == "mantener"


class TestDescomposicionCausal:
    def test_identidad_volumen_precio_mix(self):
        periodo_a = [
            {"nombre": "A", "cantidad": 10, "precio": 100, "venta_neta": 1000},
            {"nombre": "B", "cantidad": 5, "precio": 200, "venta_neta": 1000},
        ]
        periodo_b = [
            {"nombre": "A", "cantidad": 12, "precio": 105, "venta_neta": 1260},
            {"nombre": "B", "cantidad": 4, "precio": 195, "venta_neta": 780},
        ]
        r = semantica.descomponer_varianza_venta(periodo_a, periodo_b)
        assert r["venta_periodo_a"] == 2000
        assert r["venta_periodo_b"] == 2040
        assert r["delta_venta"] == 40
        suma = r["efecto_volumen"] + r["efecto_precio"] + r["efecto_mix"]
        assert abs(suma - r["delta_venta"]) < 0.01

    def test_detalle_ordenado_por_impacto(self):
        periodo_a = [{"nombre": "X", "cantidad": 1, "precio": 10, "venta_neta": 10}]
        periodo_b = [{"nombre": "X", "cantidad": 100, "precio": 10, "venta_neta": 1000}]
        r = semantica.descomponer_varianza_venta(periodo_a, periodo_b)
        assert len(r["detalle"]) == 1
        assert r["efecto_volumen"] == 990

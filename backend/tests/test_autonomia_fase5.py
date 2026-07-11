"""Tests de autonomía Fase 5."""
from app import semantica


class TestNivelAutonomia:
    def test_prohibidos_siempre_nivel2(self):
        assert semantica.nivel_autonomia("margen_negativo", 1000, auto_max_impacto=1_000_000) == 2
        assert semantica.nivel_autonomia("quiebre_inminente", 0, auto_max_impacto=1_000_000) == 2

    def test_comite_nivel3(self):
        assert semantica.nivel_autonomia("surtido_eliminar", 50_000) == 3
        assert semantica.nivel_autonomia("forecast_degradado", 10) == 3

    def test_bajo_umbral_nivel1(self):
        assert (
            semantica.nivel_autonomia(
                "inventario_muerto",
                100_000,
                auto_max_impacto=200_000,
                habilitado=True,
            )
            == 1
        )

    def test_sobre_umbral_nivel2(self):
        assert (
            semantica.nivel_autonomia(
                "inventario_muerto",
                500_000,
                auto_max_impacto=200_000,
                habilitado=True,
            )
            == 2
        )

    def test_deshabilitado_nivel2(self):
        assert (
            semantica.nivel_autonomia(
                "markdown_recomendado",
                10,
                auto_max_impacto=1_000_000,
                habilitado=False,
            )
            == 2
        )


class TestScores:
    def test_score_riesgo(self):
        assert semantica.score_riesgo(1000, 0.5) == 500.0
        assert semantica.score_riesgo(None, 0.5) == 0.0

    def test_score_oportunidad(self):
        assert semantica.score_oportunidad(2000, 0.25) == 500.0

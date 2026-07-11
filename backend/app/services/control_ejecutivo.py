"""
Control ejecutivo (Fase 5): riesgos, oportunidades y resumen de autonomía.

Agrega lo ya existente (decisiones, venta perdida, scorecards) sin inventar
modelos de red multi-tienda, fraude POS o labor.
"""
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class ControlEjecutivoService:
    """Panel de control: riesgos, oportunidades y estado del sistema."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_riesgos(self) -> List[Dict[str, Any]]:
        """Riesgos activos = decisiones pendientes de códigos de riesgo."""
        codigos_riesgo = {
            "quiebre_inminente": 0.9,
            "quiebre_fantasma": 0.7,
            "oc_vencida_sin_recibir": 0.8,
            "proveedor_deteriorado": 0.6,
            "merma_alta": 0.5,
            "forecast_degradado": 0.4,
            "margen_negativo": 0.95,
            "exactitud_baja": 0.5,
            "autonomia_deshabilitada": 0.3,
        }
        result = await self.db.execute(
            text(
                """
                SELECT id, codigo_alerta, prioridad, titulo, impacto_dinero, dueno, vence_en
                FROM decisiones
                WHERE estado = 'pendiente'
                ORDER BY impacto_dinero DESC NULLS LAST
                LIMIT 200
                """
            )
        )
        riesgos = []
        for r in result.fetchall():
            if r[1] not in codigos_riesgo:
                continue
            impacto = float(r[4]) if r[4] is not None else 0.0
            prob = codigos_riesgo.get(r[1], 0.5)
            riesgos.append(
                {
                    "decision_id": int(r[0]),
                    "codigo": r[1],
                    "prioridad": r[2],
                    "titulo": r[3],
                    "impacto_dinero": impacto,
                    "score": round(semantica.score_riesgo(impacto, prob), 2),
                    "dueno": r[5],
                    "vence_en": str(r[6]) if r[6] else None,
                }
            )
        riesgos.sort(key=lambda x: x["score"], reverse=True)
        return riesgos[:50]

    async def get_oportunidades(self) -> List[Dict[str, Any]]:
        """Oportunidades = markdowns, surtido, venta perdida, decisiones de oportunidad."""
        oportunidades: List[Dict[str, Any]] = []

        result = await self.db.execute(
            text(
                """
                SELECT id, codigo_alerta, titulo, impacto_dinero, dueno
                FROM decisiones
                WHERE estado = 'pendiente'
                  AND codigo_alerta IN (
                      'markdown_recomendado', 'surtido_eliminar',
                      'venta_perdida_semanal', 'inventario_muerto',
                      'margen_erosion_mix'
                  )
                ORDER BY impacto_dinero DESC NULLS LAST
                LIMIT 40
                """
            )
        )
        capturabilidad = {
            "markdown_recomendado": 0.6,
            "surtido_eliminar": 0.5,
            "venta_perdida_semanal": 0.7,
            "inventario_muerto": 0.55,
            "margen_erosion_mix": 0.4,
        }
        for r in result.fetchall():
            impacto = float(r[3]) if r[3] is not None else 0.0
            cap = capturabilidad.get(r[1], 0.5)
            oportunidades.append(
                {
                    "fuente": "decision",
                    "codigo": r[1],
                    "titulo": r[2],
                    "impacto_dinero": impacto,
                    "score": round(semantica.score_oportunidad(impacto, cap), 2),
                    "dueno": r[4],
                }
            )

        try:
            from app.services.forecast import ForecastService

            vp = await ForecastService(self.db).get_venta_perdida(dias=30)
            total = float(vp.get("venta_perdida_total") or 0)
            if total > 0:
                oportunidades.append(
                    {
                        "fuente": "venta_perdida",
                        "codigo": "venta_perdida_30d",
                        "titulo": f"Venta perdida 30d: ${total:,.0f}",
                        "impacto_dinero": total,
                        "score": round(semantica.score_oportunidad(total, 0.65), 2),
                        "dueno": "comprador",
                    }
                )
        except Exception:
            await self.db.rollback()

        oportunidades.sort(key=lambda x: x["score"], reverse=True)
        return oportunidades

    async def get_resumen(self) -> Dict[str, Any]:
        riesgos = await self.get_riesgos()
        oportunidades = await self.get_oportunidades()

        from app.services.aprendizaje import AprendizajeService
        from app.services.orquestador import OrquestadorService
        from app.services.autonomia import AutonomiaService

        aprendizaje = await AprendizajeService(self.db).get_metricas(dias=30)
        horas = await OrquestadorService(self.db).horas_desde_ultimo_ok()
        politicas = await AutonomiaService(self.db).get_politicas()

        return {
            "dinero_en_riesgo": round(sum(r["impacto_dinero"] for r in riesgos), 2),
            "dinero_en_oportunidades": round(
                sum(o["impacto_dinero"] for o in oportunidades), 2
            ),
            "riesgos_activos": len(riesgos),
            "oportunidades_activas": len(oportunidades),
            "tasa_aceptacion_pct": aprendizaje.get("tasa_aceptacion_pct"),
            "pct_auto_nivel1": aprendizaje.get("pct_auto_nivel1"),
            "horas_desde_ultimo_ciclo": round(horas, 1) if horas is not None else None,
            "politicas_habilitadas": sum(1 for p in politicas if p["habilitado"]),
            "modulos_sin_datos": [
                "multi_tienda_cd",
                "transferencias_red",
                "fraude_pos",
                "dotacion_turnos",
                "promociones_causales",
                "clv_market_basket",
            ],
            "top_riesgos": riesgos[:5],
            "top_oportunidades": oportunidades[:5],
        }

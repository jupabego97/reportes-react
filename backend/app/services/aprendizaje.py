"""
Circuito de aprendizaje (Fase 5).

Registra cada resolución de decisión para medir tasa de aceptación
por tipo de alerta — el insumo del circuito cerrado.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AprendizajeService:
    """Registro y métricas de aceptación de decisiones."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar(
        self,
        decision_id: int,
        codigo_alerta: str,
        prioridad: Optional[str],
        estado_final: str,
        impacto_dinero: Optional[float],
        nota: Optional[str],
        usuario: Optional[str],
    ) -> None:
        fue_auto = bool(usuario and str(usuario).startswith("auto:"))
        await self.db.execute(
            text(
                """
                INSERT INTO aprendizaje_decisiones
                    (decision_id, codigo_alerta, prioridad, estado_final,
                     impacto_dinero, nota, usuario, fue_auto)
                VALUES (:did, :codigo, :prio, :estado, :impacto, :nota, :usuario, :auto)
                """
            ),
            {
                "did": decision_id,
                "codigo": codigo_alerta,
                "prio": prioridad,
                "estado": estado_final,
                "impacto": impacto_dinero,
                "nota": nota,
                "usuario": usuario,
                "auto": fue_auto,
            },
        )
        # El commit lo hace el caller (resolver)

    async def get_metricas(self, dias: int = 30) -> Dict[str, Any]:
        query = """
            SELECT
                codigo_alerta,
                COUNT(*) as total,
                SUM(CASE WHEN estado_final IN ('aprobada', 'resuelta') THEN 1 ELSE 0 END) as aceptadas,
                SUM(CASE WHEN estado_final = 'rechazada' THEN 1 ELSE 0 END) as rechazadas,
                SUM(CASE WHEN fue_auto THEN 1 ELSE 0 END) as auto,
                AVG(impacto_dinero) as impacto_promedio
            FROM aprendizaje_decisiones
            WHERE created_at >= CURRENT_DATE - CAST(:dias AS INTEGER)
            GROUP BY codigo_alerta
            ORDER BY COUNT(*) DESC
        """
        result = await self.db.execute(text(query), {"dias": dias})
        por_codigo = []
        total = 0
        aceptadas = 0
        auto = 0
        for r in result.fetchall():
            t = int(r[1] or 0)
            a = int(r[2] or 0)
            total += t
            aceptadas += a
            auto += int(r[4] or 0)
            por_codigo.append(
                {
                    "codigo_alerta": r[0],
                    "total": t,
                    "aceptadas": a,
                    "rechazadas": int(r[3] or 0),
                    "auto": int(r[4] or 0),
                    "tasa_aceptacion_pct": round(a / t * 100, 1) if t else None,
                    "impacto_promedio": round(float(r[5]), 2) if r[5] is not None else None,
                }
            )
        return {
            "dias": dias,
            "total_resoluciones": total,
            "tasa_aceptacion_pct": round(aceptadas / total * 100, 1) if total else None,
            "pct_auto_nivel1": round(auto / total * 100, 1) if total else None,
            "por_codigo": por_codigo,
        }

"""
Orquestador nocturno (Fase 5).

Pipeline idempotente que reemplaza los botones manuales:
consolidar historial → precios → forecast → decisiones → markdowns/surtido → autonomía.
"""
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class OrquestadorService:
    """Ciclo nocturno de inteligencia operativa."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def correr_noche(self) -> Dict[str, Any]:
        """Ejecuta el pipeline completo y registra el job."""
        job_id = await self._iniciar_job("ciclo_nocturno")
        pasos: Dict[str, Any] = {}
        try:
            from app.services.forecast import ForecastService
            from app.services.pricing import PricingService
            from app.services.decisiones import DecisionesService
            from app.services.surtido import SurtidoService
            from app.services.autonomia import AutonomiaService

            pasos["consolidar_historial"] = await ForecastService(self.db).consolidar_historial()
            pasos["consolidar_precios"] = await PricingService(self.db).consolidar_precios()

            try:
                pasos["generar_forecast"] = await ForecastService(self.db).generar()
            except Exception as e:
                pasos["generar_forecast"] = {"error": str(e), "omitido": True}

            pasos["evaluar_decisiones"] = await DecisionesService(self.db).evaluar()

            try:
                pasos["markdowns"] = await PricingService(self.db).sugerir_markdowns()
            except Exception as e:
                pasos["markdowns"] = {"error": str(e)}

            try:
                pasos["surtido"] = await SurtidoService(self.db).generar_revision()
            except Exception as e:
                pasos["surtido"] = {"error": str(e)}

            try:
                pasos["evaluar_decisiones_2"] = await DecisionesService(self.db).evaluar()
            except Exception as e:
                pasos["evaluar_decisiones_2"] = {"error": str(e)}

            pasos["autonomia_nivel1"] = await AutonomiaService(self.db).ejecutar_nivel1()

            await self._finalizar_job(job_id, "ok", pasos)
            return {"job_id": job_id, "estado": "ok", "pasos": pasos}
        except Exception as e:
            await self._finalizar_job(job_id, "error", pasos, error=str(e))
            raise

    async def get_jobs(self, limite: int = 20) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT id, job, estado, detalle, error, iniciado_en, finalizado_en
                FROM jobs_ejecucion
                ORDER BY iniciado_en DESC
                LIMIT :limite
                """
            ),
            {"limite": limite},
        )
        filas = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            fila["iniciado_en"] = str(fila["iniciado_en"]) if fila["iniciado_en"] else None
            fila["finalizado_en"] = str(fila["finalizado_en"]) if fila["finalizado_en"] else None
            filas.append(fila)
        return filas

    async def horas_desde_ultimo_ok(self) -> Optional[float]:
        result = await self.db.execute(
            text(
                """
                SELECT EXTRACT(EPOCH FROM (NOW() - finalizado_en)) / 3600.0
                FROM jobs_ejecucion
                WHERE job = 'ciclo_nocturno' AND estado = 'ok'
                ORDER BY finalizado_en DESC NULLS LAST
                LIMIT 1
                """
            )
        )
        row = result.fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0])

    async def _iniciar_job(self, job: str) -> int:
        result = await self.db.execute(
            text(
                """
                INSERT INTO jobs_ejecucion (job, estado)
                VALUES (:job, 'corriendo')
                RETURNING id
                """
            ),
            {"job": job},
        )
        await self.db.commit()
        return int(result.fetchone()[0])

    async def _finalizar_job(
        self,
        job_id: int,
        estado: str,
        detalle: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        await self.db.execute(
            text(
                """
                UPDATE jobs_ejecucion
                SET estado = :estado, detalle = CAST(:detalle AS JSON),
                    error = :error, finalizado_en = NOW()
                WHERE id = :id
                """
            ),
            {
                "estado": estado,
                "detalle": json.dumps(detalle, default=str),
                "error": error,
                "id": job_id,
            },
        )
        await self.db.commit()

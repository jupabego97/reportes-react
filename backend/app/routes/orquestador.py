"""Rutas del orquestador nocturno (Fase 5)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.orquestador import OrquestadorService

router = APIRouter(
    prefix="/api/orquestador",
    tags=["orquestador"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post("/correr")
async def correr_ciclo(db: AsyncSession = Depends(get_db)):
    """Ejecuta el ciclo nocturno completo (manual o vía cron)."""
    service = OrquestadorService(db)
    return await service.correr_noche()


@router.get("/jobs")
async def get_jobs(
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Últimas corridas del orquestador."""
    service = OrquestadorService(db)
    return await service.get_jobs(limite=limite)

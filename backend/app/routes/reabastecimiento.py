"""
Rutas de reabastecimiento con stock de seguridad dinámico (Fase 2).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.reabastecimiento import ReabastecimientoService

router = APIRouter(
    prefix="/api/reabastecimiento",
    tags=["reabastecimiento"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/sugerencias")
async def get_sugerencias(
    dias_historia: int = Query(60, ge=14, le=365),
    horizonte_cobertura_dias: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Sugerencias con SS dinámico por clase ABC, ROP y urgencia."""
    service = ReabastecimientoService(db)
    return await service.get_sugerencias(
        dias_historia=dias_historia,
        horizonte_cobertura_dias=horizonte_cobertura_dias,
    )


@router.get("/resumen")
async def get_resumen(db: AsyncSession = Depends(get_db)):
    """Totales por urgencia e inversión requerida."""
    service = ReabastecimientoService(db)
    return await service.get_resumen()

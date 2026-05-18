"""Rutas de métricas retail estándar."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.schemas import FilterParams, MetricasSectorResponse
from app.routes.ventas import get_filter_params
from app.services.metricas_sector import MetricasSectorService

router = APIRouter(
    prefix="/api/metricas-sector",
    tags=["metricas-sector"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/resumen", response_model=MetricasSectorResponse)
async def get_metricas_sector_resumen(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Resumen ejecutivo con métricas retail estándar y proxies etiquetados."""
    service = MetricasSectorService(db)
    return await service.get_resumen(filters)

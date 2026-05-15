"""
Rutas de insights inteligentes.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.models.schemas import FilterParams
from app.services.ventas import VentasService
from app.services.insights import InsightsService
from app.services.predicciones import PrediccionesService
from app.routes.ventas import get_filter_params


router = APIRouter(
    prefix="/api/insights",
    tags=["insights"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("", response_model=dict)
async def get_insights(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Obtiene insights inteligentes cruzando ABC + inventario + tendencias."""
    ventas_service = VentasService(db)
    pred = PrediccionesService(ventas_service)
    service = InsightsService(db, ventas_service, pred)
    return await service.get_insights(filters)


@router.get("/kpis", response_model=dict)
async def get_insights_kpis(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """KPIs ejecutivos consolidados (ventas, margen, inventario, forecast, urgencias)."""
    ventas_service = VentasService(db)
    pred = PrediccionesService(ventas_service)
    service = InsightsService(db, ventas_service, pred)
    return await service.get_kpis_ejecutivo(filters)


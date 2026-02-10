"""
Rutas de insights inteligentes.
"""
from datetime import date
from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.models.schemas import FilterParams
from app.services.ventas import VentasService
from app.services.insights import InsightsService
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
    service = InsightsService(db, ventas_service)
    return await service.get_insights(filters)


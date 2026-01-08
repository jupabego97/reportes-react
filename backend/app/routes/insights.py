"""
Rutas de insights.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.insights import InsightsService

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
async def get_insights(db: AsyncSession = Depends(get_db)):
    """Obtiene insights automáticos del negocio."""
    service = InsightsService(db)
    return await service.get_insights_dashboard()


@router.get("/kpis")
async def get_kpis_ejecutivo(db: AsyncSession = Depends(get_db)):
    """Obtiene KPIs para dashboard ejecutivo."""
    service = InsightsService(db)
    return await service.get_kpis_ejecutivo()

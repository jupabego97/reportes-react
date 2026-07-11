"""Rutas de pricing (Fase 4): historial, elasticidad y markdowns."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.pricing import PricingService

router = APIRouter(
    prefix="/api/pricing",
    tags=["pricing"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post("/consolidar-precios")
async def consolidar_precios(db: AsyncSession = Depends(get_db)):
    """Consolida historial de precios desde ventas y maestro."""
    service = PricingService(db)
    return await service.consolidar_precios()


@router.get("/elasticidades")
async def get_elasticidades(db: AsyncSession = Depends(get_db)):
    """Elasticidades estimadas (solo productos con variación de precio observada)."""
    service = PricingService(db)
    return await service.estimar_elasticidades()


@router.post("/generar-markdowns")
async def generar_markdowns(db: AsyncSession = Depends(get_db)):
    """Genera recomendaciones de markdown para inventario muerto/exceso."""
    service = PricingService(db)
    return await service.sugerir_markdowns()


@router.get("/oportunidades")
async def get_oportunidades(
    limite: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Oportunidades de precio / markdown pendientes."""
    service = PricingService(db)
    return await service.get_oportunidades_precio(limite=limite)

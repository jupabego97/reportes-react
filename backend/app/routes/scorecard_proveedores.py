"""
Rutas del scorecard de proveedores (Fase 3): OTIF, fill rate y deterioro.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.scorecard_proveedores import ScorecardProveedoresService

router = APIRouter(
    prefix="/api/scorecard-proveedores",
    tags=["scorecard-proveedores"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("")
async def get_scorecard(
    dias: int = Query(90, ge=14, le=365),
    db: AsyncSession = Depends(get_db),
):
    """OTIF, fill rate y lead time real por proveedor (OC recibidas en la ventana)."""
    service = ScorecardProveedoresService(db)
    return await service.get_scorecard(dias=dias)


@router.get("/deteriorados")
async def get_deteriorados(db: AsyncSession = Depends(get_db)):
    """Proveedores con OTIF reciente en caída vs su histórico."""
    service = ScorecardProveedoresService(db)
    return await service.get_deteriorados()

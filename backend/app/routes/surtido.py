"""Rutas de surtido (Fase 4): matriz GMROI×velocidad y bajas lógicas."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.surtido import SurtidoService

router = APIRouter(
    prefix="/api/surtido",
    tags=["surtido"],
    dependencies=[Depends(get_current_active_user)],
)


@router.post("/generar-revision")
async def generar_revision(db: AsyncSession = Depends(get_db)):
    """Calcula y persiste recomendaciones de surtido."""
    service = SurtidoService(db)
    return await service.generar_revision()


@router.get("/revision")
async def get_revision(
    limite: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Matriz de surtido con acción sugerida por producto."""
    service = SurtidoService(db)
    return await service.get_revision_surtido(limite=limite)


@router.post("/{producto_id}/baja")
async def aplicar_baja(producto_id: int, db: AsyncSession = Depends(get_db)):
    """Baja lógica de un SKU (activo=false)."""
    service = SurtidoService(db)
    try:
        return await service.aplicar_baja(producto_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

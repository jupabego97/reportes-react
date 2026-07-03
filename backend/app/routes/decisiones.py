"""
Rutas del motor de decisiones — la bandeja que reemplaza a los dashboards.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.services.decisiones import DecisionesService

router = APIRouter(
    prefix="/api/decisiones",
    tags=["decisiones"],
)


class ResolverRequest(BaseModel):
    estado: str  # aprobada | rechazada | resuelta
    nota: Optional[str] = None


@router.get("")
async def get_bandeja(
    dueno: Optional[str] = Query(None, description="Filtrar por rol dueño"),
    estado: str = Query("pendiente", description="pendiente | aprobada | rechazada | resuelta | expirada | todas"),
    limite: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Bandeja de decisiones ordenada por prioridad e impacto en dinero."""
    service = DecisionesService(db)
    return await service.get_bandeja(dueno=dueno, estado=estado, limite=limite)


@router.get("/resumen")
async def get_resumen(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Resumen de pendientes y dinero en juego por prioridad."""
    service = DecisionesService(db)
    return await service.get_resumen()


@router.post("/evaluar")
async def evaluar(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Corre todos los detectores y emite nuevas decisiones (idempotente por dedup)."""
    service = DecisionesService(db)
    return await service.evaluar()


@router.post("/{decision_id}/resolver")
async def resolver(
    decision_id: int,
    body: ResolverRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Cierra una decisión (aprobada/rechazada/resuelta) con trazabilidad."""
    service = DecisionesService(db)
    try:
        return await service.resolver(
            decision_id, body.estado, usuario=user.username, nota=body.nota
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

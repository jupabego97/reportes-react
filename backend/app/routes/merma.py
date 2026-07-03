"""
Rutas de merma por causa (Fase 3).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.services.merma import MermaService

router = APIRouter(
    prefix="/api/merma",
    tags=["merma"],
    dependencies=[Depends(get_current_active_user)],
)


class MermaRequest(BaseModel):
    nombre_producto: str
    causa: str
    cantidad: float = Field(gt=0)
    nota: Optional[str] = None


@router.post("/registrar")
async def registrar(
    payload: MermaRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Registra una merma clasificada y descuenta el inventario perpetuo."""
    service = MermaService(db)
    try:
        return await service.registrar(
            nombre_producto=payload.nombre_producto,
            causa=payload.causa,
            cantidad=payload.cantidad,
            nota=payload.nota,
            usuario=user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reporte")
async def get_reporte(
    dias: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Merma valorizada del período: total, % sobre venta, por causa y top productos."""
    service = MermaService(db)
    return await service.get_reporte(dias=dias)

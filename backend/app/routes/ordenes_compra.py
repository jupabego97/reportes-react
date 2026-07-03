"""
Rutas de órdenes de compra (Fase 3): generación con restricciones,
ciclo de vida y recepción contra el inventario perpetuo.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.services.ordenes_compra import OrdenesCompraService

router = APIRouter(
    prefix="/api/ordenes-compra",
    tags=["ordenes-compra"],
    dependencies=[Depends(get_current_active_user)],
)


class RecepcionLinea(BaseModel):
    producto_id: int
    cantidad_recibida: float = Field(ge=0)


class RecepcionRequest(BaseModel):
    recepciones: List[RecepcionLinea]


@router.post("/generar")
async def generar_borradores(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Genera OC en borrador desde las sugerencias urgentes, agrupadas por proveedor."""
    service = OrdenesCompraService(db)
    return await service.generar_borradores(usuario=user.username)


@router.get("")
async def get_ordenes(
    estado: Optional[str] = Query(None),
    limite: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Lista de órdenes de compra, más recientes primero."""
    service = OrdenesCompraService(db)
    return await service.get_ordenes(estado=estado, limite=limite)


@router.get("/{orden_id}")
async def get_detalle(orden_id: int, db: AsyncSession = Depends(get_db)):
    """Cabecera y líneas de una orden."""
    service = OrdenesCompraService(db)
    try:
        return await service.get_detalle(orden_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{orden_id}/aprobar")
async def aprobar(
    orden_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Borrador → aprobada."""
    service = OrdenesCompraService(db)
    try:
        return await service.aprobar(orden_id, usuario=user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{orden_id}/enviar")
async def enviar(orden_id: int, db: AsyncSession = Depends(get_db)):
    """Aprobada → enviada; fija la fecha promesa (compromiso OTIF)."""
    service = OrdenesCompraService(db)
    try:
        return await service.enviar(orden_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{orden_id}/recibir")
async def recibir(
    orden_id: int,
    payload: RecepcionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Registra la recepción física y los movimientos de inventario."""
    service = OrdenesCompraService(db)
    try:
        return await service.recibir(
            orden_id,
            recepciones=[r.model_dump() for r in payload.recepciones],
            usuario=user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{orden_id}/cancelar")
async def cancelar(orden_id: int, db: AsyncSession = Depends(get_db)):
    """Cancela una OC no recibida."""
    service = OrdenesCompraService(db)
    try:
        return await service.cancelar(orden_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

"""
Rutas de inventario perpetuo: movimientos, conteos cíclicos y exactitud.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.services.inventario_perpetuo import InventarioPerpetuoService

router = APIRouter(
    prefix="/api/inventario-perpetuo",
    tags=["inventario-perpetuo"],
)


class MovimientoRequest(BaseModel):
    nombre_producto: str
    tipo: str  # venta | compra | ajuste_conteo | merma | devolucion | transferencia_in | transferencia_out
    cantidad: float  # positiva entra, negativa sale
    costo_unitario: Optional[float] = None
    referencia: Optional[str] = None


class ConteoRequest(BaseModel):
    nombre_producto: str
    stock_fisico: float
    motivo: Optional[str] = None


@router.post("/carga-inicial")
async def cargar_stock_inicial(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Inicializa el libro con el stock actual de items (solo productos sin movimientos)."""
    service = InventarioPerpetuoService(db)
    return await service.cargar_stock_inicial()


@router.post("/movimientos")
async def registrar_movimiento(
    body: MovimientoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Registra un movimiento en el libro de inventario perpetuo."""
    service = InventarioPerpetuoService(db)
    try:
        return await service.registrar_movimiento(
            nombre_producto=body.nombre_producto,
            tipo=body.tipo,
            cantidad=body.cantidad,
            costo_unitario=body.costo_unitario,
            referencia=body.referencia,
            usuario=user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/conteos")
async def registrar_conteo(
    body: ConteoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Registra un conteo físico: evalúa exactitud y ajusta el libro."""
    service = InventarioPerpetuoService(db)
    try:
        return await service.registrar_conteo(
            nombre_producto=body.nombre_producto,
            stock_fisico=body.stock_fisico,
            usuario=user.username,
            motivo=body.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exactitud")
async def get_exactitud(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Exactitud de inventario de los últimos N días (objetivo > 97%)."""
    service = InventarioPerpetuoService(db)
    return await service.get_exactitud(dias=dias)


@router.get("/plan-conteos")
async def get_plan_conteos(
    limite: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Conteos dirigidos del día, priorizados por riesgo (valor × discrepancia × antigüedad)."""
    service = InventarioPerpetuoService(db)
    return await service.get_plan_conteos(limite=limite)


@router.get("/stock/{nombre_producto}")
async def get_stock_perpetuo(
    nombre_producto: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Stock según el libro perpetuo (suma de movimientos)."""
    service = InventarioPerpetuoService(db)
    stock = await service.get_stock_perpetuo(nombre_producto)
    if stock is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el maestro")
    return {"nombre_producto": nombre_producto, "stock_perpetuo": stock}

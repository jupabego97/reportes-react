"""
Rutas de facturas de proveedor - vencimientos.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.facturas_proveedor import FacturasProveedorService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/api/facturas-proveedor",
    tags=["facturas-proveedor"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("")
async def listar_facturas(
    db: AsyncSession = Depends(get_db),
    proveedor: Optional[str] = Query(None, description="Filtrar por nombre de proveedor"),
    dias_plazo: int = Query(30, ge=1, le=90, description="Dias para calcular vencimiento desde fecha factura"),
    estado: Optional[str] = Query(None, description="Filtrar: vencida, vence_hoy, proxima, vigente"),
):
    """Lista facturas con estado de vencimiento."""
    service = FacturasProveedorService(db)
    return await service.get_facturas(
        proveedor=proveedor,
        dias_plazo=dias_plazo,
        estado=estado,
    )


@router.get("/resumen")
async def resumen_facturas(
    db: AsyncSession = Depends(get_db),
    proveedor: Optional[str] = Query(None, description="Filtrar por nombre de proveedor"),
    dias_plazo: int = Query(30, ge=1, le=90),
):
    """Resumen por proveedor: total facturas, vencidas, proximas a vencer."""
    service = FacturasProveedorService(db)
    return await service.get_resumen(
        proveedor=proveedor,
        dias_plazo=dias_plazo,
    )

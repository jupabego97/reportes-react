"""
Rutas de vendedores.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.models.schemas import (
    FilterParams,
    VendedorRankingResponse,
    VendedorDetalleResponse,
    SugerenciaCompraResponse,
    ResumenProveedorResponse,
    OrdenCompraResponse,
)
from app.services.ventas import VentasService
from app.services.vendedores import VendedoresService
from app.services.compras import ComprasService
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api", tags=["vendedores"], dependencies=[Depends(get_current_active_user)])


@router.get("/vendedores", response_model=List[VendedorRankingResponse])
async def get_vendedores_ranking(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ranking de vendedores."""
    ventas_service = VentasService(db)
    service = VendedoresService(ventas_service)
    return await service.get_ranking(filters)


@router.get("/vendedores/{nombre}", response_model=VendedorDetalleResponse)
async def get_vendedor_detalle(
    nombre: str,
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene detalle de un vendedor."""
    ventas_service = VentasService(db)
    service = VendedoresService(ventas_service)
    return await service.get_detalle(nombre, filters)


# Rutas de compras
@router.get("/compras/sugerencias", response_model=List[SugerenciaCompraResponse])
async def get_sugerencias_compra(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene sugerencias de compra."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_sugerencias(filters)


@router.get("/compras/proveedores", response_model=List[ResumenProveedorResponse])
async def get_resumen_proveedores(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene resumen de compras por proveedor."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_resumen_proveedores(filters)


@router.get("/compras/orden/{proveedor}", response_model=OrdenCompraResponse)
async def get_orden_compra(
    proveedor: str,
    prioridad_minima: Optional[str] = Query(None),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Genera orden de compra para un proveedor."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_orden_compra(proveedor, filters, prioridad_minima)


@router.get("/compras/alertas-stock")
async def get_alertas_stock(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene alertas de stock crítico."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_alertas_stock(filters)



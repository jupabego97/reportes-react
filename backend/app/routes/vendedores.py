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
from app.services.predicciones import PrediccionesService
from app.routes.ventas import get_filter_params
from app.cache import COMPRAS_CACHE, _cache_key, get_cached, set_cached

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
    lead_time_default: Optional[int] = Query(7, ge=1, le=90, description="Lead time por defecto (días)"),
    safety_dias_base: Optional[int] = Query(3, ge=0, le=30, description="Días base para safety stock"),
    db: AsyncSession = Depends(get_db),
):
    """Sugerencias de compra con demanda proyectada. Cache TTL 15 min."""
    extra = f"lt{lead_time_default or 7}_sd{safety_dias_base or 3}"
    key = _cache_key("compras", filters, extra)
    cached = get_cached(COMPRAS_CACHE, key)
    if cached is not None:
        return cached
    ventas_service = VentasService(db)
    predicciones_service = PrediccionesService(ventas_service)
    service = ComprasService(
        db,
        ventas_service,
        predicciones_service,
        lead_time_default=lead_time_default or 7,
        safety_dias_base=safety_dias_base or 3,
    )
    result = await service.get_sugerencias(filters)
    set_cached(COMPRAS_CACHE, key, result)
    return result


@router.get("/compras/proveedores", response_model=List[ResumenProveedorResponse])
async def get_resumen_proveedores(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene resumen de compras por proveedor."""
    ventas_service = VentasService(db)
    predicciones_service = PrediccionesService(ventas_service)
    service = ComprasService(db, ventas_service, predicciones_service)
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
    predicciones_service = PrediccionesService(ventas_service)
    service = ComprasService(db, ventas_service, predicciones_service)
    return await service.get_orden_compra(proveedor, filters, prioridad_minima)


@router.get("/compras/alertas-stock")
async def get_alertas_stock(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene alertas de stock crítico."""
    ventas_service = VentasService(db)
    predicciones_service = PrediccionesService(ventas_service)
    service = ComprasService(db, ventas_service, predicciones_service)
    return await service.get_alertas_stock(filters)



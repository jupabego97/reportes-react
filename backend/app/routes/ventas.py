"""
Rutas de ventas y datos principales.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.models.schemas import (
    FilterParams,
    VentaResponse,
    FiltrosOpciones,
    MargenResponse,
    PrediccionResponse,
    PrediccionDesgloseResponse,
)
from app.services.ventas import VentasService
from app.services.margenes import MargenesService
from app.services.predicciones import PrediccionesService
from app.services.abc import ABCService
from app.cache import (
    PREDICCIONES_CACHE,
    PREDICCIONES_DESGLOSE_CACHE,
    _cache_key,
    get_cached,
    set_cached,
)

router = APIRouter(prefix="/api", tags=["ventas"], dependencies=[Depends(get_current_active_user)])


def get_filter_params(
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    productos: Optional[List[str]] = Query(None),
    vendedores: Optional[List[str]] = Query(None),
    familias: Optional[List[str]] = Query(None),
    metodos: Optional[List[str]] = Query(None),
    proveedores: Optional[List[str]] = Query(None),
    precio_min: Optional[float] = Query(None),
    precio_max: Optional[float] = Query(None),
    cantidad_min: Optional[int] = Query(None),
    cantidad_max: Optional[int] = Query(None),
) -> FilterParams:
    """Dependency para obtener parámetros de filtro."""
    return FilterParams(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        productos=productos,
        vendedores=vendedores,
        familias=familias,
        metodos=metodos,
        proveedores=proveedores,
        precio_min=precio_min,
        precio_max=precio_max,
        cantidad_min=cantidad_min,
        cantidad_max=cantidad_max,
    )


@router.get("/ventas")
async def get_ventas(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ventas paginadas con filtros aplicados."""
    service = VentasService(db)
    ventas, total, total_pages = await service.get_ventas_paginated(filters, page, page_size)
    return {
        "data": ventas,
        "total_registros": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/ventas/all")
async def get_all_ventas(
    limit: int = Query(10000, ge=1, le=50000, description="Máximo de registros a devolver"),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene todas las ventas sin paginación (para exportación). Máximo 50000 registros."""
    service = VentasService(db)
    ventas, total = await service.get_ventas(filters, max_rows=limit)
    return {"data": ventas, "total_registros": total}


@router.get("/filtros/opciones", response_model=FiltrosOpciones)
async def get_filtros_opciones(db: AsyncSession = Depends(get_db)):
    """Obtiene opciones disponibles para filtros."""
    service = VentasService(db)
    return await service.get_filtros_opciones()


@router.get("/ventas/por-dia")
async def get_ventas_por_dia(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ventas agrupadas por día."""
    service = VentasService(db)
    return await service.get_ventas_por_dia(filters)


@router.get("/ventas/por-vendedor")
async def get_ventas_por_vendedor(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ventas agrupadas por vendedor."""
    service = VentasService(db)
    return await service.get_ventas_por_vendedor(filters)


@router.get("/ventas/por-familia")
async def get_ventas_por_familia(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ventas agrupadas por familia."""
    service = VentasService(db)
    return await service.get_ventas_por_familia(filters)


@router.get("/ventas/por-metodo")
async def get_ventas_por_metodo(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ventas agrupadas por método de pago."""
    service = VentasService(db)
    return await service.get_ventas_por_metodo(filters)


@router.get("/ventas/top-productos-cantidad")
async def get_top_productos_cantidad(
    limit: int = Query(10, ge=1, le=50),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene top productos por cantidad vendida."""
    service = VentasService(db)
    return await service.get_top_productos_cantidad(filters, limit)


@router.get("/margenes", response_model=MargenResponse)
async def get_margenes(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene análisis de márgenes."""
    ventas_service = VentasService(db)
    service = MargenesService(ventas_service)
    return await service.get_analisis_margenes(filters)


@router.get("/predicciones", response_model=PrediccionResponse)
async def get_predicciones(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene predicciones de ventas (nivel global). Cache TTL 15 min."""
    key = _cache_key("pred", filters)
    cached = get_cached(PREDICCIONES_CACHE, key)
    if cached is not None:
        return cached
    ventas_service = VentasService(db)
    service = PrediccionesService(ventas_service)
    result = await service.get_predicciones(filters)
    set_cached(PREDICCIONES_CACHE, key, result)
    return result


@router.get("/predicciones/desglose", response_model=PrediccionDesgloseResponse)
async def get_predicciones_desglose(
    nivel: str = Query("familia", description="Agrupación: familia o producto"),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Predicciones desglosadas por familia o producto. Cache TTL 15 min."""
    if nivel not in ("familia", "producto"):
        nivel = "familia"
    key = _cache_key("pred_desglose", filters, nivel)
    cached = get_cached(PREDICCIONES_DESGLOSE_CACHE, key)
    if cached is not None:
        return cached
    ventas_service = VentasService(db)
    service = PrediccionesService(ventas_service)
    result = await service.get_predicciones_desglose(filters, nivel)
    set_cached(PREDICCIONES_DESGLOSE_CACHE, key, result)
    return result


@router.get("/predicciones/backtest")
async def get_predicciones_backtest(
    semanas: int = Query(8, ge=2, le=12, description="Semanas para walk-forward validation"),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Backtesting rolling: WAPE/MAPE sobre últimas N semanas."""
    ventas_service = VentasService(db)
    service = PrediccionesService(ventas_service)
    return await service.get_backtest_metricas(filters, semanas)


@router.get("/abc")
async def get_abc(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene análisis ABC."""
    ventas_service = VentasService(db)
    service = ABCService(ventas_service)
    return await service.get_analisis_abc(filters)


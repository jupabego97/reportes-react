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
    ABCResponse,
)
from app.services.ventas import VentasService
from app.services.margenes import MargenesService
from app.services.predicciones import PrediccionesService
from app.services.abc import ABCService

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
    """Obtiene predicciones de ventas."""
    ventas_service = VentasService(db)
    service = PrediccionesService(ventas_service)
    return await service.get_predicciones(filters)


@router.get("/abc", response_model=ABCResponse)
async def get_abc(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene análisis ABC."""
    ventas_service = VentasService(db)
    service = ABCService(ventas_service)
    return await service.get_analisis_abc(filters)


"""
Rutas del dashboard - métricas y alertas.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    FilterParams,
    MetricasResponse,
    AlertaResponse,
    TopProductoResponse,
    TopVendedorResponse,
)
from app.services.ventas import VentasService
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metricas", response_model=MetricasResponse)
async def get_metricas(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene métricas principales del dashboard."""
    service = VentasService(db)
    return await service.get_metricas(filters)


@router.get("/alertas", response_model=List[AlertaResponse])
async def get_alertas(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene alertas del sistema."""
    service = VentasService(db)
    return await service.get_alertas(filters)


@router.get("/top-productos", response_model=List[TopProductoResponse])
async def get_top_productos(
    limit: int = Query(5, ge=1, le=20),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene top productos más vendidos."""
    service = VentasService(db)
    return await service.get_top_productos(filters, limit)


@router.get("/top-vendedores", response_model=List[TopVendedorResponse])
async def get_top_vendedores(
    limit: int = Query(5, ge=1, le=20),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene top vendedores."""
    service = VentasService(db)
    return await service.get_top_vendedores(filters, limit)


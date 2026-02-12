"""
Rutas del dashboard - métricas y alertas.
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
    MetricasResponse,
    AlertaResponse,
    TopProductoResponse,
    TopVendedorResponse,
)
from app.services.ventas import VentasService
from app.services.inventario import InventarioService
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_active_user)])


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


@router.get("/salud-inventario")
async def get_salud_inventario(db: AsyncSession = Depends(get_db)):
    """Salud del inventario: % productos con stock normal, top 3 criticos."""
    inv_service = InventarioService(db)
    resumen = await inv_service.get_resumen_inventario()
    alertas = await inv_service.get_alertas_inventario()

    total = resumen.get("total_productos", 0) or 0
    normales = resumen.get("productos_normales", 0) or 0
    exceso = resumen.get("productos_exceso", 0) or 0
    salud_porcentaje = round((normales + exceso) / total * 100, 1) if total > 0 else 100

    top_criticos = []
    for a in alertas:
        if a.get("tipo") == "error" and a.get("datos"):
            top_criticos = [{"nombre": p.get("nombre"), "dias_cobertura": p.get("dias_cobertura"), "estado_stock": p.get("estado_stock")} for p in (a["datos"][:3])]
            break

    return {"salud_porcentaje": salud_porcentaje, "top_criticos": top_criticos, "total_productos": total}


@router.get("/top-vendedores", response_model=List[TopVendedorResponse])
async def get_top_vendedores(
    limit: int = Query(5, ge=1, le=20),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene top vendedores."""
    service = VentasService(db)
    return await service.get_top_vendedores(filters, limit)



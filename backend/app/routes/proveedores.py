"""
Rutas de análisis de proveedores.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.models.schemas import FilterParams
from app.services.proveedores import ProveedoresService
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"], dependencies=[Depends(get_current_active_user)])


@router.get("/lista")
async def get_lista_proveedores(db: AsyncSession = Depends(get_db)):
    """Obtiene lista de todos los proveedores."""
    service = ProveedoresService(db)
    return await service.get_lista_proveedores()


@router.get("/resumen")
async def get_resumen_proveedores(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene resumen de todos los proveedores."""
    service = ProveedoresService(db)
    return await service.get_resumen_proveedores(filters)


@router.get("/ranking")
async def get_ranking_proveedores(
    criterio: str = Query("ventas", enum=["ventas", "margen", "unidades", "productos"]),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ranking de proveedores por criterio."""
    service = ProveedoresService(db)
    return await service.get_ranking_proveedores(filters, criterio)


@router.get("/detalle/{proveedor}")
async def get_detalle_proveedor(
    proveedor: str,
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene detalle completo de un proveedor."""
    service = ProveedoresService(db)
    return await service.get_detalle_proveedor(proveedor, filters)


@router.get("/comparativa")
async def get_comparativa_proveedores(
    proveedores: List[str] = Query(...),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Compara múltiples proveedores."""
    service = ProveedoresService(db)
    return await service.get_comparativa_proveedores(proveedores, filters)



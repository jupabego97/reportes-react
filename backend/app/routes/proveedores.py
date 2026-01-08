"""
Rutas de análisis de proveedores mejoradas.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import FilterParams
from app.services.proveedores import ProveedoresService
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


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
    """Obtiene resumen de todos los proveedores con alertas de stock."""
    service = ProveedoresService(db)
    return await service.get_resumen_proveedores(filters)


@router.get("/ranking")
async def get_ranking_proveedores(
    criterio: str = Query("ventas", enum=["ventas", "margen", "unidades", "productos", "alertas"]),
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
    """Obtiene detalle completo de un proveedor con tendencia y alertas."""
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


# ===== NUEVOS ENDPOINTS =====

@router.get("/stock/{proveedor}")
async def get_stock_proveedor(
    proveedor: str,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene estado de stock de todos los productos de un proveedor."""
    service = ProveedoresService(db)
    return await service.get_stock_proveedor(proveedor)


@router.get("/sugerencias-compra/{proveedor}")
async def get_sugerencias_compra(
    proveedor: str,
    db: AsyncSession = Depends(get_db),
):
    """Genera lista de compras sugerida para un proveedor."""
    service = ProveedoresService(db)
    return await service.get_sugerencias_compra_proveedor(proveedor)


@router.get("/score/{proveedor}")
async def get_score_proveedor(
    proveedor: str,
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Calcula score de 0-100 para un proveedor."""
    service = ProveedoresService(db)
    return await service.get_score_proveedor(proveedor, filters)


@router.get("/comparativa-precios")
async def get_comparativa_precios(
    db: AsyncSession = Depends(get_db),
):
    """Compara precios del mismo producto entre diferentes proveedores."""
    service = ProveedoresService(db)
    return await service.get_comparativa_precios()


@router.get("/tendencia/{proveedor}")
async def get_tendencia_proveedor(
    proveedor: str,
    db: AsyncSession = Depends(get_db),
):
    """Compara ventas del mes actual vs mes anterior."""
    service = ProveedoresService(db)
    return await service.get_tendencia_proveedor(proveedor)

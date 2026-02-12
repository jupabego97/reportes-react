"""
Rutas de inventario.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.services.inventario import InventarioService

router = APIRouter(
    prefix="/api/inventario",
    tags=["inventario"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("")
async def get_inventario(
    estado: Optional[str] = Query(None, description="Filtrar por estado: critico, bajo, normal, exceso"),
    familia: Optional[str] = Query(None, description="Filtrar por familia"),
    proveedor: Optional[str] = Query(None, description="Filtrar por proveedor"),
    ordenar_por: str = Query("venta_diaria", description="Campo para ordenar"),
    limite: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene inventario completo con métricas."""
    service = InventarioService(db)
    productos = await service.get_inventario_completo()
    
    # Aplicar filtros
    if estado:
        estado_map = {
            "critico": "🔴 Crítico",
            "bajo": "🟠 Bajo",
            "normal": "🟢 Normal",
            "exceso": "🔵 Exceso",
        }
        estado_filtro = estado_map.get(estado.lower())
        if estado_filtro:
            productos = [p for p in productos if p["estado_stock"] == estado_filtro]
    
    if familia:
        productos = [p for p in productos if p.get("familia") == familia]
    
    if proveedor:
        productos = [p for p in productos if p.get("proveedor") == proveedor]
    
    # Ordenar
    if ordenar_por in ["venta_diaria", "stock_actual", "dias_cobertura", "rotacion", "valor_inventario"]:
        productos = sorted(
            productos, 
            key=lambda x: x.get(ordenar_por) or 0, 
            reverse=ordenar_por != "dias_cobertura"
        )
    
    return {
        "data": productos[:limite],
        "total": len(productos),
    }


@router.get("/resumen")
async def get_resumen_inventario(db: AsyncSession = Depends(get_db)):
    """Obtiene resumen ejecutivo del inventario."""
    service = InventarioService(db)
    return await service.get_resumen_inventario()


@router.get("/alertas")
async def get_alertas_inventario(db: AsyncSession = Depends(get_db)):
    """Obtiene alertas de inventario priorizadas."""
    service = InventarioService(db)
    return await service.get_alertas_inventario()


@router.get("/por-familia")
async def get_inventario_por_familia(db: AsyncSession = Depends(get_db)):
    """Obtiene valor del inventario por familia de productos."""
    service = InventarioService(db)
    return await service.get_valor_por_familia()


@router.get("/por-proveedor")
async def get_inventario_por_proveedor(db: AsyncSession = Depends(get_db)):
    """Obtiene valor del inventario por proveedor."""
    service = InventarioService(db)
    return await service.get_valor_por_proveedor()


@router.get("/producto/{nombre}")
async def get_producto_detalle(
    nombre: str,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene detalle completo de un producto."""
    service = InventarioService(db)
    producto = await service.get_producto_detalle(nombre)
    
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return producto


@router.get("/agotados")
async def get_productos_agotados(db: AsyncSession = Depends(get_db)):
    """Obtiene productos que se agotaron en la última semana y últimas 2 semanas."""
    service = InventarioService(db)
    return await service.get_productos_agotados()


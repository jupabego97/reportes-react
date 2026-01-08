"""
Rutas de vendedores.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    FilterParams,
    VendedorRankingResponse,
    VendedorDetalleResponse,
    SugerenciaCompraResponse,
    ResumenProveedorResponse,
    OrdenCompraResponse,
)
from app.services.ventas import VentasService
from app.services.compras import ComprasService
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api", tags=["vendedores"])


@router.get("/vendedores", response_model=List[VendedorRankingResponse])
async def get_vendedores_ranking(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ranking de vendedores."""
    service = VentasService(db)
    ventas, _ = await service.get_ventas(filters)
    
    if not ventas:
        return []
    
    # Agrupar por vendedor
    vendedores = {}
    for v in ventas:
        if v.vendedor:
            if v.vendedor not in vendedores:
                vendedores[v.vendedor] = {
                    "ventas_totales": 0,
                    "margen_total": 0,
                    "productos": set(),
                    "unidades": 0,
                    "precios": [],
                }
            vendedores[v.vendedor]["ventas_totales"] += v.total_venta
            vendedores[v.vendedor]["margen_total"] += v.total_margen or 0
            vendedores[v.vendedor]["productos"].add(v.nombre)
            vendedores[v.vendedor]["unidades"] += v.cantidad
            vendedores[v.vendedor]["precios"].append(v.precio)
    
    # Calcular promedio de ventas
    promedio_ventas = sum(d["ventas_totales"] for d in vendedores.values()) / len(vendedores) if vendedores else 0
    
    ranking = []
    for vendedor, data in vendedores.items():
        ticket_promedio = sum(data["precios"]) / len(data["precios"]) if data["precios"] else 0
        margen_porcentaje = (data["margen_total"] / data["ventas_totales"] * 100) if data["ventas_totales"] > 0 else 0
        
        # Determinar rendimiento
        if data["ventas_totales"] > promedio_ventas * 1.2:
            rendimiento = "🟢 Excelente"
        elif data["ventas_totales"] > promedio_ventas * 0.8:
            rendimiento = "🟡 Normal"
        else:
            rendimiento = "🔴 Bajo"
        
        ranking.append(VendedorRankingResponse(
            vendedor=vendedor,
            ventas_totales=round(data["ventas_totales"], 2),
            margen_total=round(data["margen_total"], 2),
            productos_unicos=len(data["productos"]),
            unidades=data["unidades"],
            ticket_promedio=round(ticket_promedio, 2),
            margen_porcentaje=round(margen_porcentaje, 2),
            rendimiento=rendimiento,
        ))
    
    # Ordenar por ventas totales
    ranking.sort(key=lambda x: x.ventas_totales, reverse=True)
    
    return ranking


@router.get("/vendedores/{nombre}", response_model=VendedorDetalleResponse)
async def get_vendedor_detalle(
    nombre: str,
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene detalle de un vendedor."""
    service = VentasService(db)
    ventas, _ = await service.get_ventas(filters)
    
    # Filtrar por vendedor
    ventas_vendedor = [v for v in ventas if v.vendedor == nombre]
    
    if not ventas_vendedor:
        return VendedorDetalleResponse(
            vendedor=nombre,
            ventas_totales=0,
            productos_unicos=0,
            ticket_promedio=0,
            margen_porcentaje=0,
            delta_vs_promedio=0,
            ventas_diarias=[],
            top_productos=[],
            metodos_pago=[],
        )
    
    # Calcular métricas
    ventas_totales = sum(v.total_venta for v in ventas_vendedor)
    productos_unicos = len(set(v.nombre for v in ventas_vendedor))
    ticket_promedio = sum(v.precio for v in ventas_vendedor) / len(ventas_vendedor)
    
    margen_total = sum(v.total_margen for v in ventas_vendedor if v.total_margen)
    margen_porcentaje = (margen_total / ventas_totales * 100) if ventas_totales > 0 else 0
    
    # Calcular delta vs promedio del equipo
    ventas_por_vendedor = {}
    for v in ventas:
        if v.vendedor:
            ventas_por_vendedor[v.vendedor] = ventas_por_vendedor.get(v.vendedor, 0) + v.total_venta
    
    promedio_equipo = sum(ventas_por_vendedor.values()) / len(ventas_por_vendedor) if ventas_por_vendedor else 0
    delta_vs_promedio = ((ventas_totales - promedio_equipo) / promedio_equipo * 100) if promedio_equipo > 0 else 0
    
    # Ventas diarias
    ventas_dia = {}
    for v in ventas_vendedor:
        fecha = str(v.fecha_venta)
        if fecha not in ventas_dia:
            ventas_dia[fecha] = 0
        ventas_dia[fecha] += v.total_venta
    
    ventas_diarias = [
        {"fecha": fecha, "total_venta": round(total, 2)}
        for fecha, total in sorted(ventas_dia.items())
    ]
    
    # Top productos
    productos = {}
    for v in ventas_vendedor:
        if v.nombre not in productos:
            productos[v.nombre] = {"total_venta": 0, "cantidad": 0}
        productos[v.nombre]["total_venta"] += v.total_venta
        productos[v.nombre]["cantidad"] += v.cantidad
    
    top_productos = [
        {"nombre": nombre, "total_venta": round(data["total_venta"], 2), "cantidad": data["cantidad"]}
        for nombre, data in sorted(productos.items(), key=lambda x: x[1]["total_venta"], reverse=True)[:10]
    ]
    
    # Métodos de pago
    metodos = {}
    for v in ventas_vendedor:
        if v.metodo:
            if v.metodo not in metodos:
                metodos[v.metodo] = 0
            metodos[v.metodo] += v.total_venta
    
    metodos_pago = [
        {"metodo": metodo, "total_venta": round(total, 2)}
        for metodo, total in metodos.items()
    ]
    
    return VendedorDetalleResponse(
        vendedor=nombre,
        ventas_totales=round(ventas_totales, 2),
        productos_unicos=productos_unicos,
        ticket_promedio=round(ticket_promedio, 2),
        margen_porcentaje=round(margen_porcentaje, 2),
        delta_vs_promedio=round(delta_vs_promedio, 1),
        ventas_diarias=ventas_diarias,
        top_productos=top_productos,
        metodos_pago=metodos_pago,
    )


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


@router.get("/compras/resumen-completo")
async def get_resumen_completo(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene resumen completo con ROI, inversión y productos agotados."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_resumen_completo(filters)


@router.get("/compras/orden-proveedor/{proveedor}")
async def get_orden_proveedor(
    proveedor: str,
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Genera orden de compra detallada para un proveedor."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_orden_proveedor(proveedor, filters)


@router.get("/compras/puntos-reorden")
async def get_puntos_reorden(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene puntos de reorden para productos de alta rotación."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_puntos_reorden(filters)


@router.get("/compras/agotados")
async def get_productos_agotados(
    db: AsyncSession = Depends(get_db),
):
    """Obtiene productos agotados en última semana y 2 semanas."""
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    return await service.get_productos_agotados()

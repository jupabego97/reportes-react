"""
Rutas de exportación de datos.
"""
from datetime import date, datetime
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.database import get_db
from app.models.schemas import FilterParams
from app.services.ventas import VentasService
from app.services.pdf_generator import PDFReportGenerator
from app.routes.ventas import get_filter_params

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
async def export_csv(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Exporta datos a CSV."""
    service = VentasService(db)
    ventas, _ = await service.get_ventas(filters)
    
    # Convertir a DataFrame
    data = [
        {
            "fecha_venta": v.fecha_venta,
            "nombre": v.nombre,
            "precio": v.precio,
            "cantidad": v.cantidad,
            "total_venta": v.total_venta,
            "vendedor": v.vendedor,
            "familia": v.familia,
            "metodo": v.metodo,
            "proveedor": v.proveedor_moda,
            "precio_compra": v.precio_promedio_compra,
            "margen": v.margen,
            "margen_porcentaje": v.margen_porcentaje,
            "total_margen": v.total_margen,
        }
        for v in ventas
    ]
    
    df = pd.DataFrame(data)
    
    # Generar CSV
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    filename = f"reporte_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/excel")
async def export_excel(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Exporta datos a Excel."""
    service = VentasService(db)
    ventas, _ = await service.get_ventas(filters)
    
    # Convertir a DataFrame
    data = [
        {
            "fecha_venta": v.fecha_venta,
            "nombre": v.nombre,
            "precio": v.precio,
            "cantidad": v.cantidad,
            "total_venta": v.total_venta,
            "vendedor": v.vendedor,
            "familia": v.familia,
            "metodo": v.metodo,
            "proveedor": v.proveedor_moda,
            "precio_compra": v.precio_promedio_compra,
            "margen": v.margen,
            "margen_porcentaje": v.margen_porcentaje,
            "total_margen": v.total_margen,
        }
        for v in ventas
    ]
    
    df = pd.DataFrame(data)
    
    # Crear Excel con múltiples hojas
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ventas')
        
        # Hoja de resumen
        resumen = pd.DataFrame({
            'Métrica': ['Total Ventas', 'Total Registros', 'Precio Promedio', 
                       'Margen Promedio', 'Margen Total'],
            'Valor': [
                f"${df['total_venta'].sum():,.2f}" if not df.empty else "$0",
                len(df),
                f"${df['precio'].mean():,.2f}" if not df.empty else "$0",
                f"${df['margen'].mean():,.2f}" if not df.empty and df['margen'].notna().any() else "N/A",
                f"${df['total_margen'].sum():,.2f}" if not df.empty and df['total_margen'].notna().any() else "N/A"
            ]
        })
        resumen.to_excel(writer, index=False, sheet_name='Resumen')
    
    output.seek(0)
    
    filename = f"reporte_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/pdf")
async def export_pdf(
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Exporta reporte completo a PDF."""
    from app.services.margenes import MargenesService
    
    service = VentasService(db)
    
    # Obtener datos
    ventas, _ = await service.get_ventas(filters)
    metricas = await service.get_metricas(filters)
    top_productos = await service.get_top_productos_cantidad(filters, 10)
    vendedores = await service.get_ventas_por_vendedor(filters)
    familias = await service.get_ventas_por_familia(filters)
    alertas = await service.get_alertas(filters)
    
    # Generar PDF
    pdf_generator = PDFReportGenerator()
    pdf_bytes = pdf_generator.generate_sales_report(
        metricas=metricas.dict() if hasattr(metricas, 'dict') else metricas,
        top_productos=[p.dict() if hasattr(p, 'dict') else p for p in top_productos],
        top_vendedores=vendedores,
        ventas_por_familia=familias,
        alertas=[a.dict() if hasattr(a, 'dict') else a for a in alertas],
        fecha_inicio=str(filters.fecha_inicio) if filters.fecha_inicio else None,
        fecha_fin=str(filters.fecha_fin) if filters.fecha_fin else None,
    )
    
    filename = f"reporte_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/orden-compra/{proveedor}/csv")
async def export_orden_compra_csv(
    proveedor: str,
    prioridad_minima: Optional[str] = Query(None),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Exporta orden de compra a CSV."""
    from app.services.compras import ComprasService
    
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    orden = await service.get_orden_compra(proveedor, filters, prioridad_minima)
    
    # Convertir a DataFrame
    data = [
        {
            "producto": item.nombre,
            "familia": item.familia,
            "cantidad": item.cantidad_sugerida,
            "precio_unitario": item.precio_compra,
            "subtotal": item.costo_estimado,
        }
        for item in orden.items
    ]
    
    df = pd.DataFrame(data)
    
    # Generar CSV
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    filename = f"orden_compra_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/orden-compra/{proveedor}/excel")
async def export_orden_compra_excel(
    proveedor: str,
    prioridad_minima: Optional[str] = Query(None),
    filters: FilterParams = Depends(get_filter_params),
    db: AsyncSession = Depends(get_db),
):
    """Exporta orden de compra a Excel."""
    from app.services.compras import ComprasService
    
    ventas_service = VentasService(db)
    service = ComprasService(db, ventas_service)
    orden = await service.get_orden_compra(proveedor, filters, prioridad_minima)
    
    # Convertir a DataFrame
    data = [
        {
            "Producto": item.nombre,
            "Familia": item.familia,
            "Cantidad": item.cantidad_sugerida,
            "Precio Unit.": item.precio_compra,
            "Subtotal": item.costo_estimado,
        }
        for item in orden.items
    ]
    
    df = pd.DataFrame(data)
    
    # Crear Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Orden de Compra')
        
        # Hoja de resumen
        resumen = pd.DataFrame({
            'Campo': ['Proveedor', 'Fecha', 'Total Productos', 'Total Unidades', 'Costo Total'],
            'Valor': [
                orden.proveedor,
                orden.fecha.strftime('%Y-%m-%d %H:%M'),
                orden.total_productos,
                f"{orden.total_unidades:,}",
                f"${orden.costo_total:,.2f}"
            ]
        })
        resumen.to_excel(writer, index=False, sheet_name='Resumen')
    
    output.seek(0)
    
    filename = f"orden_compra_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


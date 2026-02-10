"""
Servicio de análisis de márgenes.
"""
from typing import List

from app.models.schemas import FilterParams, MargenResponse, MargenProductoResponse
from app.services.ventas import VentasService


class MargenesService:
    """Servicio para análisis de márgenes."""
    
    def __init__(self, ventas_service: VentasService):
        self.ventas_service = ventas_service
    
    async def get_analisis_margenes(self, filters: FilterParams) -> MargenResponse:
        """Obtiene análisis completo de márgenes."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        
        # Filtrar ventas con precio de compra
        ventas_con_margen = [v for v in ventas if v.precio_promedio_compra is not None]
        sin_datos_costo = bool(ventas) and not bool(ventas_con_margen)
        
        if not ventas_con_margen:
            # No hay datos de costo suficientes para calcular márgenes
            return MargenResponse(
                margen_promedio=0,
                margen_total=0,
                ventas_con_margen_total=0,
                ventas_rentables=0,
                ventas_no_rentables=0,
                datos_scatter=[],
                top_margen=[],
                bottom_margen=[],
                sin_datos_costo=sin_datos_costo,
                margenes_por_familia=[],
            )
        
        # Métricas generales
        margenes = [v.margen for v in ventas_con_margen if v.margen is not None]
        margen_promedio = sum(margenes) / len(margenes) if margenes else 0
        margen_total = sum(v.total_margen for v in ventas_con_margen if v.total_margen is not None)
        ventas_con_margen_total = sum(v.total_venta for v in ventas_con_margen if v.total_venta is not None)
        
        ventas_rentables = len([v for v in ventas_con_margen if v.margen and v.margen > 0])
        ventas_no_rentables = len([v for v in ventas_con_margen if v.margen and v.margen <= 0])
        
        # Datos para scatter plot (máximo 200)
        datos_scatter = [
            MargenProductoResponse(
                nombre=v.nombre,
                precio=v.precio,
                precio_promedio_compra=v.precio_promedio_compra,
                cantidad=v.cantidad,
                margen=v.margen,
                margen_porcentaje=v.margen_porcentaje,
                total_margen=v.total_margen,
                vendedor=v.vendedor,
            )
            for v in ventas_con_margen[:200]
        ]
        
        # Agrupar por producto para top/bottom
        productos_margen = {}
        familias_margen = {}
        for v in ventas_con_margen:
            # Agrupación por producto
            if v.nombre not in productos_margen:
                productos_margen[v.nombre] = {
                    "margen_sum": 0.0,
                    "total_margen": 0.0,
                    "cantidad": 0,
                    "count": 0,
                }
            productos_margen[v.nombre]["margen_sum"] += float(v.margen or 0)
            productos_margen[v.nombre]["total_margen"] += float(v.total_margen or 0)
            productos_margen[v.nombre]["cantidad"] += v.cantidad
            productos_margen[v.nombre]["count"] += 1

            # Agrupación por familia
            familia = v.familia or "Sin familia"
            if familia not in familias_margen:
                familias_margen[familia] = {
                    "margen_total": 0.0,
                    "ventas_totales": 0.0,
                    "cantidad_total": 0,
                }
            familias_margen[familia]["margen_total"] += float(v.total_margen or 0)
            familias_margen[familia]["ventas_totales"] += float(v.total_venta or 0)
            familias_margen[familia]["cantidad_total"] += v.cantidad
        
        productos_list = [
            {
                "nombre": nombre,
                "margen": round(data["margen_sum"] / data["count"], 2) if data["count"] else 0,
                "total_margen": round(data["total_margen"], 2),
                "cantidad": data["cantidad"],
            }
            for nombre, data in productos_margen.items()
        ]
        
        # Top 10 por margen total
        top_margen = sorted(productos_list, key=lambda x: x["total_margen"], reverse=True)[:10]
        
        # Bottom 10 por margen total
        bottom_margen = sorted(productos_list, key=lambda x: x["total_margen"])[:10]

        # Márgenes por familia
        margenes_por_familia = [
            {
                "familia": familia,
                "margen_total": round(data["margen_total"], 2),
                "ventas_totales": round(data["ventas_totales"], 2),
                "cantidad_total": data["cantidad_total"],
                "margen_porcentaje": round(
                    (data["margen_total"] / data["ventas_totales"] * 100)
                    if data["ventas_totales"] > 0
                    else 0,
                    2,
                ),
            }
            for familia, data in familias_margen.items()
        ]
        margenes_por_familia.sort(key=lambda x: x["margen_total"], reverse=True)
        
        return MargenResponse(
            margen_promedio=round(margen_promedio, 2),
            margen_total=round(margen_total, 2),
            ventas_con_margen_total=round(ventas_con_margen_total, 2),
            ventas_rentables=ventas_rentables,
            ventas_no_rentables=ventas_no_rentables,
            datos_scatter=datos_scatter,
            top_margen=top_margen,
            bottom_margen=bottom_margen,
            sin_datos_costo=sin_datos_costo,
            margenes_por_familia=margenes_por_familia,
        )



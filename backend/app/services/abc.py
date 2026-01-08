"""
Servicio de análisis ABC (Pareto) mejorado.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.models.schemas import FilterParams, ABCResponse, ProductoABCResponse
from app.services.ventas import VentasService


@dataclass
class ABCCriterio:
    """Criterios disponibles para análisis ABC."""
    VENTAS = "ventas"
    CANTIDAD = "cantidad"
    MARGEN = "margen"
    FRECUENCIA = "frecuencia"


class ABCService:
    """Servicio para análisis ABC mejorado."""
    
    def __init__(self, ventas_service: VentasService):
        self.ventas_service = ventas_service
    
    async def get_analisis_abc(
        self, 
        filters: FilterParams, 
        criterio: str = "ventas"
    ) -> Dict[str, Any]:
        """Genera análisis ABC de productos con métricas extendidas."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        
        if not ventas:
            return self._empty_response()
        
        # Agrupar ventas por producto con métricas extendidas
        productos = {}
        for v in ventas:
            if v.nombre not in productos:
                productos[v.nombre] = {
                    "total_venta": 0, 
                    "cantidad": 0, 
                    "costo_total": 0,
                    "transacciones": 0,
                    "familia": v.familia,
                    "proveedor": getattr(v, 'proveedor_moda', None),
                }
            productos[v.nombre]["total_venta"] += v.total_venta
            productos[v.nombre]["cantidad"] += v.cantidad
            productos[v.nombre]["transacciones"] += 1
            # Calcular costo si está disponible
            if hasattr(v, 'precio_promedio_compra') and v.precio_promedio_compra:
                productos[v.nombre]["costo_total"] += v.precio_promedio_compra * v.cantidad
        
        # Calcular margen por producto
        for nombre, data in productos.items():
            if data["costo_total"] > 0:
                data["margen"] = data["total_venta"] - data["costo_total"]
                data["margen_porcentaje"] = (data["margen"] / data["total_venta"] * 100) if data["total_venta"] > 0 else 0
            else:
                data["margen"] = None
                data["margen_porcentaje"] = None
        
        # Determinar qué métrica usar para ordenar según criterio
        if criterio == "cantidad":
            key_func = lambda x: x[1]["cantidad"]
            total_key = "cantidad"
        elif criterio == "margen":
            key_func = lambda x: x[1]["margen"] if x[1]["margen"] else 0
            total_key = "margen"
        elif criterio == "frecuencia":
            key_func = lambda x: x[1]["transacciones"]
            total_key = "transacciones"
        else:  # ventas (default)
            key_func = lambda x: x[1]["total_venta"]
            total_key = "total_venta"
        
        # Ordenar por criterio descendente
        productos_ordenados = sorted(
            productos.items(),
            key=key_func,
            reverse=True
        )
        
        total_valor = sum(key_func((n, d)) for n, d in productos_ordenados)
        total_ventas = sum(p[1]["total_venta"] for p in productos_ordenados)
        total_margen = sum(p[1]["margen"] or 0 for p in productos_ordenados)
        
        # Calcular porcentaje acumulado y clasificar
        productos_abc = []
        acumulado = 0
        
        for nombre, data in productos_ordenados:
            valor_criterio = key_func((nombre, data))
            porcentaje = (valor_criterio / total_valor * 100) if total_valor > 0 else 0
            acumulado += porcentaje
            
            if acumulado <= 80:
                clasificacion = "A"
            elif acumulado <= 95:
                clasificacion = "B"
            else:
                clasificacion = "C"
            
            productos_abc.append({
                "nombre": nombre,
                "categoria": clasificacion,
                "total_venta": round(data["total_venta"], 2),
                "cantidad": data["cantidad"],
                "transacciones": data["transacciones"],
                "margen": round(data["margen"], 2) if data["margen"] else None,
                "margen_porcentaje": round(data["margen_porcentaje"], 1) if data["margen_porcentaje"] else None,
                "familia": data["familia"],
                "proveedor": data["proveedor"],
                "porcentaje": round(porcentaje, 2),
                "porcentaje_acumulado": round(acumulado, 2),
            })
        
        # Calcular métricas por clase
        clase_a = [p for p in productos_abc if p["categoria"] == "A"]
        clase_b = [p for p in productos_abc if p["categoria"] == "B"]
        clase_c = [p for p in productos_abc if p["categoria"] == "C"]
        
        def calcular_resumen_clase(clase: str, productos_clase: List[Dict]) -> Dict:
            ventas = sum(p["total_venta"] for p in productos_clase)
            cantidad = sum(p["cantidad"] for p in productos_clase)
            margen = sum(p["margen"] or 0 for p in productos_clase)
            margenes_validos = [p["margen_porcentaje"] for p in productos_clase if p["margen_porcentaje"] is not None]
            margen_promedio = sum(margenes_validos) / len(margenes_validos) if margenes_validos else None
            
            return {
                "categoria": clase,
                "productos": len(productos_clase),
                "total_ventas": round(ventas, 2),
                "total_cantidad": cantidad,
                "total_margen": round(margen, 2) if margen else None,
                "margen_promedio": round(margen_promedio, 1) if margen_promedio else None,
                "porcentaje_productos": round(len(productos_clase) / len(productos_abc) * 100, 1) if productos_abc else 0,
                "porcentaje_ventas": round(ventas / total_ventas * 100, 1) if total_ventas > 0 else 0,
                "porcentaje_margen": round(margen / total_margen * 100, 1) if total_margen > 0 else None,
            }
        
        resumen = [
            calcular_resumen_clase("A", clase_a),
            calcular_resumen_clase("B", clase_b),
            calcular_resumen_clase("C", clase_c),
        ]
        
        # Generar insights
        insights = self._generar_insights(resumen, productos_abc)
        
        return {
            "productos": productos_abc,
            "resumen": resumen,
            "insights": insights,
            "criterio_usado": criterio,
            "totales": {
                "productos": len(productos_abc),
                "ventas": round(total_ventas, 2),
                "margen": round(total_margen, 2) if total_margen else None,
            }
        }
    
    async def get_cambios_categoria(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Compara categorías ABC con período anterior."""
        # Obtener análisis actual
        actual = await self.get_analisis_abc(filters)
        
        # Crear período anterior (desplazar fechas)
        from datetime import timedelta
        filters_anterior = FilterParams(
            fecha_inicio=filters.fecha_inicio - timedelta(days=30) if filters.fecha_inicio else None,
            fecha_fin=filters.fecha_fin - timedelta(days=30) if filters.fecha_fin else None,
        )
        
        anterior = await self.get_analisis_abc(filters_anterior)
        
        # Mapear categorías anteriores
        categorias_anteriores = {p["nombre"]: p["categoria"] for p in anterior.get("productos", [])}
        
        cambios = []
        for producto in actual.get("productos", []):
            nombre = producto["nombre"]
            cat_actual = producto["categoria"]
            cat_anterior = categorias_anteriores.get(nombre)
            
            if cat_anterior and cat_anterior != cat_actual:
                # Determinar dirección del cambio
                orden = {"A": 1, "B": 2, "C": 3}
                mejora = orden.get(cat_actual, 0) < orden.get(cat_anterior, 0)
                
                cambios.append({
                    "nombre": nombre,
                    "categoria_anterior": cat_anterior,
                    "categoria_actual": cat_actual,
                    "mejora": mejora,
                    "icono": "⬆️" if mejora else "⬇️",
                    "total_venta": producto["total_venta"],
                })
        
        # Ordenar: primero mejoras, luego declives
        cambios.sort(key=lambda x: (not x["mejora"], -x["total_venta"]))
        
        return cambios
    
    def _generar_insights(self, resumen: List[Dict], productos: List[Dict]) -> List[Dict[str, Any]]:
        """Genera insights accionables basados en el análisis ABC."""
        insights = []
        
        clase_a = next((r for r in resumen if r["categoria"] == "A"), None)
        clase_b = next((r for r in resumen if r["categoria"] == "B"), None)
        clase_c = next((r for r in resumen if r["categoria"] == "C"), None)
        
        # Insight 1: Productos A (foco principal)
        if clase_a:
            insights.append({
                "tipo": "success",
                "icono": "⭐",
                "titulo": f"{clase_a['productos']} productos generan el {clase_a['porcentaje_ventas']}% de tus ventas",
                "descripcion": "Prioriza stock y visibilidad de estos productos. Son tu core de negocio.",
                "accion": "Ver productos A",
                "categoria": "A",
            })
        
        # Insight 2: Oportunidad en B
        if clase_b and clase_b['productos'] > 0:
            # Encontrar los mejores candidatos de B (cerca del límite A)
            productos_b = [p for p in productos if p["categoria"] == "B"]
            top_b = productos_b[:3] if productos_b else []
            nombres_top = ", ".join([p["nombre"][:20] for p in top_b])
            
            insights.append({
                "tipo": "info",
                "icono": "📈",
                "titulo": f"{clase_b['productos']} productos podrían subir a Categoría A",
                "descripcion": f"Candidatos: {nombres_top}. Considera promociones o mejor ubicación.",
                "accion": "Ver productos B",
                "categoria": "B",
            })
        
        # Insight 3: Optimización de C
        if clase_c and clase_c['productos'] > 0:
            # Productos C representan poco pero ocupan inventario
            porcentaje_productos = clase_c['porcentaje_productos']
            insights.append({
                "tipo": "warning",
                "icono": "📦",
                "titulo": f"{clase_c['productos']} productos ({porcentaje_productos}%) generan solo {clase_c['porcentaje_ventas']}% de ventas",
                "descripcion": "Evalúa reducir inventario, descuentos para liquidar, o descontinuar productos de bajo margen.",
                "accion": "Ver productos C",
                "categoria": "C",
            })
        
        # Insight 4: Margen por categoría (si hay datos)
        if clase_a and clase_a.get('margen_promedio') is not None:
            mejor_margen = max(resumen, key=lambda x: x.get('margen_promedio') or 0)
            if mejor_margen.get('margen_promedio'):
                insights.append({
                    "tipo": "info",
                    "icono": "💰",
                    "titulo": f"Categoría {mejor_margen['categoria']} tiene el mejor margen ({mejor_margen['margen_promedio']}%)",
                    "descripcion": "Considera estrategias diferenciadas de pricing por categoría.",
                    "accion": None,
                    "categoria": None,
                })
        
        return insights
    
    def _empty_response(self) -> Dict[str, Any]:
        """Respuesta vacía cuando no hay datos."""
        return {
            "productos": [],
            "resumen": [
                {"categoria": "A", "productos": 0, "total_ventas": 0, "porcentaje_ventas": 0},
                {"categoria": "B", "productos": 0, "total_ventas": 0, "porcentaje_ventas": 0},
                {"categoria": "C", "productos": 0, "total_ventas": 0, "porcentaje_ventas": 0},
            ],
            "insights": [],
            "criterio_usado": "ventas",
            "totales": {"productos": 0, "ventas": 0, "margen": 0},
        }

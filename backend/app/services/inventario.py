"""
Servicio de inventario - Gestión y análisis de stock.
"""
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import FilterParams
from app.services.ventas import VentasService
from app.services.abc import ABCService
from app.services.compras import ComprasService


@dataclass
class ProductoInventario:
    """Modelo de producto con datos de inventario."""
    nombre: str
    familia: Optional[str]
    proveedor: Optional[str]
    stock_actual: int
    stock_minimo: int
    stock_maximo: int
    precio_venta: float
    precio_compra: Optional[float]
    venta_diaria: float
    dias_cobertura: float
    rotacion: Optional[float]
    estado_stock: str  # Crítico, Bajo, Normal, Exceso
    valor_inventario: float
    margen_porcentaje: Optional[float]


class InventarioService:
    """Servicio para gestión de inventario."""
    
    # Configuración de niveles de stock
    DIAS_STOCK_MINIMO = 7  # Días mínimos de cobertura
    DIAS_STOCK_OBJETIVO = 30  # Días objetivo de stock
    DIAS_STOCK_MAXIMO = 60  # Días máximo antes de considerarlo exceso
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_inventario_completo(self) -> List[Dict[str, Any]]:
        """Obtiene inventario con todas las métricas calculadas."""
        
        # Query para obtener stock actual y ventas de los últimos 30 días
        query = """
            WITH ventas_30d AS (
                SELECT 
                    nombre,
                    SUM(cantidad) as cantidad_vendida,
                    SUM(precio * cantidad) as total_ventas,
                    AVG(precio) as precio_promedio_venta,
                    AVG(precio_promedio_compra) as precio_promedio_compra,
                    MAX(proveedor_moda) as proveedor,
                    MAX(familia) as familia
                FROM reportes_ventas_30dias
                GROUP BY nombre
            ),
            inventario AS (
                SELECT 
                    nombre,
                    cantidad_disponible,
                    precio
                FROM items
            )
            SELECT 
                COALESCE(i.nombre, v.nombre) as nombre,
                COALESCE(i.cantidad_disponible, 0) as stock_actual,
                COALESCE(v.cantidad_vendida, 0) as cantidad_vendida_30d,
                COALESCE(v.total_ventas, 0) as total_ventas_30d,
                COALESCE(v.precio_promedio_venta, i.precio) as precio_venta,
                v.precio_promedio_compra as precio_compra,
                v.proveedor,
                v.familia
            FROM inventario i
            FULL OUTER JOIN ventas_30d v ON i.nombre = v.nombre
            WHERE COALESCE(i.cantidad_disponible, 0) > 0 
               OR COALESCE(v.cantidad_vendida, 0) > 0
            ORDER BY COALESCE(v.cantidad_vendida, 0) DESC
        """
        
        result = await self.db.execute(text(query))
        rows = result.fetchall()
        
        productos = []
        for row in rows:
            row_dict = row._asdict()
            
            stock_actual = int(row_dict["stock_actual"] or 0)
            cantidad_vendida = int(row_dict["cantidad_vendida_30d"] or 0)
            precio_venta = float(row_dict["precio_venta"] or 0)
            precio_compra = float(row_dict["precio_compra"]) if row_dict["precio_compra"] else None
            
            # Calcular métricas
            venta_diaria = cantidad_vendida / 30 if cantidad_vendida > 0 else 0
            dias_cobertura = stock_actual / venta_diaria if venta_diaria > 0 else 999
            
            # Rotación anual = (Ventas anualizadas) / Stock promedio
            ventas_anualizadas = cantidad_vendida * 12
            rotacion = ventas_anualizadas / stock_actual if stock_actual > 0 else None
            
            # Estado del stock
            if dias_cobertura <= 3:
                estado_stock = "🔴 Crítico"
            elif dias_cobertura <= self.DIAS_STOCK_MINIMO:
                estado_stock = "🟠 Bajo"
            elif dias_cobertura <= self.DIAS_STOCK_MAXIMO:
                estado_stock = "🟢 Normal"
            else:
                estado_stock = "🔵 Exceso"
            
            # Stock mínimo y máximo calculados
            stock_minimo = int(venta_diaria * self.DIAS_STOCK_MINIMO)
            stock_maximo = int(venta_diaria * self.DIAS_STOCK_MAXIMO)
            
            # Valor del inventario
            valor_inventario = stock_actual * (precio_compra or precio_venta)
            
            # Margen
            margen_porcentaje = None
            if precio_compra and precio_venta > 0:
                margen_porcentaje = ((precio_venta - precio_compra) / precio_venta) * 100
            
            productos.append({
                "nombre": row_dict["nombre"],
                "familia": row_dict["familia"],
                "proveedor": row_dict["proveedor"],
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "stock_maximo": stock_maximo,
                "precio_venta": round(precio_venta, 2),
                "precio_compra": round(precio_compra, 2) if precio_compra else None,
                "venta_diaria": round(venta_diaria, 2),
                "dias_cobertura": round(dias_cobertura, 1) if dias_cobertura < 999 else None,
                "rotacion": round(rotacion, 1) if rotacion else None,
                "estado_stock": estado_stock,
                "valor_inventario": round(valor_inventario, 2),
                "margen_porcentaje": round(margen_porcentaje, 1) if margen_porcentaje else None,
                "cantidad_vendida_30d": cantidad_vendida,
            })
        
        return productos
    
    async def get_resumen_inventario(self) -> Dict[str, Any]:
        """Obtiene resumen ejecutivo del inventario."""
        productos = await self.get_inventario_completo()
        
        if not productos:
            return {
                "total_productos": 0,
                "total_unidades": 0,
                "valor_total": 0,
                "productos_criticos": 0,
                "productos_bajos": 0,
                "productos_normales": 0,
                "productos_exceso": 0,
                "rotacion_promedio": 0,
            }
        
        total_unidades = sum(p["stock_actual"] for p in productos)
        valor_total = sum(p["valor_inventario"] for p in productos)
        
        criticos = [p for p in productos if p["estado_stock"] == "🔴 Crítico"]
        bajos = [p for p in productos if p["estado_stock"] == "🟠 Bajo"]
        normales = [p for p in productos if p["estado_stock"] == "🟢 Normal"]
        exceso = [p for p in productos if p["estado_stock"] == "🔵 Exceso"]
        
        rotaciones = [p["rotacion"] for p in productos if p["rotacion"] is not None]
        rotacion_promedio = sum(rotaciones) / len(rotaciones) if rotaciones else 0
        
        return {
            "total_productos": len(productos),
            "total_unidades": total_unidades,
            "valor_total": round(valor_total, 2),
            "productos_criticos": len(criticos),
            "productos_bajos": len(bajos),
            "productos_normales": len(normales),
            "productos_exceso": len(exceso),
            "rotacion_promedio": round(rotacion_promedio, 1),
            "valor_criticos": round(sum(p["valor_inventario"] for p in criticos), 2),
            "valor_exceso": round(sum(p["valor_inventario"] for p in exceso), 2),
        }
    
    async def get_alertas_inventario(self) -> List[Dict[str, Any]]:
        """Obtiene alertas de inventario priorizadas."""
        productos = await self.get_inventario_completo()
        alertas = []
        
        # Productos críticos (< 3 días)
        criticos = [p for p in productos if p["estado_stock"] == "🔴 Crítico"]
        if criticos:
            alertas.append({
                "tipo": "error",
                "icono": "🚨",
                "titulo": f"{len(criticos)} productos con stock crítico",
                "detalle": "Menos de 3 días de cobertura. ¡Compra urgente requerida!",
                "datos": sorted(criticos, key=lambda x: x.get("dias_cobertura") or 999)[:10],
            })
        
        # Productos con stock bajo (< 7 días)
        bajos = [p for p in productos if p["estado_stock"] == "🟠 Bajo"]
        if bajos:
            alertas.append({
                "tipo": "warning",
                "icono": "⚠️",
                "titulo": f"{len(bajos)} productos con stock bajo",
                "detalle": "Menos de 7 días de cobertura. Planificar compra.",
                "datos": sorted(bajos, key=lambda x: x.get("dias_cobertura") or 999)[:10],
            })
        
        # Productos con exceso de stock
        exceso = [p for p in productos if p["estado_stock"] == "🔵 Exceso"]
        if exceso:
            valor_exceso = sum(p["valor_inventario"] for p in exceso)
            alertas.append({
                "tipo": "info",
                "icono": "📦",
                "titulo": f"{len(exceso)} productos con exceso de stock",
                "detalle": f"Capital inmovilizado: ${valor_exceso:,.0f}",
                "datos": sorted(exceso, key=lambda x: x["valor_inventario"], reverse=True)[:10],
            })
        
        # Productos sin movimiento (ventas = 0 pero hay stock)
        sin_movimiento = [p for p in productos if p["cantidad_vendida_30d"] == 0 and p["stock_actual"] > 0]
        if sin_movimiento:
            valor_muerto = sum(p["valor_inventario"] for p in sin_movimiento)
            alertas.append({
                "tipo": "warning",
                "icono": "💤",
                "titulo": f"{len(sin_movimiento)} productos sin movimiento",
                "detalle": f"Sin ventas en 30 días. Inventario muerto: ${valor_muerto:,.0f}",
                "datos": sorted(sin_movimiento, key=lambda x: x["valor_inventario"], reverse=True)[:10],
            })
        
        return alertas
    
    async def get_producto_detalle(self, nombre: str) -> Optional[Dict[str, Any]]:
        """Obtiene detalle completo de un producto."""
        
        # Datos básicos del producto
        producto_query = """
            SELECT 
                nombre,
                cantidad_disponible as stock_actual,
                precio as precio_venta,
                familia
            FROM items
            WHERE nombre = :nombre
        """
        
        result = await self.db.execute(text(producto_query), {"nombre": nombre})
        producto_row = result.fetchone()
        
        if not producto_row:
            return None
        
        producto = producto_row._asdict()
        
        # Historial de ventas (últimos 90 días) con proveedor
        ventas_query = """
            SELECT 
                fecha_venta,
                SUM(cantidad) as cantidad,
                SUM(precio * cantidad) as total_venta,
                AVG(precio) as precio_promedio,
                AVG(precio_promedio_compra) as costo_promedio,
                STRING_AGG(DISTINCT vendedor, ', ') as vendedores,
                MAX(proveedor_moda) as proveedor
            FROM reportes_ventas_30dias
            WHERE nombre = :nombre
            GROUP BY fecha_venta
            ORDER BY fecha_venta DESC
        """
        
        result = await self.db.execute(text(ventas_query), {"nombre": nombre})
        ventas = [dict(row._asdict()) for row in result.fetchall()]

        # Proveedor principal (el mas frecuente en ventas)
        proveedor = ventas[0].get("proveedor") if ventas else None

        hoy = date.today()
        filtros = FilterParams(fecha_inicio=hoy - timedelta(days=30), fecha_fin=hoy)

        # Clasificacion ABC (usando ultimos 30 dias)
        clasificacion_abc = None
        try:
            ventas_svc = VentasService(self.db)
            abc_svc = ABCService(ventas_svc)
            abc_result = await abc_svc.get_analisis_abc(filtros)
            for p in abc_result.get("productos", []):
                if p.get("nombre") == nombre:
                    clasificacion_abc = p.get("categoria")
                    break
        except Exception:
            pass

        # Calcular métricas
        total_vendido = sum(v["cantidad"] for v in ventas)
        total_ingresos = sum(float(v["total_venta"] or 0) for v in ventas)
        venta_diaria = total_vendido / 30 if ventas else 0
        stock_actual = int(producto.get("stock_actual") or 0)
        dias_cobertura = stock_actual / venta_diaria if venta_diaria > 0 else None
        
        # Precio de compra promedio
        precios_compra = [float(v["costo_promedio"]) for v in ventas if v.get("costo_promedio")]
        precio_compra_prom = sum(precios_compra) / len(precios_compra) if precios_compra else None
        
        # Calcular tendencia (comparar últimas 2 semanas vs 2 semanas anteriores)
        if len(ventas) >= 14:
            ultimas_2_sem = sum(v["cantidad"] for v in ventas[:14])
            prev_2_sem = sum(v["cantidad"] for v in ventas[14:28]) if len(ventas) >= 28 else ultimas_2_sem
            tendencia = ((ultimas_2_sem - prev_2_sem) / prev_2_sem * 100) if prev_2_sem > 0 else 0
        else:
            tendencia = 0

        # Fill rate estimado: dias con stock probable / 30. Proxy = min(1, dias_cobertura/30)
        fill_rate_estimado = None
        if venta_diaria and venta_diaria > 0 and stock_actual is not None:
            dias_cob = stock_actual / venta_diaria if venta_diaria else 0
            fill_rate_estimado = round(min(1.0, dias_cob / 30) * 100, 1) if dias_cob else 0

        # Sugerencia de compra si aplica
        sugerencia_compra = None
        try:
            ventas_svc = VentasService(self.db)
            compras_svc = ComprasService(self.db, ventas_svc)
            sugerencias = await compras_svc.get_sugerencias(filtros)
            for s in sugerencias:
                if s.nombre == nombre:
                    sugerencia_compra = {
                        "cantidad_sugerida": s.cantidad_sugerida,
                        "costo_estimado": s.costo_estimado,
                        "prioridad": s.prioridad,
                        "dias_stock": s.dias_stock,
                    }
                    break
        except Exception:
            pass
        
        return {
            "nombre": nombre,
            "familia": producto.get("familia"),
            "proveedor": proveedor,
            "clasificacion_abc": clasificacion_abc,
            "fill_rate_estimado": fill_rate_estimado,
            "stock_actual": stock_actual,
            "precio_venta": float(producto.get("precio_venta") or 0),
            "precio_compra_promedio": round(precio_compra_prom, 2) if precio_compra_prom else None,
            "venta_diaria": round(venta_diaria, 2),
            "dias_cobertura": round(dias_cobertura, 1) if dias_cobertura else None,
            "total_vendido_30d": total_vendido,
            "total_ingresos_30d": round(total_ingresos, 2),
            "margen_porcentaje": round(
                ((float(producto.get("precio_venta") or 0) - precio_compra_prom) / float(producto.get("precio_venta") or 1)) * 100, 1
            ) if precio_compra_prom else None,
            "tendencia": round(tendencia, 1),
            "tendencia_label": "📈 Creciendo" if tendencia > 5 else ("📉 Decreciendo" if tendencia < -5 else "➡️ Estable"),
            "historial_ventas": ventas[:30],
            "sugerencia_compra": sugerencia_compra,
        }
    
    async def get_valor_por_familia(self) -> List[Dict[str, Any]]:
        """Obtiene valor del inventario agrupado por familia."""
        productos = await self.get_inventario_completo()
        
        familias = {}
        for p in productos:
            familia = p["familia"] or "Sin familia"
            if familia not in familias:
                familias[familia] = {
                    "familia": familia,
                    "productos": 0,
                    "unidades": 0,
                    "valor": 0,
                    "criticos": 0,
                    "bajos": 0,
                }
            familias[familia]["productos"] += 1
            familias[familia]["unidades"] += p["stock_actual"]
            familias[familia]["valor"] += p["valor_inventario"]
            if p["estado_stock"] == "🔴 Crítico":
                familias[familia]["criticos"] += 1
            elif p["estado_stock"] == "🟠 Bajo":
                familias[familia]["bajos"] += 1
        
        return sorted(familias.values(), key=lambda x: x["valor"], reverse=True)
    
    async def get_valor_por_proveedor(self) -> List[Dict[str, Any]]:
        """Obtiene valor del inventario agrupado por proveedor."""
        productos = await self.get_inventario_completo()
        
        proveedores = {}
        for p in productos:
            prov = p["proveedor"] or "Sin proveedor"
            if prov not in proveedores:
                proveedores[prov] = {
                    "proveedor": prov,
                    "productos": 0,
                    "unidades": 0,
                    "valor": 0,
                    "criticos": 0,
                }
            proveedores[prov]["productos"] += 1
            proveedores[prov]["unidades"] += p["stock_actual"]
            proveedores[prov]["valor"] += p["valor_inventario"]
            if p["estado_stock"] == "🔴 Crítico":
                proveedores[prov]["criticos"] += 1
        
        return sorted(proveedores.values(), key=lambda x: x["valor"], reverse=True)
    
    async def get_productos_agotados(self) -> Dict[str, Any]:
        """Obtiene productos que se agotaron en la última semana y últimas 2 semanas."""
        
        # Productos con stock 0 que tuvieron ventas recientes
        query = """
            WITH ventas_recientes AS (
                SELECT 
                    nombre,
                    proveedor_moda as proveedor,
                    familia,
                    SUM(cantidad) as cantidad_vendida,
                    SUM(precio * cantidad) as ingresos,
                    MAX(fecha_venta) as ultima_venta,
                    AVG(precio) as precio_promedio,
                    AVG(precio_promedio_compra) as costo_promedio,
                    SUM(cantidad) / 30.0 as venta_diaria
                FROM reportes_ventas_30dias
                GROUP BY nombre, proveedor_moda, familia
            ),
            stock_actual AS (
                SELECT 
                    nombre,
                    cantidad_disponible as stock
                FROM items
            )
            SELECT 
                v.nombre,
                v.proveedor,
                v.familia,
                COALESCE(s.stock, 0) as stock_actual,
                v.cantidad_vendida,
                v.ingresos,
                v.ultima_venta,
                v.precio_promedio,
                v.costo_promedio,
                v.venta_diaria,
                -- Si se vendió en última semana pero stock = 0, se agotó recientemente
                CASE 
                    WHEN v.ultima_venta >= CURRENT_DATE - INTERVAL '7 days' THEN 'ultima_semana'
                    WHEN v.ultima_venta >= CURRENT_DATE - INTERVAL '14 days' THEN 'ultimas_2_semanas'
                    ELSE 'mas_antiguo'
                END as periodo_agotamiento
            FROM ventas_recientes v
            LEFT JOIN stock_actual s ON v.nombre = s.nombre
            WHERE COALESCE(s.stock, 0) <= 0
                AND v.cantidad_vendida > 0
            ORDER BY v.ultima_venta DESC
        """
        
        result = await self.db.execute(text(query))
        rows = result.fetchall()
        
        agotados_semana = []
        agotados_2_semanas = []
        
        for row in rows:
            row_dict = row._asdict()
            producto = {
                "nombre": row_dict["nombre"],
                "proveedor": row_dict["proveedor"],
                "familia": row_dict["familia"],
                "stock_actual": row_dict["stock_actual"],
                "cantidad_vendida_30d": row_dict["cantidad_vendida"],
                "ingresos_perdidos": float(row_dict["ingresos"] or 0),
                "ultima_venta": str(row_dict["ultima_venta"]) if row_dict["ultima_venta"] else None,
                "precio_promedio": float(row_dict["precio_promedio"] or 0),
                "costo_promedio": float(row_dict["costo_promedio"]) if row_dict["costo_promedio"] else None,
                "venta_diaria": round(float(row_dict["venta_diaria"] or 0), 2),
                "cantidad_sugerida": max(1, int(float(row_dict["venta_diaria"] or 0) * 15)),  # 15 días de stock
            }
            
            if row_dict["periodo_agotamiento"] == "ultima_semana":
                agotados_semana.append(producto)
            elif row_dict["periodo_agotamiento"] == "ultimas_2_semanas":
                agotados_2_semanas.append(producto)
        
        # Calcular ingresos perdidos potenciales
        ingresos_perdidos_semana = sum(p["venta_diaria"] * p["precio_promedio"] * 7 for p in agotados_semana)
        ingresos_perdidos_2_semanas = sum(p["venta_diaria"] * p["precio_promedio"] * 14 for p in agotados_2_semanas)
        
        return {
            "ultima_semana": {
                "productos": agotados_semana[:50],  # Limitar a top 50
                "total": len(agotados_semana),
                "ingresos_perdidos_estimados": round(ingresos_perdidos_semana, 2),
            },
            "ultimas_2_semanas": {
                "productos": agotados_2_semanas[:50],
                "total": len(agotados_2_semanas),
                "ingresos_perdidos_estimados": round(ingresos_perdidos_2_semanas, 2),
            },
            "resumen": {
                "total_agotados": len(agotados_semana) + len(agotados_2_semanas),
                "ingresos_totales_perdidos": round(ingresos_perdidos_semana + ingresos_perdidos_2_semanas, 2),
            }
        }

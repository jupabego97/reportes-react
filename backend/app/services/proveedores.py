"""
Servicio de análisis de proveedores mejorado.
Incluye: stock crítico, score, sugerencias de compra, comparativa de precios.
"""
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import FilterParams


# Constantes para cálculo de stock
DIAS_STOCK_MINIMO = 5
DIAS_STOCK_OBJETIVO = 15
DIAS_STOCK_MAXIMO = 45


class ProveedoresService:
    """Servicio para análisis de proveedores mejorado."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_lista_proveedores(self) -> List[str]:
        """Obtiene lista de todos los proveedores."""
        query = """
            SELECT DISTINCT proveedor_moda 
            FROM reportes_ventas_30dias 
            WHERE proveedor_moda IS NOT NULL 
            ORDER BY proveedor_moda
        """
        result = await self.db.execute(text(query))
        return [row[0] for row in result.fetchall()]
    
    async def get_resumen_proveedores(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Obtiene resumen de todos los proveedores CON alertas de stock."""
        where = "WHERE proveedor_moda IS NOT NULL"
        params = {}
        
        if filters.fecha_inicio:
            where += " AND fecha_venta >= :fecha_inicio"
            params["fecha_inicio"] = filters.fecha_inicio
        
        if filters.fecha_fin:
            where += " AND fecha_venta <= :fecha_fin"
            params["fecha_fin"] = filters.fecha_fin
        
        query = f"""
            SELECT 
                proveedor_moda as proveedor,
                COUNT(*) as total_transacciones,
                COUNT(DISTINCT nombre) as productos_unicos,
                SUM(cantidad) as unidades_vendidas,
                SUM(precio * cantidad) as total_ventas,
                AVG(precio) as precio_promedio,
                AVG(precio_promedio_compra) as costo_promedio,
                SUM(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN (precio - precio_promedio_compra) * cantidad 
                    ELSE 0 END) as margen_total,
                AVG(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN ((precio - precio_promedio_compra) / NULLIF(precio, 0)) * 100 
                    ELSE NULL END) as margen_porcentaje_promedio
            FROM reportes_ventas_30dias
            {where}
            GROUP BY proveedor_moda
            ORDER BY total_ventas DESC
        """
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        proveedores = []
        for row in rows:
            row_dict = row._asdict()
            proveedor_name = row_dict["proveedor"]
            
            # Obtener alertas de stock para este proveedor
            alertas = await self._get_alertas_stock_proveedor(proveedor_name)
            
            proveedores.append({
                "proveedor": proveedor_name,
                "total_transacciones": row_dict["total_transacciones"] or 0,
                "productos_unicos": row_dict["productos_unicos"] or 0,
                "unidades_vendidas": row_dict["unidades_vendidas"] or 0,
                "total_ventas": float(row_dict["total_ventas"] or 0),
                "precio_promedio": float(row_dict["precio_promedio"] or 0),
                "costo_promedio": float(row_dict["costo_promedio"] or 0) if row_dict["costo_promedio"] else None,
                "margen_total": float(row_dict["margen_total"] or 0),
                "margen_porcentaje_promedio": float(row_dict["margen_porcentaje_promedio"] or 0) if row_dict["margen_porcentaje_promedio"] else None,
                # Nuevas métricas de alertas
                "productos_criticos": alertas["criticos"],
                "productos_bajos": alertas["bajos"],
                "tiene_alertas": alertas["criticos"] > 0 or alertas["bajos"] > 0,
            })
        
        return proveedores
    
    async def _get_alertas_stock_proveedor(self, proveedor: str) -> Dict[str, int]:
        """Obtiene conteo de alertas de stock REAL para un proveedor."""
        from app.services.inventario import InventarioService
        
        try:
            inventario_service = InventarioService(self.db)
            productos = await inventario_service.get_inventario_completo()
            
            # Filtrar por proveedor
            productos_proveedor = [p for p in productos if p.get("proveedor") == proveedor]
            
            criticos = len([p for p in productos_proveedor if p["estado_stock"] == "🔴 Crítico"])
            bajos = len([p for p in productos_proveedor if p["estado_stock"] == "🟠 Bajo"])
            
            return {"criticos": criticos, "bajos": bajos}
        except Exception:
            return {"criticos": 0, "bajos": 0}
    
    async def get_stock_proveedor(self, proveedor: str) -> List[Dict[str, Any]]:
        """Obtiene estado de stock REAL de todos los productos de un proveedor."""
        from app.services.inventario import InventarioService
        
        inventario_service = InventarioService(self.db)
        productos = await inventario_service.get_inventario_completo()
        
        # Filtrar por proveedor
        productos_proveedor = [p for p in productos if p.get("proveedor") == proveedor]
        
        # Ordenar: primero críticos, luego bajos, luego por venta
        def sort_key(p):
            if p["estado_stock"] == "🔴 Crítico":
                return (0, -p.get("venta_diaria", 0))
            elif p["estado_stock"] == "🟠 Bajo":
                return (1, -p.get("venta_diaria", 0))
            elif p["estado_stock"] == "🟢 Normal":
                return (2, -p.get("venta_diaria", 0))
            else:
                return (3, -p.get("venta_diaria", 0))
        
        productos_proveedor.sort(key=sort_key)
        
        # Calcular cantidad sugerida a comprar
        resultado = []
        for p in productos_proveedor:
            venta_diaria = p.get("venta_diaria", 0)
            stock_actual = p.get("stock_actual", 0)
            dias_cobertura = p.get("dias_cobertura")
            
            # Sugerir compra si días de cobertura < 15
            if dias_cobertura is not None and dias_cobertura < DIAS_STOCK_OBJETIVO:
                cantidad_sugerida = max(0, int(venta_diaria * DIAS_STOCK_OBJETIVO) - stock_actual)
            else:
                cantidad_sugerida = 0
            
            resultado.append({
                "nombre": p["nombre"],
                "familia": p.get("familia"),
                "stock_actual": stock_actual,
                "precio_venta": p.get("precio_venta", 0),
                "precio_compra": p.get("precio_compra"),
                "cantidad_vendida_30d": p.get("cantidad_vendida_30d", 0),
                "venta_diaria": venta_diaria,
                "dias_cobertura": dias_cobertura,
                "estado": p["estado_stock"],
                "cantidad_sugerida": cantidad_sugerida,
                "valor_inventario": p.get("valor_inventario", 0),
            })
        
        return resultado

    async def get_sugerencias_compra_proveedor(self, proveedor: str) -> Dict[str, Any]:
        """Genera lista de compras sugerida para un proveedor con datos REALES."""
        productos = await self.get_stock_proveedor(proveedor)
        
        # Filtrar solo productos que necesitan reabastecimiento (crítico o bajo)
        productos_a_comprar = [
            p for p in productos 
            if p["estado"] in ["🔴 Crítico", "🟠 Bajo"] or p["cantidad_sugerida"] > 0
        ]
        
        # Calcular totales
        total_unidades = sum(p["cantidad_sugerida"] for p in productos_a_comprar)
        total_inversion = sum(
            p["cantidad_sugerida"] * (p["precio_compra"] or p["precio_venta"] * 0.7)
            for p in productos_a_comprar
        )
        
        return {
            "proveedor": proveedor,
            "fecha_generacion": str(date.today()),
            "productos": productos_a_comprar,
            "resumen": {
                "total_productos": len(productos_a_comprar),
                "total_unidades": total_unidades,
                "inversion_estimada": round(total_inversion, 2),
            }
        }

    
    async def get_score_proveedor(self, proveedor: str, filters: FilterParams) -> Dict[str, Any]:
        """Calcula score de 0-100 para un proveedor."""
        # Obtener métricas del proveedor
        detalle = await self.get_detalle_proveedor(proveedor, filters)
        productos_stock = await self.get_stock_proveedor(proveedor)
        
        if not detalle.get("metricas"):
            return {"proveedor": proveedor, "score": 0, "desglose": {}}
        
        metricas = detalle["metricas"]
        
        # 1. Score de Margen (30%) - Margen promedio
        margen_prom = metricas.get("margen_porcentaje_promedio") or 0
        score_margen = min(100, max(0, margen_prom * 2.5))  # 40% margen = 100 puntos
        
        # 2. Score de Rotación (25%) - Basado en ventas promedio
        productos_activos = len([p for p in productos_stock if p["venta_diaria"] > 0])
        total_productos = len(productos_stock)
        ratio_rotacion = productos_activos / total_productos if total_productos > 0 else 0
        score_rotacion = ratio_rotacion * 100
        
        # 3. Score de Stock (25%) - Productos sin stockout
        productos_criticos = len([p for p in productos_stock if "Crítico" in p["estado"]])
        productos_bajos = len([p for p in productos_stock if "Bajo" in p["estado"]])
        ratio_stock_sano = 1 - (productos_criticos * 2 + productos_bajos) / max(1, total_productos)
        score_stock = max(0, ratio_stock_sano * 100)
        
        # 4. Score de Consistencia (20%) - Ventas regulares
        ventas_por_dia = detalle.get("ventas_por_dia", [])
        if len(ventas_por_dia) > 1:
            valores = [v["total_venta"] for v in ventas_por_dia]
            promedio = sum(valores) / len(valores)
            varianza = sum((v - promedio) ** 2 for v in valores) / len(valores)
            cv = (varianza ** 0.5) / promedio if promedio > 0 else 1
            score_consistencia = max(0, (1 - cv) * 100)
        else:
            score_consistencia = 50
        
        # Calcular score total ponderado
        score_total = (
            score_margen * 0.30 +
            score_rotacion * 0.25 +
            score_stock * 0.25 +
            score_consistencia * 0.20
        )
        
        # Convertir a estrellas (1-5)
        estrellas = max(1, min(5, round(score_total / 20)))
        
        return {
            "proveedor": proveedor,
            "score": round(score_total, 1),
            "estrellas": estrellas,
            "desglose": {
                "margen": round(score_margen, 1),
                "rotacion": round(score_rotacion, 1),
                "stock": round(score_stock, 1),
                "consistencia": round(score_consistencia, 1),
            },
            "metricas_base": {
                "margen_promedio": round(margen_prom, 1),
                "productos_activos": productos_activos,
                "total_productos": total_productos,
                "productos_criticos": productos_criticos,
            }
        }
    
    async def get_comparativa_precios(self) -> List[Dict[str, Any]]:
        """Compara precios del mismo producto entre diferentes proveedores."""
        query = """
            WITH productos_multi_proveedor AS (
                SELECT nombre
                FROM reportes_ventas_30dias
                WHERE proveedor_moda IS NOT NULL
                    AND fecha_venta >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY nombre
                HAVING COUNT(DISTINCT proveedor_moda) > 1
            )
            SELECT 
                nombre,
                proveedor_moda as proveedor,
                AVG(precio) as precio_venta,
                AVG(precio_promedio_compra) as precio_compra,
                SUM(cantidad) as cantidad_vendida
            FROM reportes_ventas_30dias
            WHERE nombre IN (SELECT nombre FROM productos_multi_proveedor)
                AND fecha_venta >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY nombre, proveedor_moda
            ORDER BY nombre, AVG(precio_promedio_compra) NULLS LAST
        """
        
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            # Agrupar por producto
            productos = {}
            for row in rows:
                row_dict = row._asdict()
                nombre = row_dict["nombre"]
                
                if nombre not in productos:
                    productos[nombre] = {
                        "nombre": nombre,
                        "proveedores": [],
                        "cantidad_vendida_30d": 0,
                    }
                
                productos[nombre]["cantidad_vendida_30d"] += row_dict["cantidad_vendida"] or 0
                productos[nombre]["proveedores"].append({
                    "proveedor": row_dict["proveedor"],
                    "precio_venta": float(row_dict["precio_venta"] or 0),
                    "precio_compra": float(row_dict["precio_compra"] or 0) if row_dict["precio_compra"] else None,
                    "cantidad_vendida": row_dict["cantidad_vendida"] or 0,
                })
            
            # Identificar mejor opción por producto
            for nombre, data in productos.items():
                proveedores = data["proveedores"]
                # Mejor precio de compra
                provs_con_precio = [p for p in proveedores if p["precio_compra"]]
                if provs_con_precio:
                    mejor = min(provs_con_precio, key=lambda x: x["precio_compra"])
                    mejor["es_mejor_precio"] = True
            
            return list(productos.values())[:30]  # Top 30
        except Exception:
            return []

    
    async def get_tendencia_proveedor(self, proveedor: str) -> Dict[str, Any]:
        """Compara ventas del mes actual vs mes anterior."""
        query = """
            WITH mes_actual AS (
                SELECT SUM(precio * cantidad) as total
                FROM reportes_ventas_30dias
                WHERE proveedor_moda = :proveedor
                    AND fecha_venta >= DATE_TRUNC('month', CURRENT_DATE)
            ),
            mes_anterior AS (
                SELECT SUM(precio * cantidad) as total
                FROM reportes_ventas_30dias
                WHERE proveedor_moda = :proveedor
                    AND fecha_venta >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                    AND fecha_venta < DATE_TRUNC('month', CURRENT_DATE)
            )
            SELECT 
                COALESCE(a.total, 0) as ventas_mes_actual,
                COALESCE(p.total, 0) as ventas_mes_anterior
            FROM mes_actual a, mes_anterior p
        """
        
        try:
            result = await self.db.execute(text(query), {"proveedor": proveedor})
            row = result.fetchone()
            
            if row:
                actual = float(row[0] or 0)
                anterior = float(row[1] or 0)
                
                if anterior > 0:
                    cambio_porcentaje = ((actual - anterior) / anterior) * 100
                else:
                    cambio_porcentaje = 100 if actual > 0 else 0
                
                return {
                    "proveedor": proveedor,
                    "ventas_mes_actual": actual,
                    "ventas_mes_anterior": anterior,
                    "cambio_porcentaje": round(cambio_porcentaje, 1),
                    "tendencia": "creciendo" if cambio_porcentaje > 5 else "decreciendo" if cambio_porcentaje < -5 else "estable",
                    "icono": "📈" if cambio_porcentaje > 5 else "📉" if cambio_porcentaje < -5 else "➡️",
                }
            
            return {"proveedor": proveedor, "tendencia": "sin_datos"}
        except Exception:
            return {"proveedor": proveedor, "tendencia": "sin_datos"}
    
    async def get_detalle_proveedor(self, proveedor: str, filters: FilterParams) -> Dict[str, Any]:
        """Obtiene detalle completo de un proveedor (mejorado)."""
        where = "WHERE proveedor_moda = :proveedor"
        params = {"proveedor": proveedor}
        
        if filters.fecha_inicio:
            where += " AND fecha_venta >= :fecha_inicio"
            params["fecha_inicio"] = filters.fecha_inicio
        
        if filters.fecha_fin:
            where += " AND fecha_venta <= :fecha_fin"
            params["fecha_fin"] = filters.fecha_fin
        
        # Métricas generales
        metricas_query = f"""
            SELECT 
                COUNT(*) as total_transacciones,
                COUNT(DISTINCT nombre) as productos_unicos,
                COUNT(DISTINCT vendedor) as vendedores_activos,
                SUM(cantidad) as unidades_vendidas,
                SUM(precio * cantidad) as total_ventas,
                AVG(precio) as precio_promedio,
                AVG(precio_promedio_compra) as costo_promedio,
                SUM(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN (precio - precio_promedio_compra) * cantidad 
                    ELSE 0 END) as margen_total,
                AVG(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN ((precio - precio_promedio_compra) / NULLIF(precio, 0)) * 100 
                    ELSE NULL END) as margen_porcentaje_promedio,
                MIN(fecha_venta) as primera_venta,
                MAX(fecha_venta) as ultima_venta
            FROM reportes_ventas_30dias
            {where}
        """
        
        result = await self.db.execute(text(metricas_query), params)
        metricas_row = result.fetchone()
        
        if not metricas_row or not metricas_row[0]:
            return {
                "proveedor": proveedor,
                "metricas": {},
                "productos": [],
                "ventas_por_dia": [],
                "ventas_por_familia": [],
                "top_productos": [],
            }
        
        metricas = metricas_row._asdict()
        
        # Productos del proveedor
        productos_query = f"""
            SELECT 
                nombre,
                familia,
                SUM(cantidad) as cantidad_vendida,
                SUM(precio * cantidad) as total_ventas,
                AVG(precio) as precio_promedio,
                AVG(precio_promedio_compra) as costo_promedio,
                AVG(CASE WHEN precio_promedio_compra IS NOT NULL 
                    THEN ((precio - precio_promedio_compra) / NULLIF(precio, 0)) * 100 
                    ELSE NULL END) as margen_porcentaje
            FROM reportes_ventas_30dias
            {where}
            GROUP BY nombre, familia
            ORDER BY total_ventas DESC
        """
        
        result = await self.db.execute(text(productos_query), params)
        productos = [dict(row._asdict()) for row in result.fetchall()]
        
        # Ventas por día
        ventas_dia_query = f"""
            SELECT 
                fecha_venta::date as fecha,
                SUM(cantidad) as cantidad,
                SUM(precio * cantidad) as total_venta
            FROM reportes_ventas_30dias
            {where}
            GROUP BY fecha_venta::date
            ORDER BY fecha_venta::date
        """
        
        result = await self.db.execute(text(ventas_dia_query), params)
        ventas_por_dia = [
            {
                "fecha": str(row[0]),
                "cantidad": row[1],
                "total_venta": float(row[2] or 0)
            }
            for row in result.fetchall()
        ]
        
        # Ventas por familia
        ventas_familia_query = f"""
            SELECT 
                COALESCE(familia, 'Sin familia') as familia,
                SUM(cantidad) as cantidad,
                SUM(precio * cantidad) as total_venta,
                COUNT(DISTINCT nombre) as productos
            FROM reportes_ventas_30dias
            {where}
            GROUP BY familia
            ORDER BY total_venta DESC
        """
        
        result = await self.db.execute(text(ventas_familia_query), params)
        ventas_por_familia = [
            {
                "familia": row[0],
                "cantidad": row[1],
                "total_venta": float(row[2] or 0),
                "productos": row[3]
            }
            for row in result.fetchall()
        ]
        
        # Obtener tendencia
        tendencia = await self.get_tendencia_proveedor(proveedor)
        
        # Obtener alertas de stock
        alertas_stock = await self._get_alertas_stock_proveedor(proveedor)
        
        return {
            "proveedor": proveedor,
            "metricas": {
                "total_transacciones": metricas["total_transacciones"] or 0,
                "productos_unicos": metricas["productos_unicos"] or 0,
                "vendedores_activos": metricas["vendedores_activos"] or 0,
                "unidades_vendidas": metricas["unidades_vendidas"] or 0,
                "total_ventas": float(metricas["total_ventas"] or 0),
                "precio_promedio": float(metricas["precio_promedio"] or 0),
                "costo_promedio": float(metricas["costo_promedio"] or 0) if metricas["costo_promedio"] else None,
                "margen_total": float(metricas["margen_total"] or 0),
                "margen_porcentaje_promedio": float(metricas["margen_porcentaje_promedio"] or 0) if metricas["margen_porcentaje_promedio"] else None,
                "primera_venta": str(metricas["primera_venta"]) if metricas["primera_venta"] else None,
                "ultima_venta": str(metricas["ultima_venta"]) if metricas["ultima_venta"] else None,
            },
            "productos": productos[:50],
            "ventas_por_dia": ventas_por_dia,
            "ventas_por_familia": ventas_por_familia,
            "top_productos": productos[:10],
            "tendencia": tendencia,
            "alertas_stock": alertas_stock,
        }
    
    async def get_comparativa_proveedores(self, proveedores: List[str], filters: FilterParams) -> Dict[str, Any]:
        """Compara múltiples proveedores."""
        if not proveedores:
            return {"proveedores": [], "comparativa": []}
        
        where = "WHERE proveedor_moda = ANY(:proveedores)"
        params = {"proveedores": proveedores}
        
        if filters.fecha_inicio:
            where += " AND fecha_venta >= :fecha_inicio"
            params["fecha_inicio"] = filters.fecha_inicio
        
        if filters.fecha_fin:
            where += " AND fecha_venta <= :fecha_fin"
            params["fecha_fin"] = filters.fecha_fin
        
        query = f"""
            SELECT 
                proveedor_moda as proveedor,
                fecha_venta::date as fecha,
                SUM(precio * cantidad) as total_venta
            FROM reportes_ventas_30dias
            {where}
            GROUP BY proveedor_moda, fecha_venta::date
            ORDER BY fecha_venta::date
        """
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        datos_por_fecha = {}
        for row in rows:
            fecha = str(row[0])
            proveedor = row[1]
            total = float(row[2] or 0)
            
            if fecha not in datos_por_fecha:
                datos_por_fecha[fecha] = {"fecha": fecha}
            datos_por_fecha[fecha][proveedor] = total
        
        comparativa = list(datos_por_fecha.values())
        
        return {
            "proveedores": proveedores,
            "comparativa": comparativa
        }
    
    async def get_ranking_proveedores(self, filters: FilterParams, criterio: str = "ventas") -> List[Dict[str, Any]]:
        """Obtiene ranking de proveedores por diferentes criterios."""
        resumen = await self.get_resumen_proveedores(filters)
        
        if criterio == "ventas":
            return sorted(resumen, key=lambda x: x["total_ventas"], reverse=True)
        elif criterio == "margen":
            return sorted(resumen, key=lambda x: x["margen_total"], reverse=True)
        elif criterio == "unidades":
            return sorted(resumen, key=lambda x: x["unidades_vendidas"], reverse=True)
        elif criterio == "productos":
            return sorted(resumen, key=lambda x: x["productos_unicos"], reverse=True)
        elif criterio == "alertas":
            return sorted(resumen, key=lambda x: (x["productos_criticos"], x["productos_bajos"]), reverse=True)
        else:
            return resumen

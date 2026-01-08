"""
Servicio de sugerencias de compras - Versión mejorada.
Incluye: ROI, órdenes por proveedor, productos agotados, punto de reorden.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    FilterParams,
    SugerenciaCompraResponse,
    ResumenProveedorResponse,
    OrdenCompraResponse,
)
from app.services.ventas import VentasService


class ComprasService:
    """Servicio mejorado para sugerencias de compras."""
    
    def __init__(self, db: AsyncSession, ventas_service: VentasService):
        self.db = db
        self.ventas_service = ventas_service
    
    async def get_inventario(self) -> dict:
        """Obtiene datos de inventario desde la tabla items."""
        query = "SELECT id, nombre, cantidad_disponible, familia, precio FROM items"
        
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            inventario = {}
            for row in rows:
                row_dict = row._asdict()
                nombre = row_dict.get("nombre")
                if nombre:
                    inventario[nombre] = {
                        "cantidad_disponible": float(row_dict.get("cantidad_disponible") or 0),
                        "precio": float(row_dict.get("precio") or 0),
                    }
            
            return inventario
        except Exception:
            return {}
    
    async def get_sugerencias(self, filters: FilterParams) -> List[SugerenciaCompraResponse]:
        """Calcula sugerencias de reposición."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        inventario = await self.get_inventario()
        
        if not ventas:
            return []
        
        # Agrupar ventas por producto
        productos = {}
        for v in ventas:
            if v.nombre not in productos:
                productos[v.nombre] = {
                    "unidades_vendidas": 0,
                    "total_ventas": 0,
                    "precio_compra": v.precio_promedio_compra,
                    "precio_venta": 0,
                    "proveedor": v.proveedor_moda,
                    "familia": v.familia,
                }
            productos[v.nombre]["unidades_vendidas"] += v.cantidad
            productos[v.nombre]["total_ventas"] += v.total_venta
            productos[v.nombre]["precio_venta"] = v.precio  # último precio
        
        sugerencias = []
        
        for nombre, data in productos.items():
            # Venta diaria promedio
            venta_diaria = data["unidades_vendidas"] / 30
            
            # Stock actual
            stock_actual = inventario.get(nombre, {}).get("cantidad_disponible", 0)
            
            # Días de stock
            dias_stock = stock_actual / venta_diaria if venta_diaria > 0 else 999
            
            # Cantidad sugerida (30 días + 20% margen de seguridad)
            cantidad_sugerida = max(0, int((data["unidades_vendidas"] * 1.2) - stock_actual))
            
            if cantidad_sugerida <= 0:
                continue
            
            # Precio de compra
            precio_compra = data["precio_compra"] or inventario.get(nombre, {}).get("precio", 0)
            precio_venta = data["precio_venta"] or precio_compra * 1.3
            
            # Costo estimado
            costo_estimado = cantidad_sugerida * (precio_compra or 0)
            
            # Prioridad
            if dias_stock <= 3:
                prioridad = "🔴 Urgente"
            elif dias_stock <= 7:
                prioridad = "🟠 Alta"
            elif dias_stock <= 15:
                prioridad = "🟡 Media"
            else:
                prioridad = "🟢 Baja"
            
            sugerencias.append(SugerenciaCompraResponse(
                nombre=nombre,
                proveedor=data["proveedor"],
                familia=data["familia"],
                cantidad_disponible=int(stock_actual),
                venta_diaria=round(venta_diaria, 1),
                dias_stock=round(dias_stock, 1),
                cantidad_sugerida=cantidad_sugerida,
                precio_compra=precio_compra,
                costo_estimado=round(costo_estimado, 2),
                prioridad=prioridad,
            ))
        
        # Ordenar por prioridad y días de stock
        prioridad_orden = {"🔴 Urgente": 0, "🟠 Alta": 1, "🟡 Media": 2, "🟢 Baja": 3}
        sugerencias.sort(key=lambda x: (prioridad_orden.get(x.prioridad, 4), x.dias_stock))
        
        return sugerencias
    
    async def get_resumen_completo(self, filters: FilterParams) -> Dict[str, Any]:
        """Obtiene resumen completo con ROI, inversión total y productos agotados."""
        sugerencias = await self.get_sugerencias(filters)
        agotados = await self.get_productos_agotados()
        
        # Calcular totales
        inversion_total = sum(s.costo_estimado for s in sugerencias)
        
        # Calcular ROI esperado (basado en margen promedio 25%)
        margen_promedio = 0.25
        ventas_esperadas = inversion_total * (1 + margen_promedio)
        roi_esperado = (ventas_esperadas - inversion_total) / inversion_total * 100 if inversion_total > 0 else 0
        
        # Agrupar por proveedor
        por_proveedor = {}
        for s in sugerencias:
            prov = s.proveedor or "Sin proveedor"
            if prov not in por_proveedor:
                por_proveedor[prov] = {
                    "proveedor": prov,
                    "productos": 0,
                    "unidades": 0,
                    "inversion": 0,
                    "urgentes": 0,
                    "altas": 0,
                }
            por_proveedor[prov]["productos"] += 1
            por_proveedor[prov]["unidades"] += s.cantidad_sugerida
            por_proveedor[prov]["inversion"] += s.costo_estimado
            if s.prioridad == "🔴 Urgente":
                por_proveedor[prov]["urgentes"] += 1
            elif s.prioridad == "🟠 Alta":
                por_proveedor[prov]["altas"] += 1
        
        # Ordenar proveedores por urgencia
        proveedores_ordenados = sorted(
            por_proveedor.values(),
            key=lambda x: (-(x["urgentes"] * 1000 + x["altas"]), -x["inversion"])
        )
        
        # Contar por prioridad
        urgentes = [s for s in sugerencias if s.prioridad == "🔴 Urgente"]
        altas = [s for s in sugerencias if s.prioridad == "🟠 Alta"]
        medias = [s for s in sugerencias if s.prioridad == "🟡 Media"]
        bajas = [s for s in sugerencias if s.prioridad == "🟢 Baja"]
        
        return {
            "resumen": {
                "total_productos": len(sugerencias),
                "total_unidades": sum(s.cantidad_sugerida for s in sugerencias),
                "inversion_total": round(inversion_total, 2),
                "ventas_esperadas": round(ventas_esperadas, 2),
                "roi_esperado": round(roi_esperado, 1),
                "margen_promedio_usado": margen_promedio * 100,
            },
            "por_prioridad": {
                "urgentes": {"count": len(urgentes), "inversion": round(sum(s.costo_estimado for s in urgentes), 2)},
                "altas": {"count": len(altas), "inversion": round(sum(s.costo_estimado for s in altas), 2)},
                "medias": {"count": len(medias), "inversion": round(sum(s.costo_estimado for s in medias), 2)},
                "bajas": {"count": len(bajas), "inversion": round(sum(s.costo_estimado for s in bajas), 2)},
            },
            "por_proveedor": proveedores_ordenados[:15],  # Top 15
            "agotados": agotados,
            "sugerencias": [s.dict() for s in sugerencias],
        }
    
    async def get_productos_agotados(self) -> Dict[str, Any]:
        """Obtiene productos agotados en última semana y 2 semanas."""
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
                    SUM(cantidad) / 30.0 as venta_diaria
                FROM reportes_ventas_30dias
                GROUP BY nombre, proveedor_moda, familia
            ),
            stock_actual AS (
                SELECT nombre, cantidad_disponible as stock FROM items
            )
            SELECT 
                v.nombre, v.proveedor, v.familia,
                COALESCE(s.stock, 0) as stock_actual,
                v.cantidad_vendida, v.ingresos, v.ultima_venta,
                v.precio_promedio, v.venta_diaria,
                CASE 
                    WHEN v.ultima_venta >= CURRENT_DATE - INTERVAL '7 days' THEN 'semana'
                    WHEN v.ultima_venta >= CURRENT_DATE - INTERVAL '14 days' THEN '2semanas'
                    ELSE 'antiguo'
                END as periodo
            FROM ventas_recientes v
            LEFT JOIN stock_actual s ON v.nombre = s.nombre
            WHERE COALESCE(s.stock, 0) <= 0 AND v.cantidad_vendida > 0
            ORDER BY v.ultima_venta DESC
        """
        
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            semana = []
            dos_semanas = []
            
            for row in rows:
                d = row._asdict()
                producto = {
                    "nombre": d["nombre"],
                    "proveedor": d["proveedor"],
                    "familia": d["familia"],
                    "ultima_venta": str(d["ultima_venta"]) if d["ultima_venta"] else None,
                    "venta_diaria": round(float(d["venta_diaria"] or 0), 2),
                    "cantidad_sugerida": max(1, int(float(d["venta_diaria"] or 0) * 15)),
                    "ventas_perdidas": round(float(d["venta_diaria"] or 0) * float(d["precio_promedio"] or 0) * 7, 2),
                }
                if d["periodo"] == "semana":
                    semana.append(producto)
                elif d["periodo"] == "2semanas":
                    dos_semanas.append(producto)
            
            return {
                "ultima_semana": {
                    "total": len(semana),
                    "productos": semana[:20],
                    "ventas_perdidas": round(sum(p["ventas_perdidas"] for p in semana), 2),
                },
                "ultimas_2_semanas": {
                    "total": len(dos_semanas),
                    "productos": dos_semanas[:20],
                    "ventas_perdidas": round(sum(p["ventas_perdidas"] for p in dos_semanas), 2),
                },
            }
        except Exception:
            return {"ultima_semana": {"total": 0, "productos": []}, "ultimas_2_semanas": {"total": 0, "productos": []}}
    
    async def get_orden_proveedor(self, proveedor: str, filters: FilterParams) -> Dict[str, Any]:
        """Genera orden de compra detallada para un proveedor específico."""
        sugerencias = await self.get_sugerencias(filters)
        
        # Filtrar por proveedor
        items = [s for s in sugerencias if (s.proveedor or "Sin proveedor") == proveedor]
        
        total_unidades = sum(s.cantidad_sugerida for s in items)
        costo_total = sum(s.costo_estimado for s in items)
        
        # Calcular ROI para este proveedor
        margen_promedio = 0.25
        ventas_esperadas = costo_total * (1 + margen_promedio)
        
        return {
            "proveedor": proveedor,
            "fecha_generacion": str(date.today()),
            "total_productos": len(items),
            "total_unidades": total_unidades,
            "inversion_total": round(costo_total, 2),
            "ventas_esperadas": round(ventas_esperadas, 2),
            "ganancia_esperada": round(ventas_esperadas - costo_total, 2),
            "items": [
                {
                    "nombre": s.nombre,
                    "familia": s.familia,
                    "stock_actual": s.cantidad_disponible,
                    "dias_stock": s.dias_stock,
                    "cantidad": s.cantidad_sugerida,
                    "precio_unitario": s.precio_compra,
                    "subtotal": s.costo_estimado,
                    "prioridad": s.prioridad,
                }
                for s in sorted(items, key=lambda x: x.dias_stock)
            ],
        }
    
    async def get_puntos_reorden(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Calcula puntos de reorden para productos con alta rotación."""
        sugerencias = await self.get_sugerencias(filters)
        
        puntos = []
        for s in sugerencias:
            if s.venta_diaria >= 0.5:  # Solo productos con ventas significativas
                # Punto de reorden = venta diaria * lead time (7 días) + stock seguridad (3 días)
                lead_time = 7
                stock_seguridad = 3
                punto_reorden = int(s.venta_diaria * (lead_time + stock_seguridad))
                stock_objetivo = int(s.venta_diaria * 30)  # 30 días de stock
                
                puntos.append({
                    "nombre": s.nombre,
                    "proveedor": s.proveedor,
                    "familia": s.familia,
                    "stock_actual": s.cantidad_disponible,
                    "venta_diaria": s.venta_diaria,
                    "punto_reorden": punto_reorden,
                    "stock_objetivo": stock_objetivo,
                    "estado": "🔴 Por debajo" if s.cantidad_disponible < punto_reorden else "🟢 OK",
                    "cantidad_pedir": max(0, stock_objetivo - s.cantidad_disponible),
                })
        
        # Ordenar por estado (críticos primero)
        puntos.sort(key=lambda x: (0 if x["estado"].startswith("🔴") else 1, -x["venta_diaria"]))
        
        return puntos[:100]  # Top 100
    
    async def get_resumen_proveedores(self, filters: FilterParams) -> List[ResumenProveedorResponse]:
        """Obtiene resumen de compras por proveedor."""
        sugerencias = await self.get_sugerencias(filters)
        
        # Agrupar por proveedor
        proveedores = {}
        for s in sugerencias:
            if s.proveedor:
                if s.proveedor not in proveedores:
                    proveedores[s.proveedor] = {
                        "productos": 0,
                        "unidades": 0,
                        "costo_total": 0,
                    }
                proveedores[s.proveedor]["productos"] += 1
                proveedores[s.proveedor]["unidades"] += s.cantidad_sugerida
                proveedores[s.proveedor]["costo_total"] += s.costo_estimado
        
        return [
            ResumenProveedorResponse(
                proveedor=proveedor,
                productos=data["productos"],
                unidades=data["unidades"],
                costo_total=round(data["costo_total"], 2),
            )
            for proveedor, data in sorted(proveedores.items(), key=lambda x: x[1]["costo_total"], reverse=True)
        ]
    
    async def get_orden_compra(
        self,
        proveedor: str,
        filters: FilterParams,
        prioridad_minima: Optional[str] = None
    ) -> OrdenCompraResponse:
        """Genera orden de compra para un proveedor."""
        sugerencias = await self.get_sugerencias(filters)
        
        # Filtrar por proveedor
        items = [s for s in sugerencias if s.proveedor == proveedor]
        
        # Filtrar por prioridad mínima
        if prioridad_minima:
            prioridades_incluir = {
                "🔴 Urgente": ["🔴 Urgente"],
                "🟠 Alta": ["🔴 Urgente", "🟠 Alta"],
                "🟡 Media": ["🔴 Urgente", "🟠 Alta", "🟡 Media"],
            }
            prioridades = prioridades_incluir.get(prioridad_minima, [])
            if prioridades:
                items = [s for s in items if s.prioridad in prioridades]
        
        total_unidades = sum(s.cantidad_sugerida for s in items)
        costo_total = sum(s.costo_estimado for s in items)
        
        return OrdenCompraResponse(
            proveedor=proveedor,
            fecha=datetime.now(),
            total_productos=len(items),
            total_unidades=total_unidades,
            costo_total=round(costo_total, 2),
            items=items,
        )
    
    async def get_alertas_stock(self, filters: FilterParams) -> dict:
        """Obtiene alertas de stock crítico."""
        sugerencias = await self.get_sugerencias(filters)
        
        urgentes = [s for s in sugerencias if s.prioridad == "🔴 Urgente"]
        altos = [s for s in sugerencias if s.prioridad == "🟠 Alta"]
        medios = [s for s in sugerencias if s.prioridad == "🟡 Media"]
        
        return {
            "urgentes": {
                "count": len(urgentes),
                "costo": round(sum(s.costo_estimado for s in urgentes), 2),
                "items": urgentes[:10],
            },
            "altos": {
                "count": len(altos),
                "costo": round(sum(s.costo_estimado for s in altos), 2),
            },
            "medios": {
                "count": len(medios),
                "costo": round(sum(s.costo_estimado for s in medios), 2),
            },
        }



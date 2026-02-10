"""
Servicio de sugerencias de compras.
"""
from datetime import datetime
from typing import List, Optional, Dict

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    FilterParams,
    SugerenciaCompraResponse,
    ResumenProveedorResponse,
    OrdenCompraResponse,
    ABCResponse,
)
from app.services.ventas import VentasService
from app.services.abc import ABCService


class ComprasService:
    """Servicio para sugerencias de compras."""
    
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
    
    async def _get_clasificacion_abc_por_producto(
        self, filters: FilterParams
    ) -> Dict[str, str]:
        """Obtiene un mapa nombre_producto -> clasificación ABC."""
        abc_service = ABCService(self.ventas_service)
        abc: ABCResponse = await abc_service.get_analisis_abc(filters)
        return {p.nombre: p.clasificacion for p in abc.productos}

    async def get_sugerencias(self, filters: FilterParams) -> List[SugerenciaCompraResponse]:
        """Calcula sugerencias de reposición con inteligencia adicional (ABC, tendencia, ROI)."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        inventario = await self.get_inventario()
        
        if not ventas:
            return []
        
        # Rango real de fechas del periodo
        fechas = [v.fecha_venta for v in ventas]
        fecha_min = min(fechas)
        fecha_max = max(fechas)
        dias_periodo = max((fecha_max - fecha_min).days + 1, 1)
        
        # Agrupar ventas por producto y por día
        productos: Dict[str, dict] = {}
        for v in ventas:
            if v.nombre not in productos:
                productos[v.nombre] = {
                    "unidades_vendidas": 0,
                    "total_ventas": 0.0,
                    "precio_compra": v.precio_promedio_compra,
                    "proveedor": v.proveedor_moda,
                    "familia": v.familia,
                    "por_dia": {},  # fecha -> unidades
                }
            prod = productos[v.nombre]
            prod["unidades_vendidas"] += v.cantidad
            prod["total_ventas"] += float(v.total_venta or 0)
            prod["por_dia"].setdefault(v.fecha_venta, 0)
            prod["por_dia"][v.fecha_venta] += v.cantidad

        # Clasificación ABC por producto
        mapa_abc = await self._get_clasificacion_abc_por_producto(filters)
        
        sugerencias: List[SugerenciaCompraResponse] = []
        
        for nombre, data in productos.items():
            unidades_vendidas = data["unidades_vendidas"]
            if unidades_vendidas <= 0:
                continue

            # Venta diaria promedio basada en rango real
            venta_diaria = unidades_vendidas / dias_periodo
            
            # Serie diaria ordenada para calcular tendencia y variabilidad
            dias_ordenados = sorted(data["por_dia"].keys())
            serie = [data["por_dia"][d] for d in dias_ordenados]
            n = len(serie)

            # Tendencia (primera mitad vs segunda mitad)
            if n >= 2:
                mitad = n // 2
                primera = np.mean(serie[:mitad])
                segunda = np.mean(serie[mitad:])
                if segunda > primera * 1.2:
                    tendencia = "creciente"
                elif segunda < primera * 0.8:
                    tendencia = "decreciente"
                else:
                    tendencia = "estable"
            else:
                tendencia = "estable"

            # Variabilidad (coeficiente de variación)
            if n >= 2:
                arr = np.array(serie, dtype=float)
                media = float(np.mean(arr))
                std = float(np.std(arr))
                variabilidad = round(std / media, 3) if media > 0 else 0.0
            else:
                variabilidad = 0.0

            # Stock actual
            stock_actual = inventario.get(nombre, {}).get("cantidad_disponible", 0)
            
            # Días de stock
            dias_stock = stock_actual / venta_diaria if venta_diaria > 0 else 999

            # Cobertura objetivo según ABC
            clasificacion_abc = mapa_abc.get(nombre) or "C"
            if clasificacion_abc == "A":
                cobertura_objetivo = 45
            elif clasificacion_abc == "B":
                cobertura_objetivo = 30
            else:
                cobertura_objetivo = 21

            # Margen de seguridad según variabilidad (entre 10% y 40%)
            margen_seguridad_factor = min(max(0.1 + variabilidad, 0.1), 0.4)
            demanda_objetivo = venta_diaria * cobertura_objetivo * (1 + margen_seguridad_factor)

            # Cantidad sugerida = demanda objetivo - stock actual
            cantidad_sugerida = max(0, int(round(demanda_objetivo - stock_actual)))
            if cantidad_sugerida <= 0:
                continue
            
            # Precio de compra (de ventas o inventario)
            precio_compra = data["precio_compra"] or inventario.get(nombre, {}).get("precio", 0)
            
            # Costo estimado
            costo_estimado = cantidad_sugerida * (precio_compra or 0)
            
            # Prioridad por días de stock
            if dias_stock <= 3:
                prioridad = "🔴 Urgente"
            elif dias_stock <= 7:
                prioridad = "🟠 Alta"
            elif dias_stock <= 15:
                prioridad = "🟡 Media"
            else:
                prioridad = "🟢 Baja"

            # ROI estimado (si tenemos margen unitario aproximado)
            # Aproximamos margen como (precio_venta_promedio - precio_compra)
            if unidades_vendidas > 0:
                precio_venta_promedio = data["total_ventas"] / unidades_vendidas
            else:
                precio_venta_promedio = 0.0
            margen_unitario = max(0.0, precio_venta_promedio - (precio_compra or 0))
            roi_estimado = margen_unitario * cantidad_sugerida
            
            sugerencias.append(
                SugerenciaCompraResponse(
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
                    clasificacion_abc=clasificacion_abc,
                    tendencia=tendencia,
                    variabilidad=variabilidad,
                    cobertura_objetivo_dias=cobertura_objetivo,
                    roi_estimado=round(roi_estimado, 2),
                    unidades_vendidas_periodo=unidades_vendidas,
                )
            )
        
        # Ordenar por prioridad y días de stock (y luego por ROI descendente)
        prioridad_orden = {"🔴 Urgente": 0, "🟠 Alta": 1, "🟡 Media": 2, "🟢 Baja": 3}
        sugerencias.sort(
            key=lambda x: (
                prioridad_orden.get(x.prioridad, 4),
                x.dias_stock,
                -(x.roi_estimado or 0),
            )
        )
        
        return sugerencias
    
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



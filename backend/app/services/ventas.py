"""
Servicio de ventas - Lógica de negocio principal.
"""
from datetime import date, timedelta
from typing import List, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    FilterParams,
    VentaBase,
    MetricasResponse,
    AlertaResponse,
    TopProductoResponse,
    TopVendedorResponse,
    FiltrosOpciones,
)


class VentasService:
    """Servicio para operaciones de ventas."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _build_where_clause(self, filters: FilterParams) -> Tuple[str, dict]:
        """Construye la cláusula WHERE y parámetros."""
        where = "WHERE 1=1"
        params = {}
        
        if filters.fecha_inicio:
            where += " AND fecha_venta >= :fecha_inicio"
            params["fecha_inicio"] = filters.fecha_inicio
        
        if filters.fecha_fin:
            where += " AND fecha_venta <= :fecha_fin"
            params["fecha_fin"] = filters.fecha_fin
        
        if filters.productos:
            where += " AND nombre = ANY(:productos)"
            params["productos"] = filters.productos
        
        if filters.vendedores:
            where += " AND vendedor = ANY(:vendedores)"
            params["vendedores"] = filters.vendedores
        
        if filters.familias:
            where += " AND familia = ANY(:familias)"
            params["familias"] = filters.familias
        
        if filters.metodos:
            where += " AND metodo = ANY(:metodos)"
            params["metodos"] = filters.metodos
        
        if filters.proveedores:
            where += " AND proveedor_moda = ANY(:proveedores)"
            params["proveedores"] = filters.proveedores
        
        if filters.precio_min is not None:
            where += " AND precio >= :precio_min"
            params["precio_min"] = filters.precio_min
        
        if filters.precio_max is not None:
            where += " AND precio <= :precio_max"
            params["precio_max"] = filters.precio_max
        
        if filters.cantidad_min is not None:
            where += " AND cantidad >= :cantidad_min"
            params["cantidad_min"] = filters.cantidad_min
        
        if filters.cantidad_max is not None:
            where += " AND cantidad <= :cantidad_max"
            params["cantidad_max"] = filters.cantidad_max
        
        return where, params
    
    async def get_ventas_paginated(
        self, 
        filters: FilterParams,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[VentaBase], int, int]:
        """Obtiene ventas paginadas con filtros aplicados."""
        where, params = self._build_where_clause(filters)
        
        # Query para contar total
        count_query = f"SELECT COUNT(*) FROM reportes_ventas_30dias {where}"
        count_result = await self.db.execute(text(count_query), params)
        total = count_result.scalar() or 0
        
        # Query con paginación
        offset = (page - 1) * page_size
        query = f"""
            SELECT * FROM reportes_ventas_30dias 
            {where}
            ORDER BY fecha_venta DESC, nombre
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = offset
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        ventas = self._rows_to_ventas(rows)
        total_pages = (total + page_size - 1) // page_size
        
        return ventas, total, total_pages
    
    def _rows_to_ventas(self, rows) -> List[VentaBase]:
        """Convierte rows de DB a lista de VentaBase."""
        ventas = []
        for row in rows:
            row_dict = row._asdict()
            precio = float(row_dict.get("precio") or 0)
            cantidad = int(row_dict.get("cantidad") or 0)
            precio_compra = row_dict.get("precio_promedio_compra")
            precio_compra = float(precio_compra) if precio_compra else None
            
            total_venta = precio * cantidad
            margen = (precio - precio_compra) if precio_compra else None
            margen_porcentaje = (margen / precio * 100) if margen and precio else None
            total_margen = (margen * cantidad) if margen else None
            
            ventas.append(VentaBase(
                nombre=row_dict.get("nombre", ""),
                precio=precio,
                cantidad=cantidad,
                metodo=row_dict.get("metodo"),
                vendedor=row_dict.get("vendedor"),
                fecha_venta=row_dict.get("fecha_venta"),
                familia=row_dict.get("familia"),
                proveedor_moda=row_dict.get("proveedor_moda"),
                precio_promedio_compra=precio_compra,
                total_venta=total_venta,
                margen=margen,
                margen_porcentaje=round(margen_porcentaje, 2) if margen_porcentaje else None,
                total_margen=total_margen,
            ))
        return ventas
    
    async def get_ventas(self, filters: FilterParams) -> Tuple[List[VentaBase], int]:
        """Obtiene ventas con filtros aplicados (sin paginación)."""
        query = "SELECT * FROM reportes_ventas_30dias WHERE 1=1"
        params = {}
        
        if filters.fecha_inicio:
            query += " AND fecha_venta >= :fecha_inicio"
            params["fecha_inicio"] = filters.fecha_inicio
        
        if filters.fecha_fin:
            query += " AND fecha_venta <= :fecha_fin"
            params["fecha_fin"] = filters.fecha_fin
        
        if filters.productos:
            query += " AND nombre = ANY(:productos)"
            params["productos"] = filters.productos
        
        if filters.vendedores:
            query += " AND vendedor = ANY(:vendedores)"
            params["vendedores"] = filters.vendedores
        
        if filters.familias:
            query += " AND familia = ANY(:familias)"
            params["familias"] = filters.familias
        
        if filters.metodos:
            query += " AND metodo = ANY(:metodos)"
            params["metodos"] = filters.metodos
        
        if filters.proveedores:
            query += " AND proveedor_moda = ANY(:proveedores)"
            params["proveedores"] = filters.proveedores
        
        if filters.precio_min is not None:
            query += " AND precio >= :precio_min"
            params["precio_min"] = filters.precio_min
        
        if filters.precio_max is not None:
            query += " AND precio <= :precio_max"
            params["precio_max"] = filters.precio_max
        
        if filters.cantidad_min is not None:
            query += " AND cantidad >= :cantidad_min"
            params["cantidad_min"] = filters.cantidad_min
        
        if filters.cantidad_max is not None:
            query += " AND cantidad <= :cantidad_max"
            params["cantidad_max"] = filters.cantidad_max
        
        query += " ORDER BY fecha_venta DESC, nombre"
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        ventas = []
        for row in rows:
            row_dict = row._asdict()
            precio = float(row_dict.get("precio") or 0)
            cantidad = int(row_dict.get("cantidad") or 0)
            precio_compra = row_dict.get("precio_promedio_compra")
            precio_compra = float(precio_compra) if precio_compra else None
            
            total_venta = precio * cantidad
            margen = (precio - precio_compra) if precio_compra else None
            margen_porcentaje = (margen / precio * 100) if margen and precio else None
            total_margen = (margen * cantidad) if margen else None
            
            ventas.append(VentaBase(
                nombre=row_dict.get("nombre", ""),
                precio=precio,
                cantidad=cantidad,
                metodo=row_dict.get("metodo"),
                vendedor=row_dict.get("vendedor"),
                fecha_venta=row_dict.get("fecha_venta"),
                familia=row_dict.get("familia"),
                proveedor_moda=row_dict.get("proveedor_moda"),
                precio_promedio_compra=precio_compra,
                total_venta=total_venta,
                margen=margen,
                margen_porcentaje=round(margen_porcentaje, 2) if margen_porcentaje else None,
                total_margen=total_margen,
            ))
        
        return ventas, len(ventas)
    
    async def get_periodo_anterior(self) -> pd.DataFrame:
        """Obtiene datos del período anterior (30-60 días atrás)."""
        fecha_inicio = date.today() - timedelta(days=60)
        fecha_fin = date.today() - timedelta(days=31)
        
        query = """
            SELECT 
                f.nombre,
                f.precio,
                f.cantidad,
                f.metodo,
                f.vendedor,
                f.fecha as fecha_venta,
                i.familia,
                (f.precio * f.cantidad) as total_venta
            FROM facturas f
            LEFT JOIN items i ON f.item_id = i.id
            WHERE f.fecha BETWEEN :fecha_inicio AND :fecha_fin
        """
        
        result = await self.db.execute(
            text(query),
            {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}
        )
        rows = result.fetchall()
        
        if not rows:
            return pd.DataFrame()
        
        data = [row._asdict() for row in rows]
        return pd.DataFrame(data)
    
    async def get_metricas(self, filters: FilterParams) -> MetricasResponse:
        """Calcula métricas principales con comparación."""
        ventas, _ = await self.get_ventas(filters)
        df_prev = await self.get_periodo_anterior()
        
        if not ventas:
            return MetricasResponse(
                total_ventas=0,
                total_registros=0,
                precio_promedio=0,
                margen_promedio=0,
                margen_total=0,
            )
        
        total_ventas = sum(v.total_venta for v in ventas)
        total_registros = len(ventas)
        precio_promedio = sum(v.precio for v in ventas) / len(ventas)
        
        margenes = [v.margen for v in ventas if v.margen is not None]
        margen_promedio = sum(margenes) / len(margenes) if margenes else 0
        margen_total = sum(v.total_margen for v in ventas if v.total_margen is not None)
        
        # Calcular deltas
        delta_ventas = None
        delta_registros = None
        delta_precio = None
        
        if not df_prev.empty:
            prev_total = df_prev["total_venta"].sum()
            prev_registros = len(df_prev)
            prev_precio = df_prev["precio"].mean()
            
            if prev_total > 0:
                delta = ((total_ventas - prev_total) / prev_total) * 100
                delta_ventas = f"{delta:+.1f}%"
            
            if prev_registros > 0:
                delta = ((total_registros - prev_registros) / prev_registros) * 100
                delta_registros = f"{delta:+.1f}%"
            
            if prev_precio > 0:
                delta = ((precio_promedio - prev_precio) / prev_precio) * 100
                delta_precio = f"{delta:+.1f}%"
        
        return MetricasResponse(
            total_ventas=round(total_ventas, 2),
            total_registros=total_registros,
            precio_promedio=round(precio_promedio, 2),
            margen_promedio=round(margen_promedio, 2),
            margen_total=round(margen_total, 2),
            delta_ventas=delta_ventas,
            delta_registros=delta_registros,
            delta_precio=delta_precio,
        )
    
    async def get_alertas(self, filters: FilterParams) -> List[AlertaResponse]:
        """Genera alertas del sistema."""
        ventas, _ = await self.get_ventas(filters)
        alertas = []
        
        if not ventas:
            return alertas
        
        # Alerta: Productos con margen negativo
        negativos = [v for v in ventas if v.margen is not None and v.margen < 0]
        if negativos:
            total_perdida = sum(v.total_margen for v in negativos if v.total_margen)
            alertas.append(AlertaResponse(
                tipo="error",
                icono="🚨",
                titulo=f"{len(negativos)} ventas con margen negativo",
                detalle=f"Pérdida total: ${abs(total_perdida):,.2f}",
                datos=[{
                    "nombre": v.nombre,
                    "precio": v.precio,
                    "precio_compra": v.precio_promedio_compra,
                    "margen": v.margen,
                    "cantidad": v.cantidad
                } for v in negativos[:10]]
            ))
        
        # Alerta: Margen bajo (<10%)
        margen_bajo = [v for v in ventas 
                       if v.margen is not None and v.margen > 0 
                       and v.margen_porcentaje is not None and v.margen_porcentaje < 10]
        if margen_bajo:
            alertas.append(AlertaResponse(
                tipo="warning",
                icono="⚠️",
                titulo=f"{len(margen_bajo)} ventas con margen menor al 10%",
                detalle="Considera revisar los precios de estos productos",
                datos=[{
                    "nombre": v.nombre,
                    "precio": v.precio,
                    "margen_porcentaje": v.margen_porcentaje,
                    "cantidad": v.cantidad
                } for v in margen_bajo[:10]]
            ))
        
        # Alerta: Vendedores bajo rendimiento
        ventas_por_vendedor = {}
        for v in ventas:
            if v.vendedor:
                ventas_por_vendedor[v.vendedor] = ventas_por_vendedor.get(v.vendedor, 0) + v.total_venta
        
        if ventas_por_vendedor:
            promedio = sum(ventas_por_vendedor.values()) / len(ventas_por_vendedor)
            bajo_rendimiento = {k: v for k, v in ventas_por_vendedor.items() if v < promedio * 0.5}
            
            if bajo_rendimiento:
                alertas.append(AlertaResponse(
                    tipo="info",
                    icono="📉",
                    titulo=f"{len(bajo_rendimiento)} vendedores bajo el 50% del promedio",
                    detalle=f"Promedio de ventas: ${promedio:,.2f}",
                    datos=[{"vendedor": k, "total_venta": v} for k, v in bajo_rendimiento.items()]
                ))
        
        return alertas
    
    async def get_top_productos(self, filters: FilterParams, limit: int = 5) -> List[TopProductoResponse]:
        """Obtiene top productos más vendidos."""
        ventas, _ = await self.get_ventas(filters)
        
        productos = {}
        for v in ventas:
            if v.nombre not in productos:
                productos[v.nombre] = {"cantidad": 0, "total_venta": 0}
            productos[v.nombre]["cantidad"] += v.cantidad
            productos[v.nombre]["total_venta"] += v.total_venta
        
        sorted_productos = sorted(productos.items(), key=lambda x: x[1]["cantidad"], reverse=True)[:limit]
        
        return [
            TopProductoResponse(
                nombre=nombre,
                cantidad=data["cantidad"],
                total_venta=round(data["total_venta"], 2)
            )
            for nombre, data in sorted_productos
        ]
    
    async def get_top_vendedores(self, filters: FilterParams, limit: int = 5) -> List[TopVendedorResponse]:
        """Obtiene top vendedores."""
        ventas, _ = await self.get_ventas(filters)
        
        vendedores = {}
        for v in ventas:
            if v.vendedor:
                if v.vendedor not in vendedores:
                    vendedores[v.vendedor] = {"total_venta": 0, "cantidad": 0}
                vendedores[v.vendedor]["total_venta"] += v.total_venta
                vendedores[v.vendedor]["cantidad"] += v.cantidad
        
        sorted_vendedores = sorted(vendedores.items(), key=lambda x: x[1]["total_venta"], reverse=True)[:limit]
        
        return [
            TopVendedorResponse(
                vendedor=vendedor,
                total_venta=round(data["total_venta"], 2),
                cantidad=data["cantidad"]
            )
            for vendedor, data in sorted_vendedores
        ]
    
    async def get_filtros_opciones(self) -> FiltrosOpciones:
        """Obtiene opciones disponibles para filtros."""
        query = """
            SELECT 
                ARRAY_AGG(DISTINCT nombre) as productos,
                ARRAY_AGG(DISTINCT vendedor) FILTER (WHERE vendedor IS NOT NULL) as vendedores,
                ARRAY_AGG(DISTINCT familia) FILTER (WHERE familia IS NOT NULL) as familias,
                ARRAY_AGG(DISTINCT metodo) FILTER (WHERE metodo IS NOT NULL) as metodos,
                ARRAY_AGG(DISTINCT proveedor_moda) FILTER (WHERE proveedor_moda IS NOT NULL) as proveedores,
                MIN(precio) as precio_min,
                MAX(precio) as precio_max,
                MIN(cantidad) as cantidad_min,
                MAX(cantidad) as cantidad_max,
                MIN(fecha_venta) as fecha_min,
                MAX(fecha_venta) as fecha_max
            FROM reportes_ventas_30dias
        """
        
        result = await self.db.execute(text(query))
        row = result.fetchone()
        
        if not row:
            return FiltrosOpciones(
                productos=[],
                vendedores=[],
                familias=[],
                metodos=[],
                proveedores=[],
                precio_min=0,
                precio_max=0,
                cantidad_min=0,
                cantidad_max=0,
                fecha_min=date.today(),
                fecha_max=date.today(),
            )
        
        row_dict = row._asdict()
        
        return FiltrosOpciones(
            productos=sorted(row_dict.get("productos") or []),
            vendedores=sorted(row_dict.get("vendedores") or []),
            familias=sorted(row_dict.get("familias") or []),
            metodos=sorted(row_dict.get("metodos") or []),
            proveedores=sorted(row_dict.get("proveedores") or []),
            precio_min=float(row_dict.get("precio_min") or 0),
            precio_max=float(row_dict.get("precio_max") or 0),
            cantidad_min=int(row_dict.get("cantidad_min") or 0),
            cantidad_max=int(row_dict.get("cantidad_max") or 0),
            fecha_min=row_dict.get("fecha_min") or date.today(),
            fecha_max=row_dict.get("fecha_max") or date.today(),
        )
    
    async def get_ventas_por_dia(self, filters: FilterParams) -> List[dict]:
        """Obtiene ventas agrupadas por día."""
        ventas, _ = await self.get_ventas(filters)
        
        ventas_dia = {}
        for v in ventas:
            fecha = v.fecha_venta
            if fecha not in ventas_dia:
                ventas_dia[fecha] = {"total_venta": 0, "cantidad": 0}
            ventas_dia[fecha]["total_venta"] += v.total_venta
            ventas_dia[fecha]["cantidad"] += v.cantidad
        
        return [
            {"fecha": str(fecha), "total_venta": round(data["total_venta"], 2), "cantidad": data["cantidad"]}
            for fecha, data in sorted(ventas_dia.items())
        ]
    
    async def get_ventas_por_vendedor(self, filters: FilterParams) -> List[dict]:
        """Obtiene ventas agrupadas por vendedor."""
        ventas, _ = await self.get_ventas(filters)
        
        vendedores = {}
        for v in ventas:
            if v.vendedor:
                if v.vendedor not in vendedores:
                    vendedores[v.vendedor] = 0
                vendedores[v.vendedor] += v.total_venta
        
        sorted_vendedores = sorted(vendedores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [
            {"vendedor": vendedor, "total_venta": round(total, 2)}
            for vendedor, total in sorted_vendedores
        ]
    
    async def get_ventas_por_familia(self, filters: FilterParams) -> List[dict]:
        """Obtiene ventas agrupadas por familia."""
        ventas, _ = await self.get_ventas(filters)
        
        familias = {}
        for v in ventas:
            if v.familia:
                if v.familia not in familias:
                    familias[v.familia] = 0
                familias[v.familia] += v.total_venta
        
        return [
            {"familia": familia, "total_venta": round(total, 2)}
            for familia, total in familias.items()
        ]
    
    async def get_ventas_por_metodo(self, filters: FilterParams) -> List[dict]:
        """Obtiene ventas agrupadas por método de pago."""
        ventas, _ = await self.get_ventas(filters)
        
        metodos = {}
        for v in ventas:
            if v.metodo:
                if v.metodo not in metodos:
                    metodos[v.metodo] = 0
                metodos[v.metodo] += v.total_venta
        
        return [
            {"metodo": metodo, "total_venta": round(total, 2)}
            for metodo, total in sorted(metodos.items(), key=lambda x: x[1], reverse=True)
        ]
    
    async def get_top_productos_cantidad(self, filters: FilterParams, limit: int = 10) -> List[dict]:
        """Obtiene top productos por cantidad vendida."""
        ventas, _ = await self.get_ventas(filters)
        
        productos = {}
        for v in ventas:
            if v.nombre not in productos:
                productos[v.nombre] = 0
            productos[v.nombre] += v.cantidad
        
        sorted_productos = sorted(productos.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [
            {"nombre": nombre, "cantidad": cantidad}
            for nombre, cantidad in sorted_productos
        ]


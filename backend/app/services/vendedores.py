"""
Servicio de análisis de vendedores.
Contiene la lógica de negocio extraída de las rutas.
"""
from typing import List

from app.models.schemas import (
    VendedorRankingResponse,
    VendedorDetalleResponse,
)
from app.services.ventas import VentasService


class VendedoresService:
    """Servicio para análisis y ranking de vendedores."""

    def __init__(self, ventas_service: VentasService):
        self.ventas_service = ventas_service

    async def get_ranking(self, filters) -> List[VendedorRankingResponse]:
        """Obtiene ranking de vendedores con métricas agregadas."""
        ventas, _ = await self.ventas_service.get_ventas(filters)

        if not ventas:
            return []

        # Agrupar por vendedor
        vendedores: dict = {}
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

        # Calcular promedio de ventas para rendimiento
        promedio_ventas = (
            sum(d["ventas_totales"] for d in vendedores.values()) / len(vendedores)
            if vendedores
            else 0
        )

        ranking = []
        for vendedor, data in vendedores.items():
            ticket_promedio = (
                sum(data["precios"]) / len(data["precios"]) if data["precios"] else 0
            )
            margen_porcentaje = (
                (data["margen_total"] / data["ventas_totales"] * 100)
                if data["ventas_totales"] > 0
                else 0
            )

            # Determinar rendimiento sin emojis
            if data["ventas_totales"] > promedio_ventas * 1.2:
                rendimiento = "Excelente"
            elif data["ventas_totales"] > promedio_ventas * 0.8:
                rendimiento = "Normal"
            else:
                rendimiento = "Bajo"

            ranking.append(
                VendedorRankingResponse(
                    vendedor=vendedor,
                    ventas_totales=round(data["ventas_totales"], 2),
                    margen_total=round(data["margen_total"], 2),
                    productos_unicos=len(data["productos"]),
                    unidades=data["unidades"],
                    ticket_promedio=round(ticket_promedio, 2),
                    margen_porcentaje=round(margen_porcentaje, 2),
                    rendimiento=rendimiento,
                )
            )

        # Ordenar por ventas totales
        ranking.sort(key=lambda x: x.ventas_totales, reverse=True)
        return ranking

    async def get_detalle(self, nombre: str, filters) -> VendedorDetalleResponse:
        """Obtiene detalle de un vendedor específico."""
        ventas, _ = await self.ventas_service.get_ventas(filters)

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
        margen_porcentaje = (
            (margen_total / ventas_totales * 100) if ventas_totales > 0 else 0
        )

        # Calcular delta vs promedio del equipo
        ventas_por_vendedor: dict = {}
        for v in ventas:
            if v.vendedor:
                ventas_por_vendedor[v.vendedor] = (
                    ventas_por_vendedor.get(v.vendedor, 0) + v.total_venta
                )

        promedio_equipo = (
            sum(ventas_por_vendedor.values()) / len(ventas_por_vendedor)
            if ventas_por_vendedor
            else 0
        )
        delta_vs_promedio = (
            ((ventas_totales - promedio_equipo) / promedio_equipo * 100)
            if promedio_equipo > 0
            else 0
        )

        # Ventas diarias
        ventas_dia: dict = {}
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
        productos: dict = {}
        for v in ventas_vendedor:
            if v.nombre not in productos:
                productos[v.nombre] = {"total_venta": 0, "cantidad": 0}
            productos[v.nombre]["total_venta"] += v.total_venta
            productos[v.nombre]["cantidad"] += v.cantidad

        top_productos = [
            {
                "nombre": nombre_prod,
                "total_venta": round(data["total_venta"], 2),
                "cantidad": data["cantidad"],
            }
            for nombre_prod, data in sorted(
                productos.items(), key=lambda x: x[1]["total_venta"], reverse=True
            )[:10]
        ]

        # Métodos de pago
        metodos: dict = {}
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

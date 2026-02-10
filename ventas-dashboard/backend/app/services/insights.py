"""
Servicio de insights inteligentes para gestión de inventario.
Cruza información de ventas, compras (sugerencias) y ABC para generar insights accionables.
"""
from typing import List, Dict, Any

from app.models.schemas import FilterParams, SugerenciaCompraResponse
from app.services.ventas import VentasService
from app.services.compras import ComprasService
from sqlalchemy.ext.asyncio import AsyncSession


class InsightsService:
    """Servicio de insights de alto nivel."""

    def __init__(self, db: AsyncSession, ventas_service: VentasService):
        self.db = db
        self.ventas_service = ventas_service
        self.compras_service = ComprasService(db, ventas_service)

    async def get_insights(self, filters: FilterParams) -> Dict[str, Any]:
        """
        Genera un conjunto de insights cruzando ABC + inventario + tendencias.

        Estructura de respuesta:
        {
            "productos_en_riesgo": [...],
            "oportunidades": [...],
            "sobre_stock": [...],
            "proveedores_en_riesgo": [...],
        }
        """
        sugerencias: List[SugerenciaCompraResponse] = await self.compras_service.get_sugerencias(filters)

        if not sugerencias:
            return {
                "productos_en_riesgo": [],
                "oportunidades": [],
                "sobre_stock": [],
                "proveedores_en_riesgo": [],
            }

        # Productos en riesgo: clase A con poco stock
        productos_en_riesgo = [
            s
            for s in sugerencias
            if (s.clasificacion_abc or "C") == "A" and s.dias_stock <= 7
        ]

        # Oportunidades: alto ROI estimado, stock bajo o en cero
        oportunidades = [
            s
            for s in sugerencias
            if (s.roi_estimado or 0) > 0 and s.cantidad_disponible <= s.cobertura_objetivo_dias * s.venta_diaria * 0.3
        ]
        oportunidades.sort(key=lambda x: (x.roi_estimado or 0), reverse=True)

        # Sobre-stock: clase C con muchos días de stock
        sobre_stock = [
            s
            for s in sugerencias
            if (s.clasificacion_abc or "C") == "C" and s.dias_stock >= 90
        ]

        # Proveedores en riesgo: muchos productos en riesgo por proveedor
        proveedores_map: Dict[str, Dict[str, Any]] = {}
        for s in productos_en_riesgo:
            if not s.proveedor:
                continue
            if s.proveedor not in proveedores_map:
                proveedores_map[s.proveedor] = {
                    "proveedor": s.proveedor,
                    "productos_en_riesgo": 0,
                    "costo_estimado": 0.0,
                }
            proveedores_map[s.proveedor]["productos_en_riesgo"] += 1
            proveedores_map[s.proveedor]["costo_estimado"] += s.costo_estimado

        proveedores_en_riesgo = sorted(
            proveedores_map.values(),
            key=lambda x: (x["productos_en_riesgo"], x["costo_estimado"]),
            reverse=True,
        )

        return {
            "productos_en_riesgo": productos_en_riesgo,
            "oportunidades": oportunidades[:20],
            "sobre_stock": sobre_stock[:20],
            "proveedores_en_riesgo": proveedores_en_riesgo,
        }


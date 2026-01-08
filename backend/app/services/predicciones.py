"""
Servicio de predicciones de ventas.
"""
from datetime import date, timedelta
from typing import List

from app.models.schemas import FilterParams, PrediccionResponse, VentaDiariaResponse
from app.services.ventas import VentasService


class PrediccionesService:
    """Servicio para predicciones de ventas."""
    
    def __init__(self, ventas_service: VentasService):
        self.ventas_service = ventas_service
    
    async def get_predicciones(self, filters: FilterParams) -> PrediccionResponse:
        """Genera predicciones de ventas."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        
        if not ventas:
            return PrediccionResponse(
                venta_diaria_promedio=0,
                tendencia_diaria=0,
                prediccion_semanal=0,
                prediccion_mensual=0,
                historico=[],
                predicciones=[],
                predicciones_upper=[],
                predicciones_lower=[],
                ventas_por_dia_semana=[],
            )
        
        # Agrupar ventas por día
        ventas_dia = {}
        for v in ventas:
            fecha = v.fecha_venta
            if fecha not in ventas_dia:
                ventas_dia[fecha] = 0
            ventas_dia[fecha] += v.total_venta
        
        # Ordenar por fecha
        fechas_ordenadas = sorted(ventas_dia.keys())
        valores = [ventas_dia[f] for f in fechas_ordenadas]
        
        if len(valores) < 7:
            # No hay suficientes datos
            historico = [
                VentaDiariaResponse(fecha=f, ventas=ventas_dia[f])
                for f in fechas_ordenadas
            ]
            return PrediccionResponse(
                venta_diaria_promedio=sum(valores) / len(valores) if valores else 0,
                tendencia_diaria=0,
                prediccion_semanal=0,
                prediccion_mensual=0,
                historico=historico,
                predicciones=[],
                predicciones_upper=[],
                predicciones_lower=[],
                ventas_por_dia_semana=[],
            )
        
        # Calcular media móvil de 7 días
        media_movil = []
        for i in range(len(valores)):
            if i < 6:
                media_movil.append(sum(valores[:i+1]) / (i+1))
            else:
                media_movil.append(sum(valores[i-6:i+1]) / 7)
        
        # Tendencia (diferencia entre última media y media de hace 7 días)
        ultima_media = media_movil[-1]
        tendencia = (media_movil[-1] - media_movil[-7]) / 7 if len(media_movil) >= 7 else 0
        
        # Predicciones para los próximos 7 días
        ultima_fecha = fechas_ordenadas[-1]
        fechas_futuras = [ultima_fecha + timedelta(days=i) for i in range(1, 8)]
        predicciones_valores = [ultima_media + tendencia * i for i in range(1, 8)]
        
        # Banda de confianza ±20%
        predicciones_upper = [p * 1.2 for p in predicciones_valores]
        predicciones_lower = [p * 0.8 for p in predicciones_valores]
        
        # Histórico con media móvil
        historico = [
            VentaDiariaResponse(
                fecha=fechas_ordenadas[i],
                ventas=round(valores[i], 2),
                media_movil_7d=round(media_movil[i], 2)
            )
            for i in range(len(fechas_ordenadas))
        ]
        
        # Predicciones
        predicciones = [
            VentaDiariaResponse(
                fecha=fechas_futuras[i],
                ventas=round(predicciones_valores[i], 2)
            )
            for i in range(len(fechas_futuras))
        ]
        
        # Ventas por día de la semana
        dias_semana = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 
                       4: "Viernes", 5: "Sábado", 6: "Domingo"}
        ventas_dia_semana = {i: [] for i in range(7)}
        
        for v in ventas:
            dia = v.fecha_venta.weekday()
            ventas_dia_semana[dia].append(v.total_venta)
        
        ventas_por_dia_semana = [
            {
                "dia": dias_semana[i],
                "promedio": round(sum(ventas_dia_semana[i]) / len(ventas_dia_semana[i]), 2) if ventas_dia_semana[i] else 0
            }
            for i in range(7)
        ]
        
        return PrediccionResponse(
            venta_diaria_promedio=round(ultima_media, 2),
            tendencia_diaria=round(tendencia, 2),
            prediccion_semanal=round(ultima_media * 7 + tendencia * 28, 2),
            prediccion_mensual=round(ultima_media * 30 + tendencia * 465, 2),
            historico=historico,
            predicciones=predicciones,
            predicciones_upper=[round(p, 2) for p in predicciones_upper],
            predicciones_lower=[round(p, 2) for p in predicciones_lower],
            ventas_por_dia_semana=ventas_por_dia_semana,
        )


"""
Servicio de predicciones de ventas.
Usa regresión lineal ponderada + estacionalidad semanal + banda de confianza basada en desviación estándar.
"""
from datetime import date, timedelta
from typing import List, Tuple

import numpy as np

from app.models.schemas import FilterParams, PrediccionResponse, VentaDiariaResponse
from app.services.ventas import VentasService


class PrediccionesService:
    """Servicio para predicciones de ventas."""
    
    DIAS_PREDICCION = 14  # Predecir 14 días en lugar de 7
    VENTANA_MEDIA_MOVIL = 7
    
    def __init__(self, ventas_service: VentasService):
        self.ventas_service = ventas_service
    
    @staticmethod
    def _regresion_lineal_ponderada(
        valores: List[float],
    ) -> Tuple[float, float]:
        """Regresión lineal con pesos exponenciales (más peso a datos recientes).
        
        Returns:
            (pendiente, intercepto) de la recta y = pendiente*x + intercepto
        """
        n = len(valores)
        x = np.arange(n, dtype=float)
        y = np.array(valores, dtype=float)
        
        # Pesos exponenciales: más reciente = más peso
        decay = 0.95
        weights = np.array([decay ** (n - 1 - i) for i in range(n)])
        
        # Regresión ponderada: minimizar sum(w * (y - (a*x + b))^2)
        W = np.sum(weights)
        Wx = np.sum(weights * x)
        Wy = np.sum(weights * y)
        Wxx = np.sum(weights * x * x)
        Wxy = np.sum(weights * x * y)
        
        denom = W * Wxx - Wx * Wx
        if abs(denom) < 1e-10:
            return 0.0, float(np.mean(y))
        
        pendiente = (W * Wxy - Wx * Wy) / denom
        intercepto = (Wy - pendiente * Wx) / W
        
        return float(pendiente), float(intercepto)
    
    @staticmethod
    def _calcular_estacionalidad_semanal(
        fechas: list, valores: List[float]
    ) -> dict:
        """Calcula factores de estacionalidad por día de la semana.
        
        Returns:
            Dict {dia_semana: factor} donde factor > 1 = día fuerte, < 1 = día débil.
        """
        dias = {i: [] for i in range(7)}
        for fecha, valor in zip(fechas, valores):
            dias[fecha.weekday()].append(valor)
        
        promedios = {}
        for dia, vals in dias.items():
            promedios[dia] = np.mean(vals) if vals else 0
        
        media_global = np.mean(valores) if valores else 1
        if media_global == 0:
            media_global = 1
        
        factores = {dia: prom / media_global for dia, prom in promedios.items()}
        return factores
    
    async def get_predicciones(self, filters: FilterParams) -> PrediccionResponse:
        """Genera predicciones de ventas usando regresión lineal ponderada + estacionalidad."""
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
        ventas_dia: dict = {}
        for v in ventas:
            fecha = v.fecha_venta
            if fecha not in ventas_dia:
                ventas_dia[fecha] = 0
            ventas_dia[fecha] += v.total_venta
        
        # Ordenar por fecha
        fechas_ordenadas = sorted(ventas_dia.keys())
        valores = [ventas_dia[f] for f in fechas_ordenadas]
        n = len(valores)
        
        if n < 7:
            historico = [
                VentaDiariaResponse(fecha=f, ventas=round(ventas_dia[f], 2))
                for f in fechas_ordenadas
            ]
            promedio = sum(valores) / n if n > 0 else 0
            return PrediccionResponse(
                venta_diaria_promedio=round(promedio, 2),
                tendencia_diaria=0,
                prediccion_semanal=round(promedio * 7, 2),
                prediccion_mensual=round(promedio * 30, 2),
                historico=historico,
                predicciones=[],
                predicciones_upper=[],
                predicciones_lower=[],
                ventas_por_dia_semana=[],
            )
        
        # --- Media móvil de 7 días ---
        valores_arr = np.array(valores, dtype=float)
        media_movil = []
        for i in range(n):
            window_start = max(0, i - self.VENTANA_MEDIA_MOVIL + 1)
            media_movil.append(float(np.mean(valores_arr[window_start:i + 1])))
        
        # --- Regresión lineal ponderada para tendencia ---
        pendiente, intercepto = self._regresion_lineal_ponderada(valores)
        
        # Tendencia diaria
        tendencia_diaria = pendiente
        
        # --- Estacionalidad semanal ---
        factores_estacionalidad = self._calcular_estacionalidad_semanal(
            fechas_ordenadas, valores
        )
        
        # --- Generar predicciones ---
        ultima_fecha = fechas_ordenadas[-1]
        fechas_futuras = [
            ultima_fecha + timedelta(days=i) for i in range(1, self.DIAS_PREDICCION + 1)
        ]
        
        # Predicción = tendencia lineal * factor estacional del día
        predicciones_valores = []
        for i, fecha_futura in enumerate(fechas_futuras):
            x_futuro = n + i
            valor_tendencia = pendiente * x_futuro + intercepto
            factor = factores_estacionalidad.get(fecha_futura.weekday(), 1.0)
            prediccion = max(0, valor_tendencia * factor)  # No permitir negativos
            predicciones_valores.append(prediccion)
        
        # --- Banda de confianza basada en desviación estándar real ---
        # Calcular residuos de la regresión
        x_historico = np.arange(n, dtype=float)
        valores_ajustados = pendiente * x_historico + intercepto
        residuos = valores_arr - valores_ajustados
        std_residuos = float(np.std(residuos))
        
        # Banda crece con la distancia (incertidumbre aumenta)
        predicciones_upper = []
        predicciones_lower = []
        for i, pred in enumerate(predicciones_valores):
            margen = std_residuos * (1 + 0.1 * i)  # ±1 std que crece un 10% por día
            predicciones_upper.append(round(pred + margen, 2))
            predicciones_lower.append(round(max(0, pred - margen), 2))
        
        # --- Histórico con media móvil ---
        historico = [
            VentaDiariaResponse(
                fecha=fechas_ordenadas[i],
                ventas=round(valores[i], 2),
                media_movil_7d=round(media_movil[i], 2),
            )
            for i in range(n)
        ]
        
        # --- Predicciones ---
        predicciones = [
            VentaDiariaResponse(
                fecha=fechas_futuras[i],
                ventas=round(predicciones_valores[i], 2),
            )
            for i in range(len(fechas_futuras))
        ]
        
        # --- Ventas por día de la semana ---
        dias_semana_nombres = {
            0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
            4: "Viernes", 5: "Sábado", 6: "Domingo",
        }
        ventas_dia_semana: dict = {i: [] for i in range(7)}
        for v in ventas:
            dia = v.fecha_venta.weekday()
            ventas_dia_semana[dia].append(v.total_venta)
        
        ventas_por_dia_semana = [
            {
                "dia": dias_semana_nombres[i],
                "promedio": round(
                    sum(ventas_dia_semana[i]) / len(ventas_dia_semana[i]), 2
                )
                if ventas_dia_semana[i]
                else 0,
            }
            for i in range(7)
        ]
        
        # Métricas resumen
        venta_diaria_promedio = float(np.mean(valores_arr[-7:]))  # Promedio últimos 7 días
        pred_arr = np.array(predicciones_valores)
        prediccion_semanal = float(np.sum(pred_arr[:7]))
        prediccion_mensual = float(np.sum(pred_arr[:14])) * (30 / 14)  # Extrapolar a 30 días
        
        return PrediccionResponse(
            venta_diaria_promedio=round(venta_diaria_promedio, 2),
            tendencia_diaria=round(tendencia_diaria, 2),
            prediccion_semanal=round(prediccion_semanal, 2),
            prediccion_mensual=round(prediccion_mensual, 2),
            historico=historico,
            predicciones=predicciones,
            predicciones_upper=predicciones_upper,
            predicciones_lower=predicciones_lower,
            ventas_por_dia_semana=ventas_por_dia_semana,
        )



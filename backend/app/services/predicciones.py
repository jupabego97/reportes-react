"""
Servicio de predicciones de ventas.
Usa regresión lineal ponderada + estacionalidad semanal + banda de confianza basada en desviación estándar.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.models.schemas import (
    FilterParams,
    PrediccionResponse,
    PrediccionGrupoResponse,
    PrediccionDesgloseResponse,
    VentaDiariaResponse,
)
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

    def _calcular_prediccion_para_serie(
        self,
        fechas_ordenadas: List[date],
        valores: List[float],
    ) -> Optional[
        Tuple[
            float, float, float, List, List[float], List[float], Optional[float], Optional[float]
        ]
    ]:
        """Calcula predicción para una serie (fechas, valores). Retorna None si datos insuficientes."""
        n = len(valores)
        if n < 7:
            return None
        valores_arr = np.array(valores, dtype=float)
        pendiente, intercepto = self._regresion_lineal_ponderada(valores)
        factores = self._calcular_estacionalidad_semanal(fechas_ordenadas, valores)
        ultima_fecha = fechas_ordenadas[-1]
        fechas_futuras = [
            ultima_fecha + timedelta(days=i) for i in range(1, self.DIAS_PREDICCION + 1)
        ]
        predicciones_valores = []
        for i, fecha_futura in enumerate(fechas_futuras):
            x_futuro = n + i
            valor_tendencia = pendiente * x_futuro + intercepto
            factor = factores.get(fecha_futura.weekday(), 1.0)
            predicciones_valores.append(max(0, valor_tendencia * factor))
        x_hist = np.arange(n, dtype=float)
        valores_ajustados = pendiente * x_hist + intercepto
        residuos = valores_arr - valores_ajustados
        std_residuos = float(np.std(residuos))
        predicciones_upper = [
            round(pred + std_residuos * (1 + 0.1 * i), 2) for i, pred in enumerate(predicciones_valores)
        ]
        predicciones_lower = [
            round(max(0, pred - std_residuos * (1 + 0.1 * i)), 2) for i, pred in enumerate(predicciones_valores)
        ]
        venta_diaria_promedio = float(np.mean(valores_arr[-7:]))
        pred_arr = np.array(predicciones_valores)
        prediccion_semanal = float(np.sum(pred_arr[:7]))
        prediccion_mensual = float(np.sum(pred_arr[:14])) * (30 / 14)
        mape_val = wape_val = None
        pred_insample = [
            max(0, (pendiente * i + intercepto) * factores.get(fechas_ordenadas[i].weekday(), 1.0))
            for i in range(n)
        ]
        pred_insample_arr = np.array(pred_insample)
        errores_abs = np.abs(valores_arr - pred_insample_arr)
        total_real = float(np.sum(valores_arr))
        if total_real > 0:
            wape_val = round(float(np.sum(errores_abs) / total_real * 100), 2)
        mask = valores_arr > 0
        if np.any(mask):
            ape = errores_abs[mask] / valores_arr[mask] * 100
            mape_val = round(float(np.mean(ape)), 2)
        predicciones = [
            VentaDiariaResponse(fecha=fechas_futuras[i], ventas=round(predicciones_valores[i], 2))
            for i in range(len(fechas_futuras))
        ]
        return (
            venta_diaria_promedio,
            prediccion_semanal,
            prediccion_mensual,
            predicciones,
            predicciones_upper,
            predicciones_lower,
            mape_val,
            wape_val,
        )
    
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
                mape=None,
                wape=None,
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
                mape=None,
                wape=None,
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

        # MAPE y WAPE (ajuste in-sample: predicción vs real en histórico)
        pred_insample = []
        for i in range(n):
            x_val = float(i)
            valor_tendencia = pendiente * x_val + intercepto
            factor = factores_estacionalidad.get(fechas_ordenadas[i].weekday(), 1.0)
            pred_insample.append(max(0, valor_tendencia * factor))
        pred_insample_arr = np.array(pred_insample)
        errores_abs = np.abs(valores_arr - pred_insample_arr)
        total_real = float(np.sum(valores_arr))
        mape_val: Optional[float] = None
        wape_val: Optional[float] = None
        if n > 0:
            # WAPE = sum(|actual-pred|) / sum(actual) * 100
            if total_real > 0:
                wape_val = round(float(np.sum(errores_abs) / total_real * 100), 2)
            # MAPE = mean(|actual-pred|/actual) * 100, solo donde actual > 0
            mask = valores_arr > 0
            if np.any(mask):
                ape = errores_abs[mask] / valores_arr[mask] * 100
                mape_val = round(float(np.mean(ape)), 2)

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
            mape=mape_val,
            wape=wape_val,
        )

    async def get_predicciones_desglose(
        self, filters: FilterParams, nivel: str
    ) -> PrediccionDesgloseResponse:
        """Predicciones desglosadas por familia o producto. Fallback a global si datos insuficientes."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        if not ventas:
            return PrediccionDesgloseResponse(nivel=nivel, grupos={})

        # Obtener predicción global para fallback
        pred_global = await self.get_predicciones(filters)
        total_ventas_periodo = sum(v.total_venta or 0 for v in ventas)

        # Agrupar por familia o producto
        key_attr = "familia" if nivel == "familia" else "nombre"
        grupos_ventas: Dict[str, List[Any]] = {}
        for v in ventas:
            key = getattr(v, key_attr) or "(sin clasificar)"
            if key not in grupos_ventas:
                grupos_ventas[key] = []
            grupos_ventas[key].append(v)

        grupos: Dict[str, PrediccionGrupoResponse] = {}
        for nombre_grupo, ventas_grupo in grupos_ventas.items():
            ventas_dia: Dict[date, float] = {}
            for v in ventas_grupo:
                f = v.fecha_venta
                ventas_dia[f] = ventas_dia.get(f, 0) + (v.total_venta or 0)
            fechas_ord = sorted(ventas_dia.keys())
            valores = [ventas_dia[f] for f in fechas_ord]
            ventas_grupo_total = sum(valores)

            result = self._calcular_prediccion_para_serie(fechas_ord, valores)
            if result is not None:
                vd, ps, pm, preds, pu, pl, mape, wape = result
                grupos[nombre_grupo] = PrediccionGrupoResponse(
                    venta_diaria_promedio=round(vd, 2),
                    prediccion_semanal=round(ps, 2),
                    prediccion_mensual=round(pm, 2),
                    predicciones=preds,
                    predicciones_upper=pu,
                    predicciones_lower=pl,
                    mape=mape,
                    wape=wape,
                    fallback_usado=False,
                )
            else:
                # Fallback: escalar predicción global por participación del grupo
                participacion = ventas_grupo_total / total_ventas_periodo if total_ventas_periodo > 0 else 0
                vd_fb = pred_global.venta_diaria_promedio * participacion
                ps_fb = pred_global.prediccion_semanal * participacion
                pm_fb = pred_global.prediccion_mensual * participacion
                preds_fb = [
                    VentaDiariaResponse(
                        fecha=p.fecha,
                        ventas=round(p.ventas * participacion, 2),
                    )
                    for p in pred_global.predicciones
                ]
                pu_fb = [round(x * participacion, 2) for x in pred_global.predicciones_upper]
                pl_fb = [round(x * participacion, 2) for x in pred_global.predicciones_lower]
                grupos[nombre_grupo] = PrediccionGrupoResponse(
                    venta_diaria_promedio=vd_fb,
                    prediccion_semanal=ps_fb,
                    prediccion_mensual=pm_fb,
                    predicciones=preds_fb,
                    predicciones_upper=pu_fb,
                    predicciones_lower=pl_fb,
                    mape=None,
                    wape=None,
                    fallback_usado=True,
                )

        return PrediccionDesgloseResponse(nivel=nivel, grupos=grupos)

    async def get_backtest_metricas(
        self, filters: FilterParams, semanas: int = 8
    ) -> dict:
        """Backtesting rolling: WAPE/MAPE sobre últimos N semanas (walk-forward)."""
        ventas, _ = await self.ventas_service.get_ventas(filters)
        if not ventas:
            return {"semanas": 0, "wape_promedio": None, "mape_promedio": None, "detalle": []}

        ventas_dia: Dict[date, float] = {}
        for v in ventas:
            f = v.fecha_venta
            ventas_dia[f] = ventas_dia.get(f, 0) + (v.total_venta or 0)
        fechas_ord = sorted(ventas_dia.keys())
        if len(fechas_ord) < 14:  # Mínimo 2 semanas
            return {"semanas": 0, "wape_promedio": None, "mape_promedio": None, "detalle": []}

        resultados = []
        for i in range(semanas):
            # Holdout: última semana de la ventana
            corte = len(fechas_ord) - 7 * (i + 1)
            if corte < 7:
                break
            fechas_train = fechas_ord[:corte]
            fechas_test = fechas_ord[corte : corte + 7]
            valores_train = [ventas_dia[f] for f in fechas_train]
            valores_test = [ventas_dia[f] for f in fechas_test]
            res = self._calcular_prediccion_para_serie(fechas_train, valores_train)
            if res is None:
                continue
            _, _, _, preds, _, _, _, _ = res
            pred_valores = [p.ventas for p in preds][:7]
            if len(pred_valores) < 7 or len(valores_test) < 7:
                continue
            pred_arr = np.array(pred_valores[: len(valores_test)])
            real_arr = np.array(valores_test)
            total_real = float(np.sum(real_arr))
            if total_real > 0:
                wape = float(np.sum(np.abs(real_arr - pred_arr)) / total_real * 100)
            else:
                wape = 0.0
            mask = real_arr > 0
            mape = (
                float(np.mean(np.abs(real_arr[mask] - pred_arr[mask]) / real_arr[mask] * 100))
                if np.any(mask)
                else 0.0
            )
            resultados.append({"semana": i + 1, "wape": round(wape, 2), "mape": round(mape, 2)})

        if not resultados:
            return {"semanas": 0, "wape_promedio": None, "mape_promedio": None, "detalle": []}
        wape_avg = round(float(np.mean([r["wape"] for r in resultados])), 2)
        mape_avg = round(float(np.mean([r["mape"] for r in resultados])), 2)
        return {
            "semanas": len(resultados),
            "wape_promedio": wape_avg,
            "mape_promedio": mape_avg,
            "detalle": resultados,
        }



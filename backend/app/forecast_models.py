"""
Modelos de pronóstico de demanda (Fase 2) — funciones puras, sin base de datos.

Diseño:
- La serie de entrada es SIEMPRE diaria y densa (los días sin venta valen 0).
  Omitir los ceros infla el forecast: un producto que vende 10 unidades un
  día al mes NO vende 10 diarias.
- Selección de modelo por comportamiento de la serie:
    * intermitente (>= 70% de días en cero)  → TSB (Teunter-Syntetos-Babai)
    * regular                                 → nivel SES × estacionalidad
      por día de semana
    * historia corta (< 14 días)              → media simple
- Salida probabilística: P10/P50/P90 a partir de los residuos empíricos.
  Nunca un número único: comprar con el P50 y proteger con el P90.

Cuando el historial acumulado supere ~6 meses, estos modelos son el piso
contra el que debe ganarse un modelo global (LightGBM) — misma interfaz.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

# Umbral de intermitencia: % de días en cero a partir del cual la serie se
# trata con TSB en lugar de modelos de nivel
UMBRAL_INTERMITENCIA = 0.70
MIN_DIAS_HISTORIA = 14


# =============================================================================
# Utilidades de serie
# =============================================================================

def serie_densa(
    ventas_por_fecha: Dict[date, float],
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
) -> Tuple[List[date], List[float]]:
    """Convierte un dict {fecha: unidades} en una serie diaria densa
    (con ceros explícitos en los días sin venta)."""
    if not ventas_por_fecha:
        return [], []
    inicio = fecha_inicio or min(ventas_por_fecha)
    fin = fecha_fin or max(ventas_por_fecha)
    fechas: List[date] = []
    valores: List[float] = []
    d = inicio
    while d <= fin:
        fechas.append(d)
        valores.append(float(ventas_por_fecha.get(d, 0.0)))
        d += timedelta(days=1)
    return fechas, valores


def es_intermitente(valores: Sequence[float]) -> bool:
    """Serie intermitente = mayoría de días sin venta."""
    if not valores:
        return True
    ceros = sum(1 for v in valores if v <= 0)
    return ceros / len(valores) >= UMBRAL_INTERMITENCIA


# =============================================================================
# Métricas de precisión
# =============================================================================

def wmape(reales: Sequence[float], predichos: Sequence[float]) -> Optional[float]:
    """WMAPE = Σ|real − pred| / Σ|real|. Métrica estándar de forecast retail
    (robusta ante días en cero, a diferencia del MAPE)."""
    if not reales or len(reales) != len(predichos):
        return None
    total_real = sum(abs(r) for r in reales)
    if total_real == 0:
        return None
    error = sum(abs(r - p) for r, p in zip(reales, predichos))
    return error / total_real


def sesgo_pct(reales: Sequence[float], predichos: Sequence[float]) -> Optional[float]:
    """Sesgo % = (Σpred − Σreal) / Σreal × 100. Positivo = sobre-pronóstico
    (exceso de inventario); negativo = sub-pronóstico (quiebres)."""
    if not reales or len(reales) != len(predichos):
        return None
    total_real = sum(reales)
    if total_real == 0:
        return None
    return (sum(predichos) - total_real) / total_real * 100.0


# =============================================================================
# Modelo para demanda intermitente: TSB
# =============================================================================

def forecast_tsb(
    valores: Sequence[float], alpha: float = 0.1, beta: float = 0.1
) -> float:
    """TSB (Teunter-Syntetos-Babai): demanda esperada por día para series
    intermitentes.

    Mantiene dos estados suavizados: probabilidad de que haya demanda un día
    dado, y tamaño de la demanda cuando ocurre. A diferencia de Croston
    clásico, TSB se actualiza también los días sin demanda, por lo que
    responde cuando un producto muere (obsolescencia).
    """
    if not valores:
        return 0.0
    # Inicialización con los primeros valores observados
    positivos = [v for v in valores if v > 0]
    if not positivos:
        return 0.0
    prob = len(positivos) / len(valores)
    tamano = positivos[0]

    for v in valores:
        if v > 0:
            prob = prob + alpha * (1 - prob)
            tamano = tamano + beta * (v - tamano)
        else:
            prob = prob + alpha * (0 - prob)
    return max(prob * tamano, 0.0)


# =============================================================================
# Modelo para demanda regular: nivel SES × estacionalidad por día de semana
# =============================================================================

def _ses(valores: Sequence[float], alpha: float = 0.2) -> float:
    """Suavizado exponencial simple: nivel actual de la serie."""
    if not valores:
        return 0.0
    nivel = valores[0]
    for v in valores[1:]:
        nivel = alpha * v + (1 - alpha) * nivel
    return max(nivel, 0.0)


def factores_dia_semana(fechas: Sequence[date], valores: Sequence[float]) -> Dict[int, float]:
    """Factor multiplicativo por día de semana (0=lunes … 6=domingo).

    factor(dow) = promedio del dow / promedio global, suavizado hacia 1.0
    cuando hay pocas observaciones de ese día (shrinkage bayesiano simple).
    """
    if not fechas or not valores:
        return {d: 1.0 for d in range(7)}
    promedio_global = sum(valores) / len(valores)
    if promedio_global <= 0:
        return {d: 1.0 for d in range(7)}

    suma_dow: Dict[int, float] = {d: 0.0 for d in range(7)}
    n_dow: Dict[int, int] = {d: 0 for d in range(7)}
    for f, v in zip(fechas, valores):
        suma_dow[f.weekday()] += v
        n_dow[f.weekday()] += 1

    # Shrinkage: con n observaciones, peso n/(n+2) al factor observado
    factores = {}
    for d in range(7):
        if n_dow[d] == 0:
            factores[d] = 1.0
            continue
        factor_crudo = (suma_dow[d] / n_dow[d]) / promedio_global
        peso = n_dow[d] / (n_dow[d] + 2)
        factores[d] = peso * factor_crudo + (1 - peso) * 1.0
    return factores


def forecast_estacional_dow(
    fechas: Sequence[date], valores: Sequence[float], fecha_objetivo: date
) -> float:
    """Pronóstico puntual para una fecha: nivel SES × factor del día de semana."""
    nivel = _ses(valores)
    factores = factores_dia_semana(fechas, valores)
    return max(nivel * factores[fecha_objetivo.weekday()], 0.0)


# =============================================================================
# Cuantiles empíricos a partir de residuos
# =============================================================================

def _cuantil(ordenados: List[float], q: float) -> float:
    """Cuantil por interpolación lineal sobre una lista YA ordenada."""
    if not ordenados:
        return 0.0
    pos = q * (len(ordenados) - 1)
    base = int(pos)
    resto = pos - base
    if base + 1 < len(ordenados):
        return ordenados[base] + resto * (ordenados[base + 1] - ordenados[base])
    return ordenados[base]


def bandas_cuantiles(
    fechas: Sequence[date], valores: Sequence[float], forecast_puntual: float
) -> Tuple[float, float]:
    """(P10, P90) diarios: forecast puntual ± cuantiles de los residuos
    in-sample del modelo estacional. Piso en 0 (no hay demanda negativa)."""
    if len(valores) < MIN_DIAS_HISTORIA:
        # Sin historia suficiente: banda ancha ±50%
        return max(forecast_puntual * 0.5, 0.0), forecast_puntual * 1.5

    residuos = []
    for i, (f, v) in enumerate(zip(fechas, valores)):
        if i < 7:  # las primeras observaciones no tienen nivel estable
            continue
        pred = forecast_estacional_dow(fechas[:i], valores[:i], f)
        residuos.append(v - pred)
    if not residuos:
        return max(forecast_puntual * 0.5, 0.0), forecast_puntual * 1.5

    residuos.sort()
    p10 = max(forecast_puntual + _cuantil(residuos, 0.10), 0.0)
    p90 = max(forecast_puntual + _cuantil(residuos, 0.90), p10)
    return p10, p90


# =============================================================================
# Interfaz principal
# =============================================================================

@dataclass
class ForecastDiario:
    fecha: date
    p10: float
    p50: float
    p90: float
    modelo: str


def generar_forecast_producto(
    ventas_por_fecha: Dict[date, float],
    fecha_desde: date,
    horizonte_dias: int = 28,
) -> List[ForecastDiario]:
    """Pronóstico probabilístico diario para un producto.

    Selecciona el modelo según el comportamiento de la serie y devuelve
    P10/P50/P90 por día del horizonte. Serie vacía → lista vacía.
    """
    fechas, valores = serie_densa(ventas_por_fecha, fecha_fin=fecha_desde - timedelta(days=1))
    if not fechas:
        return []

    salida: List[ForecastDiario] = []

    if len(valores) < MIN_DIAS_HISTORIA:
        # Historia corta: media simple con banda ancha
        media = sum(valores) / len(valores)
        for i in range(horizonte_dias):
            f = fecha_desde + timedelta(days=i)
            salida.append(
                ForecastDiario(f, max(media * 0.5, 0.0), media, media * 1.5, "media_movil")
            )
        return salida

    if es_intermitente(valores):
        tasa = forecast_tsb(valores)
        # Bandas para intermitentes: P10 = 0 (lo más probable es que no venda),
        # P90 = tamaño típico de demanda cuando ocurre
        positivos = sorted(v for v in valores if v > 0)
        p90 = _cuantil(positivos, 0.90) if positivos else tasa
        for i in range(horizonte_dias):
            f = fecha_desde + timedelta(days=i)
            salida.append(ForecastDiario(f, 0.0, tasa, max(p90, tasa), "intermitente_tsb"))
        return salida

    # Serie regular: nivel × estacionalidad dow con bandas de residuos
    for i in range(horizonte_dias):
        f = fecha_desde + timedelta(days=i)
        p50 = forecast_estacional_dow(fechas, valores, f)
        p10, p90 = bandas_cuantiles(fechas, valores, p50)
        salida.append(ForecastDiario(f, p10, p50, p90, "estacional_dow"))
    return salida


def forecast_baseline_naive(
    ventas_por_fecha: Dict[date, float], fecha_desde: date, horizonte_dias: int = 28
) -> List[float]:
    """Baseline honesto: promedio del mismo día de semana en las últimas
    4 semanas. Es el método que cualquier planilla razonable usaría; el
    modelo champion debe ganarle para justificar su existencia."""
    fechas, valores = serie_densa(ventas_por_fecha, fecha_fin=fecha_desde - timedelta(days=1))
    por_dow: Dict[int, List[float]] = {d: [] for d in range(7)}
    for f, v in zip(fechas[-28:], valores[-28:]):
        por_dow[f.weekday()].append(v)

    media_global = sum(valores[-28:]) / max(len(valores[-28:]), 1) if valores else 0.0
    salida = []
    for i in range(horizonte_dias):
        f = fecha_desde + timedelta(days=i)
        obs = por_dow.get(f.weekday(), [])
        salida.append(sum(obs) / len(obs) if obs else media_global)
    return salida

"""
Capa semántica — definición canónica y ÚNICA de las métricas del negocio.

Regla de oro (Fase 1 del Retail Intelligence OS):
    Ninguna métrica de negocio se define fuera de este módulo.
    Los servicios llaman estas funciones; el frontend nunca calcula.

Cada función documenta su fórmula. Si una definición cambia aquí,
cambia para toda la empresa a la vez (una sola versión de la verdad).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# =============================================================================
# Parámetros canónicos de operación
# =============================================================================

# Umbrales de cobertura de stock (días de venta)
DIAS_STOCK_CRITICO = 3
DIAS_STOCK_MINIMO = 7
DIAS_STOCK_OBJETIVO = 30
DIAS_STOCK_MAXIMO = 60

# Inventario sin movimiento: días sin venta para considerarlo "muerto"
DIAS_SIN_MOVIMIENTO = 30

# Nivel de servicio objetivo por clase ABC (probabilidad de no quebrar)
NIVEL_SERVICIO_OBJETIVO = {"A": 0.99, "B": 0.97, "C": 0.92}

# Lead time por defecto cuando el proveedor no tiene uno registrado (días)
LEAD_TIME_DEFAULT = 7

# Plazo de pago por defecto a proveedores (días)
DIAS_PLAZO_PAGO_DEFAULT = 30

# Tolerancia de exactitud de inventario: un conteo se considera "exacto"
# si |físico - sistema| <= max(TOLERANCIA_UNIDADES, TOLERANCIA_PCT * sistema)
TOLERANCIA_CONTEO_UNIDADES = 0
TOLERANCIA_CONTEO_PCT = 0.0

# Estados de stock canónicos (sin emojis: la presentación es del frontend)
ESTADO_CRITICO = "critico"
ESTADO_BAJO = "bajo"
ESTADO_NORMAL = "normal"
ESTADO_EXCESO = "exceso"
ESTADO_SIN_VENTA = "sin_venta"


# =============================================================================
# Ventas y margen
# =============================================================================

def venta_neta(precio_unitario: float, cantidad: float) -> float:
    """Venta neta de una línea = precio unitario × cantidad.

    Nota: el sistema actual no registra descuentos ni devoluciones por línea;
    cuando existan, se restan aquí y en ningún otro lugar.
    """
    return float(precio_unitario or 0) * float(cantidad or 0)


def margen_unitario(precio_venta: float, costo_unitario: Optional[float]) -> Optional[float]:
    """Margen unitario = precio de venta − costo unitario.

    Devuelve None si no hay costo conocido: un margen desconocido NUNCA
    se reporta como 0 ni se inventa con un factor fijo.
    """
    if costo_unitario is None:
        return None
    return float(precio_venta or 0) - float(costo_unitario)


def margen_pct(precio_venta: float, costo_unitario: Optional[float]) -> Optional[float]:
    """Margen porcentual sobre la venta = (precio − costo) / precio × 100."""
    if costo_unitario is None or not precio_venta:
        return None
    return (float(precio_venta) - float(costo_unitario)) / float(precio_venta) * 100.0


def margen_total_linea(
    precio_venta: float, costo_unitario: Optional[float], cantidad: float
) -> Optional[float]:
    """Margen total de una línea = margen unitario × cantidad."""
    mu = margen_unitario(precio_venta, costo_unitario)
    if mu is None:
        return None
    return mu * float(cantidad or 0)


# =============================================================================
# Inventario
# =============================================================================

def venta_diaria(unidades_vendidas: float, dias_periodo: int) -> float:
    """Velocidad de venta = unidades vendidas / días del período observado."""
    if not dias_periodo or dias_periodo <= 0:
        return 0.0
    return float(unidades_vendidas or 0) / dias_periodo


def dias_cobertura(stock_actual: float, venta_diaria_unidades: float) -> Optional[float]:
    """Días de cobertura = stock actual / venta diaria.

    Devuelve None cuando no hay velocidad de venta (cobertura indefinida,
    no "999"): el consumidor decide cómo tratar productos sin venta.
    """
    if not venta_diaria_unidades or venta_diaria_unidades <= 0:
        return None
    return float(stock_actual or 0) / venta_diaria_unidades


def estado_stock(dias_cob: Optional[float]) -> str:
    """Clasificación canónica del estado de stock según cobertura."""
    if dias_cob is None:
        return ESTADO_SIN_VENTA
    if dias_cob <= DIAS_STOCK_CRITICO:
        return ESTADO_CRITICO
    if dias_cob <= DIAS_STOCK_MINIMO:
        return ESTADO_BAJO
    if dias_cob <= DIAS_STOCK_MAXIMO:
        return ESTADO_NORMAL
    return ESTADO_EXCESO


def rotacion_anual(
    unidades_vendidas_periodo: float, dias_periodo: int, stock_promedio: float
) -> Optional[float]:
    """Rotación anualizada = (unidades vendidas anualizadas) / stock promedio.

    Anualiza con 365/días reales del período, no con el "×12" aproximado.
    """
    if not stock_promedio or stock_promedio <= 0 or not dias_periodo or dias_periodo <= 0:
        return None
    ventas_anualizadas = float(unidades_vendidas_periodo or 0) * (365.0 / dias_periodo)
    return ventas_anualizadas / float(stock_promedio)


def gmroi(margen_bruto_periodo: float, inventario_promedio_costo: float) -> Optional[float]:
    """GMROI = margen bruto del período / inventario promedio al costo.

    Métrica reina para decidir surtido: cuánto margen genera cada peso
    invertido en inventario.
    """
    if not inventario_promedio_costo or inventario_promedio_costo <= 0:
        return None
    return float(margen_bruto_periodo or 0) / float(inventario_promedio_costo)


def valor_inventario_costo(stock_actual: float, costo_unitario: Optional[float]) -> Optional[float]:
    """Valor del inventario AL COSTO (capital invertido), no a precio de venta."""
    if costo_unitario is None:
        return None
    return float(stock_actual or 0) * float(costo_unitario)


def punto_reorden(
    venta_diaria_unidades: float, lead_time_dias: int, stock_seguridad: float
) -> float:
    """ROP = demanda durante el lead time + stock de seguridad."""
    return float(venta_diaria_unidades or 0) * int(lead_time_dias or 0) + float(stock_seguridad or 0)


def z_nivel_servicio(nivel_servicio: float) -> float:
    """z de la normal estándar para un nivel de servicio (P de no quebrar).

    Aproximación racional de Acklam para la inversa de la CDF normal;
    error < 1.15e-9, más que suficiente para stock de seguridad.
    """
    p = min(max(float(nivel_servicio), 1e-9), 1 - 1e-9)
    # Coeficientes de Acklam
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > p_high:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1
    )


def stock_seguridad(
    nivel_servicio: float,
    lead_time_dias: float,
    sigma_demanda_diaria: float,
    demanda_diaria: float = 0.0,
    sigma_lead_time_dias: float = 0.0,
) -> float:
    """Stock de seguridad dinámico (fórmula estándar de la industria):

        SS = z × √(LT × σ²_demanda + demanda² × σ²_LT)

    Protege contra la variabilidad de la demanda Y la del lead time del
    proveedor. Con σ_LT = 0 se reduce a la fórmula clásica z×σ_d×√LT.
    """
    z = z_nivel_servicio(nivel_servicio)
    varianza = (
        float(lead_time_dias or 0) * float(sigma_demanda_diaria or 0) ** 2
        + float(demanda_diaria or 0) ** 2 * float(sigma_lead_time_dias or 0) ** 2
    )
    if varianza <= 0:
        return 0.0
    return max(z * math.sqrt(varianza), 0.0)


# =============================================================================
# Venta perdida (la métrica que financia el programa)
# =============================================================================

def venta_perdida(
    venta_diaria_unidades: float,
    dias_en_quiebre: float,
    precio_venta: float,
) -> float:
    """Venta perdida por quiebre = demanda estimada durante el quiebre × precio.

    La demanda estimada es la velocidad observada ANTES del quiebre; jamás
    se usa la venta observada durante el quiebre (demanda censurada).
    """
    return float(venta_diaria_unidades or 0) * float(dias_en_quiebre or 0) * float(precio_venta or 0)


def margen_perdido(
    venta_diaria_unidades: float,
    dias_en_quiebre: float,
    precio_venta: float,
    costo_unitario: Optional[float],
) -> Optional[float]:
    """Margen perdido por quiebre, con el margen REAL del producto.

    Si no hay costo conocido devuelve None (no se inventa un margen fijo).
    """
    mu = margen_unitario(precio_venta, costo_unitario)
    if mu is None:
        return None
    return float(venta_diaria_unidades or 0) * float(dias_en_quiebre or 0) * mu


# =============================================================================
# Exactitud de inventario (conteos cíclicos)
# =============================================================================

def conteo_es_exacto(stock_sistema: float, stock_fisico: float) -> bool:
    """Un conteo es exacto si la discrepancia está dentro de la tolerancia.

    Tolerancia = max(TOLERANCIA_CONTEO_UNIDADES, TOLERANCIA_CONTEO_PCT × sistema).
    Con los valores por defecto (0, 0.0) se exige coincidencia exacta.
    """
    tolerancia = max(
        TOLERANCIA_CONTEO_UNIDADES,
        abs(float(stock_sistema or 0)) * TOLERANCIA_CONTEO_PCT,
    )
    return abs(float(stock_fisico or 0) - float(stock_sistema or 0)) <= tolerancia


def exactitud_inventario(conteos_exactos: int, conteos_totales: int) -> Optional[float]:
    """Exactitud de inventario = % de conteos que coinciden con el sistema.

    Objetivo world-class: > 97%. Bajo 95% no se automatiza reabastecimiento.
    """
    if not conteos_totales or conteos_totales <= 0:
        return None
    return conteos_exactos / conteos_totales * 100.0


def prioridad_conteo(
    valor_inventario: Optional[float],
    discrepancia_historica_pct: float,
    dias_desde_ultimo_conteo: int,
) -> float:
    """Puntaje de priorización de conteos dirigidos (mayor = contar antes).

    Score = valor en riesgo × (1 + discrepancia histórica) × factor de antigüedad.
    Sustituye el conteo por calendario ciego: se cuenta donde hay riesgo.
    """
    valor = float(valor_inventario or 0)
    factor_discrepancia = 1.0 + max(0.0, float(discrepancia_historica_pct or 0)) / 100.0
    factor_antiguedad = 1.0 + min(float(dias_desde_ultimo_conteo or 0), 365.0) / 90.0
    return valor * factor_discrepancia * factor_antiguedad


# =============================================================================
# Merma
# =============================================================================

def merma_valor(stock_teorico: float, stock_fisico: float, costo_unitario: Optional[float]) -> Optional[float]:
    """Merma en dinero = (teórico − físico) × costo. Positiva = pérdida."""
    if costo_unitario is None:
        return None
    return (float(stock_teorico or 0) - float(stock_fisico or 0)) * float(costo_unitario)


def merma_pct_sobre_venta(merma_total_valor: float, venta_neta_periodo: float) -> Optional[float]:
    """Merma % = merma valorizada / venta neta del período × 100.

    Objetivo world-class: < 1% (élite < 0.7%).
    """
    if not venta_neta_periodo or venta_neta_periodo <= 0:
        return None
    return float(merma_total_valor or 0) / float(venta_neta_periodo) * 100.0


# =============================================================================
# Normalización de maestros
# =============================================================================

# Valores de proveedor que en realidad significan "desconocido"
PROVEEDORES_PLACEHOLDER = {"", "VARIOS", "N/A", "NA", "NINGUNO", "SIN PROVEEDOR", "-", "."}

# Valores de familia que significan "sin clasificar"
FAMILIAS_PLACEHOLDER = {"", "SIN FAMILIA", "N/A", "NA", "-", "."}


def normalizar_nombre(valor: Optional[str]) -> Optional[str]:
    """Normalización canónica de nombres de maestros: trim + colapso de
    espacios + mayúsculas. 'alberto abs ' y 'ALBERTO  ABS' son el mismo."""
    if valor is None:
        return None
    limpio = " ".join(str(valor).strip().split()).upper()
    return limpio or None


def proveedor_canonico(valor: Optional[str]) -> Optional[str]:
    """Nombre canónico de proveedor; None si es un placeholder."""
    limpio = normalizar_nombre(valor)
    if limpio is None or limpio in PROVEEDORES_PLACEHOLDER:
        return None
    return limpio


def familia_canonica(valor: Optional[str]) -> Optional[str]:
    """Nombre canónico de familia; None si es un placeholder."""
    limpio = normalizar_nombre(valor)
    if limpio is None or limpio in FAMILIAS_PLACEHOLDER:
        return None
    return limpio


# =============================================================================
# Resultado tipado para diagnósticos de calidad de datos
# =============================================================================

@dataclass
class ProblemaCalidad:
    """Un problema de calidad de datos detectado en los maestros."""
    tipo: str          # sin_costo | costo_mayor_precio | sin_familia | sin_proveedor | codigo_barras_duplicado
    entidad: str       # producto | proveedor | familia
    clave: str         # identificador del registro afectado
    detalle: str
    impacto: str       # que decisión contamina este problema

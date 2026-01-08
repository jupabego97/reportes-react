"""
Esquemas Pydantic para request/response.
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Filtros
# =============================================================================

class FilterParams(BaseModel):
    """Parámetros de filtro para queries."""
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    productos: Optional[List[str]] = None
    vendedores: Optional[List[str]] = None
    familias: Optional[List[str]] = None
    metodos: Optional[List[str]] = None
    proveedores: Optional[List[str]] = None
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None
    cantidad_min: Optional[int] = None
    cantidad_max: Optional[int] = None


class FiltrosOpciones(BaseModel):
    """Opciones disponibles para filtros."""
    productos: List[str]
    vendedores: List[str]
    familias: List[str]
    metodos: List[str]
    proveedores: List[str]
    precio_min: float
    precio_max: float
    cantidad_min: int
    cantidad_max: int
    fecha_min: date
    fecha_max: date


# =============================================================================
# Ventas
# =============================================================================

class VentaBase(BaseModel):
    """Modelo base de venta."""
    nombre: str
    precio: float
    cantidad: int
    metodo: Optional[str] = None
    vendedor: Optional[str] = None
    fecha_venta: date
    familia: Optional[str] = None
    proveedor_moda: Optional[str] = None
    precio_promedio_compra: Optional[float] = None
    
    # Campos calculados
    total_venta: float
    margen: Optional[float] = None
    margen_porcentaje: Optional[float] = None
    total_margen: Optional[float] = None


class VentaResponse(BaseModel):
    """Respuesta con lista de ventas."""
    data: List[VentaBase]
    total_registros: int


class VentaResponsePaginated(BaseModel):
    """Respuesta paginada con lista de ventas."""
    data: List[VentaBase]
    total_registros: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Dashboard
# =============================================================================

class MetricasResponse(BaseModel):
    """Métricas principales del dashboard."""
    total_ventas: float
    total_registros: int
    precio_promedio: float
    margen_promedio: float
    margen_total: float
    
    # Deltas vs período anterior
    delta_ventas: Optional[str] = None
    delta_registros: Optional[str] = None
    delta_precio: Optional[str] = None


class AlertaResponse(BaseModel):
    """Alerta del sistema."""
    tipo: str  # error, warning, info
    icono: str
    titulo: str
    detalle: str
    datos: Optional[List[dict]] = None


class TopProductoResponse(BaseModel):
    """Producto en el top."""
    nombre: str
    cantidad: int
    total_venta: float


class TopVendedorResponse(BaseModel):
    """Vendedor en el top."""
    vendedor: str
    total_venta: float
    cantidad: int


# =============================================================================
# Márgenes
# =============================================================================

class MargenProductoResponse(BaseModel):
    """Margen por producto."""
    nombre: str
    precio: float
    precio_promedio_compra: float
    cantidad: int
    margen: float
    margen_porcentaje: float
    total_margen: float
    vendedor: Optional[str] = None


class MargenResponse(BaseModel):
    """Respuesta de análisis de márgenes."""
    margen_promedio: float
    margen_total: float
    ventas_rentables: int
    ventas_no_rentables: int
    datos_scatter: List[MargenProductoResponse]
    top_margen: List[dict]
    bottom_margen: List[dict]


# =============================================================================
# Predicciones
# =============================================================================

class VentaDiariaResponse(BaseModel):
    """Venta por día."""
    fecha: date
    ventas: float
    media_movil_7d: Optional[float] = None


class PrediccionResponse(BaseModel):
    """Respuesta de predicciones."""
    venta_diaria_promedio: float
    tendencia_diaria: float
    prediccion_semanal: float
    prediccion_mensual: float
    historico: List[VentaDiariaResponse]
    predicciones: List[VentaDiariaResponse]
    predicciones_upper: List[float]
    predicciones_lower: List[float]
    ventas_por_dia_semana: List[dict]


# =============================================================================
# Análisis ABC
# =============================================================================

class ProductoABCResponse(BaseModel):
    """Producto con clasificación ABC."""
    nombre: str
    total_venta: float
    cantidad: int
    porcentaje: float
    porcentaje_acumulado: float
    clasificacion: str


class ABCResponse(BaseModel):
    """Respuesta de análisis ABC."""
    clase_a: dict  # {productos, ventas, porcentaje}
    clase_b: dict
    clase_c: dict
    productos: List[ProductoABCResponse]
    resumen: List[dict]


# =============================================================================
# Vendedores
# =============================================================================

class VendedorRankingResponse(BaseModel):
    """Vendedor en el ranking."""
    vendedor: str
    ventas_totales: float
    margen_total: float
    productos_unicos: int
    unidades: int
    ticket_promedio: float
    margen_porcentaje: float
    rendimiento: str  # Excelente, Normal, Bajo


class VendedorDetalleResponse(BaseModel):
    """Detalle de un vendedor."""
    vendedor: str
    ventas_totales: float
    productos_unicos: int
    ticket_promedio: float
    margen_porcentaje: float
    delta_vs_promedio: float
    ventas_diarias: List[dict]
    top_productos: List[dict]
    metodos_pago: List[dict]


# =============================================================================
# Compras
# =============================================================================

class SugerenciaCompraResponse(BaseModel):
    """Sugerencia de compra."""
    nombre: str
    proveedor: Optional[str]
    familia: Optional[str]
    cantidad_disponible: int
    venta_diaria: float
    dias_stock: float
    cantidad_sugerida: int
    precio_compra: Optional[float]
    costo_estimado: float
    prioridad: str  # Urgente, Alta, Media, Baja


class ResumenProveedorResponse(BaseModel):
    """Resumen de compras por proveedor."""
    proveedor: str
    productos: int
    unidades: int
    costo_total: float


class OrdenCompraResponse(BaseModel):
    """Orden de compra generada."""
    proveedor: str
    fecha: datetime
    total_productos: int
    total_unidades: int
    costo_total: float
    items: List[SugerenciaCompraResponse]


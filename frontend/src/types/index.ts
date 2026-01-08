// Tipos de filtros
export interface FilterParams {
  fecha_inicio?: string;
  fecha_fin?: string;
  productos?: string[];
  vendedores?: string[];
  familias?: string[];
  metodos?: string[];
  proveedores?: string[];
  precio_min?: number;
  precio_max?: number;
  cantidad_min?: number;
  cantidad_max?: number;
}

export interface FiltrosOpciones {
  productos: string[];
  vendedores: string[];
  familias: string[];
  metodos: string[];
  proveedores: string[];
  precio_min: number;
  precio_max: number;
  cantidad_min: number;
  cantidad_max: number;
  fecha_min: string;
  fecha_max: string;
}

// Tipos de ventas
export interface Venta {
  nombre: string;
  precio: number;
  cantidad: number;
  metodo?: string;
  vendedor?: string;
  fecha_venta: string;
  familia?: string;
  proveedor_moda?: string;
  precio_promedio_compra?: number;
  total_venta: number;
  margen?: number;
  margen_porcentaje?: number;
  total_margen?: number;
}

export interface VentaResponse {
  data: Venta[];
  total_registros: number;
}

// Dashboard
export interface Metricas {
  total_ventas: number;
  total_registros: number;
  precio_promedio: number;
  margen_promedio: number;
  margen_total: number;
  delta_ventas?: string;
  delta_registros?: string;
  delta_precio?: string;
}

export interface Alerta {
  tipo: 'error' | 'warning' | 'info';
  icono: string;
  titulo: string;
  detalle: string;
  datos?: Record<string, unknown>[];
}

export interface TopProducto {
  nombre: string;
  cantidad: number;
  total_venta: number;
}

export interface TopVendedor {
  vendedor: string;
  total_venta: number;
  cantidad: number;
}

// Márgenes
export interface MargenProducto {
  nombre: string;
  precio: number;
  precio_promedio_compra: number;
  cantidad: number;
  margen: number;
  margen_porcentaje: number;
  total_margen: number;
  vendedor?: string;
}

export interface MargenResponse {
  margen_promedio: number;
  margen_total: number;
  ventas_rentables: number;
  ventas_no_rentables: number;
  datos_scatter: MargenProducto[];
  top_margen: Record<string, unknown>[];
  bottom_margen: Record<string, unknown>[];
}

// Predicciones
export interface VentaDiaria {
  fecha: string;
  ventas: number;
  media_movil_7d?: number;
}

export interface PrediccionResponse {
  venta_diaria_promedio: number;
  tendencia_diaria: number;
  prediccion_semanal: number;
  prediccion_mensual: number;
  historico: VentaDiaria[];
  predicciones: VentaDiaria[];
  predicciones_upper: number[];
  predicciones_lower: number[];
  ventas_por_dia_semana: { dia: string; promedio: number }[];
}

// ABC
export interface ProductoABC {
  nombre: string;
  total_venta: number;
  cantidad: number;
  porcentaje: number;
  porcentaje_acumulado: number;
  clasificacion: 'A' | 'B' | 'C';
}

export interface ABCResponse {
  clase_a: { productos: number; ventas: number; porcentaje: number };
  clase_b: { productos: number; ventas: number; porcentaje: number };
  clase_c: { productos: number; ventas: number; porcentaje: number };
  productos: ProductoABC[];
  resumen: Record<string, unknown>[];
}

// Vendedores
export interface VendedorRanking {
  vendedor: string;
  ventas_totales: number;
  margen_total: number;
  productos_unicos: number;
  unidades: number;
  ticket_promedio: number;
  margen_porcentaje: number;
  rendimiento: string;
}

export interface VendedorDetalle {
  vendedor: string;
  ventas_totales: number;
  productos_unicos: number;
  ticket_promedio: number;
  margen_porcentaje: number;
  delta_vs_promedio: number;
  ventas_diarias: { fecha: string; total_venta: number }[];
  top_productos: { nombre: string; total_venta: number; cantidad: number }[];
  metodos_pago: { metodo: string; total_venta: number }[];
}

// Compras
export interface SugerenciaCompra {
  nombre: string;
  proveedor?: string;
  familia?: string;
  cantidad_disponible: number;
  venta_diaria: number;
  dias_stock: number;
  cantidad_sugerida: number;
  precio_compra?: number;
  costo_estimado: number;
  prioridad: string;
}

export interface ResumenProveedor {
  proveedor: string;
  productos: number;
  unidades: number;
  costo_total: number;
}

export interface OrdenCompra {
  proveedor: string;
  fecha: string;
  total_productos: number;
  total_unidades: number;
  costo_total: number;
  items: SugerenciaCompra[];
}

// Charts
export interface VentaPorDia {
  fecha: string;
  total_venta: number;
  cantidad: number;
}

export interface VentaPorVendedor {
  vendedor: string;
  total_venta: number;
}

export interface VentaPorFamilia {
  familia: string;
  total_venta: number;
}

export interface VentaPorMetodo {
  metodo: string;
  total_venta: number;
}


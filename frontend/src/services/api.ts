import { useAuthStore } from '../stores/useAuthStore';
import type {
  FilterParams,
  PaginationParams,
  Venta,
  VentasResponse,
  FiltrosOpciones,
  Metricas,
  MetricasSectorResponse,
  PrediccionResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const token = useAuthStore.getState().token;
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  private async doFetch(url: string, init: RequestInit): Promise<Response> {
    try {
      return await fetch(url, init);
    } catch {
      // TypeError "Failed to fetch": el servidor no respondió (apagado, URL mal
      // configurada o bloqueo CORS). Damos un mensaje accionable.
      throw new Error(
        `No se pudo conectar con el servidor (${this.baseUrl}). Verifica que el backend esté corriendo y desplegado con la última versión.`,
      );
    }
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      useAuthStore.getState().logout();
      throw new Error('Sesión expirada');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Error de conexión' }));
      throw new Error(error.detail || `Error ${response.status}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach((v) => url.searchParams.append(key, v));
          } else {
            url.searchParams.append(key, String(value));
          }
        }
      });
    }

    const response = await this.doFetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await this.doFetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: data ? JSON.stringify(data) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  async getBlob(endpoint: string, params?: Record<string, any>): Promise<Blob> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach((v) => url.searchParams.append(key, v));
          } else {
            url.searchParams.append(key, String(value));
          }
        }
      });
    }

    const response = await this.doFetch(url.toString(), {
      method: 'GET',
      headers: {
        ...this.getHeaders(),
        'Accept': 'application/octet-stream',
      },
    });

    if (!response.ok) {
      throw new Error(`Error ${response.status}`);
    }

    return response.blob();
  }
}

export const api = new ApiClient(API_BASE_URL);

// Re-export types for backward compatibility
export type { FilterParams, PaginationParams, Venta, VentasResponse, FiltrosOpciones, Metricas };

// API Functions
export const apiService = {
  // Auth
  login: (username: string, password: string) =>
    api.post<{ access_token: string; user: any }>('/api/auth/login/json', { username, password }),

  logout: () => api.post<{ message?: string }>('/api/auth/logout', {}),

  getMetricas: (filters: FilterParams) =>
    api.get<Metricas>('/api/dashboard/metricas', filters),

  getAlertas: (filters: FilterParams) =>
    api.get<any[]>('/api/dashboard/alertas', filters),

  getSaludInventario: () =>
    api.get<{ salud_porcentaje: number; top_criticos: { nombre: string; dias_cobertura?: number; estado_stock?: string }[]; total_productos: number }>('/api/dashboard/salud-inventario'),

  // Ventas
  getVentas: (filters: FilterParams & PaginationParams) =>
    api.get<VentasResponse>('/api/ventas', filters),

  getVentasPorDia: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-dia', filters),

  getVentasPorVendedor: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-vendedor', filters),

  getVentasPorFamilia: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-familia', filters),

  getVentasPorMetodo: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-metodo', filters),

  // Filtros
  getFiltrosOpciones: () => api.get<FiltrosOpciones>('/api/filtros/opciones'),

  // Márgenes
  getMargenes: (filters: FilterParams) =>
    api.get<any>('/api/margenes', filters),

  getMargenesGmroi: (filters: FilterParams) =>
    api.get<any[]>('/api/margenes/gmroi', filters),

  // Predicciones
  getPredicciones: (filters: FilterParams) =>
    api.get<PrediccionResponse>('/api/predicciones', filters),

  getPrediccionesBacktest: (filters: FilterParams, semanas: number = 4) =>
    api.get<{ semanas: number; wape_promedio: number | null; mape_promedio: number | null; detalle: any[] }>(
      '/api/predicciones/backtest',
      { ...filters, semanas },
    ),

  // ABC
  getABC: (filters: FilterParams, criterio: string = 'ventas') =>
    api.get<any>('/api/abc', { ...filters, criterio }),

  // Vendedores
  getRankingVendedores: (filters: FilterParams) =>
    api.get<any[]>('/api/vendedores', filters),

  getVendedorDetalle: (nombre: string, filters: FilterParams) =>
    api.get<any>(`/api/vendedores/${encodeURIComponent(nombre)}`, filters),

  // Compras
  getSugerenciasCompra: (filters: FilterParams) =>
    api.get<any>('/api/compras/sugerencias', filters),

  getResumenProveedoresCompra: (filters: FilterParams) =>
    api.get<any[]>('/api/compras/proveedores', filters),

  getOrdenCompraProveedor: (
    proveedor: string,
    filters: FilterParams,
    prioridadMinima?: string
  ) =>
    api.get<any>(`/api/compras/orden/${encodeURIComponent(proveedor)}`, {
      ...filters,
      prioridad_minima: prioridadMinima,
    }),

  // Insights
  getInsights: (filters: FilterParams) =>
    api.get<any>('/api/insights', filters),

  getInsightsKpis: (filters: FilterParams) =>
    api.get<Record<string, unknown>>('/api/insights/kpis', filters),

  getMetricasSector: (filters: FilterParams) =>
    api.get<MetricasSectorResponse>('/api/metricas-sector/resumen', filters),

  // Facturas proveedor
  getFacturasProveedor: (params?: { proveedor?: string; dias_plazo?: number; estado?: string }) =>
    api.get<any[]>('/api/facturas-proveedor', params),

  getFacturasProveedorResumen: (params?: { proveedor?: string; dias_plazo?: number }) =>
    api.get<any>('/api/facturas-proveedor/resumen', params),

  getProductoDetalle: (nombre: string) =>
    api.get<any>(`/api/inventario/producto/${encodeURIComponent(nombre)}`),

  getInventarioResumen: () => api.get<any>('/api/inventario/resumen'),

  getInventarioAlertas: () => api.get<any[]>('/api/inventario/alertas'),

  getInventarioAgotados: () => api.get<any>('/api/inventario/agotados'),

  getInventario: (params?: {
    estado?: string;
    familia?: string;
    proveedor?: string;
    ordenar_por?: string;
    limite?: number;
  }) => api.get<{ data: any[]; total: number }>('/api/inventario', params),

  getInventarioPorFamilia: () => api.get<any[]>('/api/inventario/por-familia'),

  getInventarioPorProveedor: () => api.get<any[]>('/api/inventario/por-proveedor'),

  getStockoutRate: () =>
    api.get<{ stockout_pct: number; activos: number; sin_stock: number }>('/api/inventario/stockout-rate'),

  // Export
  exportExcel: (filters: FilterParams) =>
    api.getBlob('/api/export/excel', filters),

  exportCSV: (filters: FilterParams) =>
    api.getBlob('/api/export/csv', filters),

  exportPDF: (filters: FilterParams) =>
    api.getBlob('/api/export/pdf', filters),

  exportOrdenCompraExcel: (proveedor: string, filters: FilterParams) =>
    api.getBlob(`/api/export/orden-compra/${encodeURIComponent(proveedor)}/excel`, filters),

  // Analista IA
  preguntarAnalista: (pregunta: string, historial?: Array<{ role: string; content: string }>) =>
    api.post<{ respuesta: string; sql: string | null; datos: Record<string, any>[] | null; error: string | null }>(
      '/api/analista/preguntar',
      { pregunta, historial },
    ),

  // Motor de decisiones (Fase 1)
  getDecisiones: (params?: { dueno?: string; estado?: string; limite?: number }) =>
    api.get<any[]>('/api/decisiones', params),

  getDecisionesResumen: () =>
    api.get<{
      pendientes: number;
      impacto_dinero_total: number;
      por_prioridad: Record<string, { pendientes: number; impacto_dinero: number }>;
    }>('/api/decisiones/resumen'),

  evaluarDecisiones: () =>
    api.post<{ decisiones_emitidas: number; errores: any[] }>('/api/decisiones/evaluar'),

  resolverDecision: (id: number, estado: 'aprobada' | 'rechazada' | 'resuelta', nota?: string) =>
    api.post<{ id: number; estado: string }>(`/api/decisiones/${id}/resolver`, { estado, nota }),

  // Maestros y calidad de datos (Fase 1)
  sincronizarMaestros: () => api.post<any>('/api/maestros/sincronizar'),
  getCalidadDatos: () => api.get<any>('/api/maestros/calidad'),
  getMaestrosResumen: () => api.get<any>('/api/maestros/resumen'),

  // Forecast (Fase 2)
  consolidarHistorial: () => api.post<any>('/api/forecast/consolidar-historial'),
  generarForecast: (horizonte_dias?: number) =>
    api.post<any>(`/api/forecast/generar${horizonte_dias ? `?horizonte_dias=${horizonte_dias}` : ''}`),
  ejecutarBacktest: (dias_holdout?: number) =>
    api.post<any>(`/api/forecast/backtest${dias_holdout ? `?dias_holdout=${dias_holdout}` : ''}`),
  getUltimoBacktest: () => api.get<any>('/api/forecast/backtest'),
  getPrecisionForecast: (dias?: number) => api.get<any>('/api/forecast/precision', { dias }),
  getVentaPerdida: (dias?: number) => api.get<any>('/api/forecast/venta-perdida', { dias }),

  // Reabastecimiento con SS dinámico (Fase 2)
  getSugerenciasReabastecimiento: (params?: {
    dias_historia?: number;
    horizonte_cobertura_dias?: number;
  }) => api.get<any[]>('/api/reabastecimiento/sugerencias', params),
  getResumenReabastecimiento: () => api.get<any>('/api/reabastecimiento/resumen'),

  // Inventario perpetuo (Fase 1)
  getExactitudInventario: (dias?: number) =>
    api.get<any>('/api/inventario-perpetuo/exactitud', { dias }),
  getPlanConteos: (limite?: number) =>
    api.get<any[]>('/api/inventario-perpetuo/plan-conteos', { limite }),
  registrarConteo: (nombre_producto: string, stock_fisico: number, motivo?: string) =>
    api.post<any>('/api/inventario-perpetuo/conteos', { nombre_producto, stock_fisico, motivo }),
  cargarStockInicial: () => api.post<any>('/api/inventario-perpetuo/carga-inicial'),

  // Órdenes de compra (Fase 3)
  generarOrdenesCompra: () => api.post<any>('/api/ordenes-compra/generar'),
  getOrdenesCompra: (params?: { estado?: string; limite?: number }) =>
    api.get<any[]>('/api/ordenes-compra', params),
  getOrdenCompraDetalle: (id: number) => api.get<any>(`/api/ordenes-compra/${id}`),
  aprobarOrdenCompra: (id: number) => api.post<any>(`/api/ordenes-compra/${id}/aprobar`),
  enviarOrdenCompra: (id: number) => api.post<any>(`/api/ordenes-compra/${id}/enviar`),
  recibirOrdenCompra: (
    id: number,
    recepciones: Array<{ producto_id: number; cantidad_recibida: number }>,
  ) => api.post<any>(`/api/ordenes-compra/${id}/recibir`, { recepciones }),
  cancelarOrdenCompra: (id: number) => api.post<any>(`/api/ordenes-compra/${id}/cancelar`),

  // Scorecard de proveedores (Fase 3)
  getScorecardProveedores: (dias?: number) =>
    api.get<any[]>('/api/scorecard-proveedores', { dias }),

  // Merma (Fase 3)
  registrarMerma: (payload: {
    nombre_producto: string;
    causa: string;
    cantidad: number;
    nota?: string;
  }) => api.post<any>('/api/merma/registrar', payload),
  getReporteMerma: (dias?: number) => api.get<any>('/api/merma/reporte', { dias }),
};

import { useAuthStore } from '../stores/useAuthStore';
import type {
  FilterParams,
  PaginationParams,
  Venta,
  VentasResponse,
  FiltrosOpciones,
  Metricas,
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

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
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

    const response = await fetch(url.toString(), {
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
};

import { useAuthStore } from '../stores/useAuthStore';
import type {
  FilterParams,
  PaginationParams,
  Venta,
  VentasResponse,
  FiltrosOpciones,
  Metricas,
  DashboardData,
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
export type { FilterParams, PaginationParams, Venta, VentasResponse, FiltrosOpciones, Metricas, DashboardData };

// API Functions
export const apiService = {
  // Auth
  login: (username: string, password: string) =>
    api.post<{ access_token: string; user: any }>('/api/auth/login/json', { username, password }),

  getMe: () => api.get<any>('/api/auth/me'),

  getMetricas: (filters: FilterParams) =>
    api.get<Metricas>('/api/dashboard/metricas', filters),

  getAlertas: (filters: FilterParams) =>
    api.get<any[]>('/api/dashboard/alertas', filters),

  getSaludInventario: () =>
    api.get<{ salud_porcentaje: number; top_criticos: { nombre: string; dias_cobertura?: number; estado_stock?: string }[]; total_productos: number }>('/api/dashboard/salud-inventario'),

  // Ventas
  getVentas: (filters: FilterParams & PaginationParams) =>
    api.get<VentasResponse>('/api/ventas', filters),

  getAllVentas: (filters: FilterParams) =>
    api.get<{ data: Venta[]; total_registros: number }>('/api/ventas/all', filters),

  getVentasPorDia: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-dia', filters),

  getVentasPorVendedor: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-vendedor', filters),

  getVentasPorFamilia: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-familia', filters),

  getVentasPorMetodo: (filters: FilterParams) =>
    api.get<any[]>('/api/ventas/por-metodo', filters),

  getTopProductosCantidad: (filters: FilterParams, limit?: number) =>
    api.get<any[]>('/api/ventas/top-productos-cantidad', { ...filters, limit }),

  // Filtros
  getFiltrosOpciones: () => api.get<FiltrosOpciones>('/api/filtros/opciones'),

  // Márgenes
  getMargenes: (filters: FilterParams) =>
    api.get<any>('/api/margenes', filters),

  // Predicciones
  getPredicciones: (filters: FilterParams) =>
    api.get<PrediccionResponse>('/api/predicciones', filters),

  // ABC
  getABC: (filters: FilterParams) =>
    api.get<any>('/api/abc', filters),

  // Vendedores
  getRankingVendedores: (filters: FilterParams) =>
    api.get<any>('/api/vendedores', filters),

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

  // Facturas proveedor
  getFacturasProveedor: (params?: { proveedor?: string; dias_plazo?: number; estado?: string }) =>
    api.get<any[]>('/api/facturas-proveedor', params),

  getFacturasProveedorResumen: (params?: { proveedor?: string; dias_plazo?: number }) =>
    api.get<any>('/api/facturas-proveedor/resumen', params),

  getProductoDetalle: (nombre: string) =>
    api.get<any>(`/api/inventario/producto/${encodeURIComponent(nombre)}`),

  // Export
  exportExcel: (filters: FilterParams) =>
    api.getBlob('/api/export/excel', filters),

  exportCSV: (filters: FilterParams) =>
    api.getBlob('/api/export/csv', filters),

  exportPDF: (filters: FilterParams) =>
    api.getBlob('/api/export/pdf', filters),
};

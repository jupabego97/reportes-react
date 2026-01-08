import { useAuthStore } from '../stores/useAuthStore';
import type { PrediccionResponse } from '../types';

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

// Types
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

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface Venta {
  nombre: string;
  precio: number;
  cantidad: number;
  metodo?: string;
  vendedor?: string;
  fecha_venta?: string;
  familia?: string;
  proveedor_moda?: string;
  precio_promedio_compra?: number;
  total_venta: number;
  margen?: number;
  margen_porcentaje?: number;
  total_margen?: number;
}

export interface VentasResponse {
  data: Venta[];
  total_registros: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FiltrosOpciones {
  productos: string[];
  vendedores: string[];
  familias: string[];
  metodos: string[];
  proveedores: string[];
  fecha_min: string;
  fecha_max: string;
  precio_min: number;
  precio_max: number;
}

export interface Metricas {
  total_ventas: number;
  total_ingresos: number;
  ticket_promedio: number;
  productos_unicos: number;
  margen_promedio: number;
  total_margen: number;
  variacion_ventas?: number;
  variacion_ingresos?: number;
}

export interface DashboardData {
  metricas: Metricas;
  alertas: any[];
  top_productos: any[];
  top_vendedores: any[];
  ventas_por_dia: any[];
  ventas_por_familia: any[];
}

// API Functions
export const apiService = {
  // Auth
  login: (username: string, password: string) =>
    api.post<{ access_token: string; user: any }>('/api/auth/login/json', { username, password }),

  getMe: () => api.get<any>('/api/auth/me'),

  // Dashboard
  getDashboard: (filters: FilterParams) =>
    api.get<DashboardData>('/api/dashboard', filters),

  getMetricas: (filters: FilterParams) =>
    api.get<Metricas>('/api/dashboard/metricas', filters),

  getAlertas: (filters: FilterParams) =>
    api.get<any[]>('/api/dashboard/alertas', filters),

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
    api.get<any>('/api/vendedores/ranking', filters),

  // Compras
  getSugerenciasCompra: (filters: FilterParams) =>
    api.get<any>('/api/compras/sugerencias', filters),

  // Export
  exportExcel: (filters: FilterParams) =>
    api.getBlob('/api/export/excel', filters),

  exportCSV: (filters: FilterParams) =>
    api.getBlob('/api/export/csv', filters),

  exportPDF: (filters: FilterParams) =>
    api.getBlob('/api/export/pdf', filters),
};

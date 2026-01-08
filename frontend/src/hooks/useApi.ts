import { useQuery, useMutation } from '@tanstack/react-query';
import { apiService } from '../services/api';
import type { FilterParams, PaginationParams } from '../services/api';
import { useFiltersStore } from '../stores/useFiltersStore';
import { toast } from 'sonner';

// Helper para convertir filtros del store al formato API
function useFilterParams(): FilterParams {
  const filters = useFiltersStore();
  return {
    fecha_inicio: filters.fechaInicio || undefined,
    fecha_fin: filters.fechaFin || undefined,
    productos: filters.productos.length > 0 ? filters.productos : undefined,
    vendedores: filters.vendedores.length > 0 ? filters.vendedores : undefined,
    familias: filters.familias.length > 0 ? filters.familias : undefined,
    metodos: filters.metodos.length > 0 ? filters.metodos : undefined,
    proveedores: filters.proveedores.length > 0 ? filters.proveedores : undefined,
    precio_min: filters.precioMin || undefined,
    precio_max: filters.precioMax || undefined,
  };
}

// Query Keys
export const queryKeys = {
  dashboard: (filters: FilterParams) => ['dashboard', filters] as const,
  metricas: (filters: FilterParams) => ['metricas', filters] as const,
  alertas: (filters: FilterParams) => ['alertas', filters] as const,
  ventas: (filters: FilterParams & PaginationParams) => ['ventas', filters] as const,
  ventasPorDia: (filters: FilterParams) => ['ventas-por-dia', filters] as const,
  ventasPorVendedor: (filters: FilterParams) => ['ventas-por-vendedor', filters] as const,
  ventasPorFamilia: (filters: FilterParams) => ['ventas-por-familia', filters] as const,
  ventasPorMetodo: (filters: FilterParams) => ['ventas-por-metodo', filters] as const,
  topProductos: (filters: FilterParams, limit?: number) => ['top-productos', filters, limit] as const,
  filtrosOpciones: ['filtros-opciones'] as const,
  margenes: (filters: FilterParams) => ['margenes', filters] as const,
  predicciones: (filters: FilterParams) => ['predicciones', filters] as const,
  abc: (filters: FilterParams) => ['abc', filters] as const,
  rankingVendedores: (filters: FilterParams) => ['ranking-vendedores', filters] as const,
  sugerenciasCompra: (filters: FilterParams) => ['sugerencias-compra', filters] as const,
};

// Dashboard Hooks
export function useDashboard() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.dashboard(filters),
    queryFn: () => apiService.getDashboard(filters),
    staleTime: 30000, // 30 segundos
  });
}

export function useMetricas() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.metricas(filters),
    queryFn: () => apiService.getMetricas(filters),
    staleTime: 30000,
  });
}

export function useAlertas() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.alertas(filters),
    queryFn: () => apiService.getAlertas(filters),
    staleTime: 60000, // 1 minuto
  });
}

// Ventas Hooks
export function useVentas(page: number = 1, pageSize: number = 50) {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.ventas({ ...filters, page, page_size: pageSize }),
    queryFn: () => apiService.getVentas({ ...filters, page, page_size: pageSize }),
    staleTime: 30000,
  });
}

export function useVentasPorDia() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.ventasPorDia(filters),
    queryFn: () => apiService.getVentasPorDia(filters),
    staleTime: 30000,
  });
}

export function useVentasPorVendedor() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.ventasPorVendedor(filters),
    queryFn: () => apiService.getVentasPorVendedor(filters),
    staleTime: 30000,
  });
}

export function useVentasPorFamilia() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.ventasPorFamilia(filters),
    queryFn: () => apiService.getVentasPorFamilia(filters),
    staleTime: 30000,
  });
}

export function useVentasPorMetodo() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.ventasPorMetodo(filters),
    queryFn: () => apiService.getVentasPorMetodo(filters),
    staleTime: 30000,
  });
}

export function useTopProductos(limit: number = 10) {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.topProductos(filters, limit),
    queryFn: () => apiService.getTopProductosCantidad(filters, limit),
    staleTime: 30000,
  });
}

// Filtros Hook
export function useFiltrosOpciones() {
  return useQuery({
    queryKey: queryKeys.filtrosOpciones,
    queryFn: () => apiService.getFiltrosOpciones(),
    staleTime: 300000, // 5 minutos
  });
}

// Análisis Hooks
export function useMargenes() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.margenes(filters),
    queryFn: () => apiService.getMargenes(filters),
    staleTime: 60000,
  });
}

export function usePredicciones() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.predicciones(filters),
    queryFn: () => apiService.getPredicciones(filters),
    staleTime: 60000,
  });
}

export function useABC() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.abc(filters),
    queryFn: () => apiService.getABC(filters),
    staleTime: 60000,
  });
}

export function useRankingVendedores() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.rankingVendedores(filters),
    queryFn: () => apiService.getRankingVendedores(filters),
    staleTime: 60000,
  });
}

export function useSugerenciasCompra() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.sugerenciasCompra(filters),
    queryFn: () => apiService.getSugerenciasCompra(filters),
    staleTime: 60000,
  });
}

// Export Hooks
export function useExportExcel() {
  const filters = useFilterParams();
  
  return useMutation({
    mutationFn: () => apiService.exportExcel(filters),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ventas_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Archivo Excel descargado');
    },
    onError: (error) => {
      toast.error(`Error al exportar: ${error.message}`);
    },
  });
}

export function useExportCSV() {
  const filters = useFilterParams();
  
  return useMutation({
    mutationFn: () => apiService.exportCSV(filters),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ventas_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Archivo CSV descargado');
    },
    onError: (error) => {
      toast.error(`Error al exportar: ${error.message}`);
    },
  });
}

export function useExportPDF() {
  const filters = useFilterParams();
  
  return useMutation({
    mutationFn: () => apiService.exportPDF(filters),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_ventas_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Reporte PDF descargado');
    },
    onError: (error) => {
      toast.error(`Error al exportar PDF: ${error.message}`);
    },
  });
}


import { useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiService } from '../services/api';
import type { FilterParams, PaginationParams } from '../services/api';
import { useFiltersStore } from '../stores/useFiltersStore';
import { toast } from 'sonner';

// Helper para convertir filtros del store al formato API (memoizado)
function useFilterParams(): FilterParams {
  const fechaInicio = useFiltersStore((s) => s.fechaInicio);
  const fechaFin = useFiltersStore((s) => s.fechaFin);
  const productos = useFiltersStore((s) => s.productos);
  const vendedores = useFiltersStore((s) => s.vendedores);
  const familias = useFiltersStore((s) => s.familias);
  const metodos = useFiltersStore((s) => s.metodos);
  const proveedores = useFiltersStore((s) => s.proveedores);
  const precioMin = useFiltersStore((s) => s.precioMin);
  const precioMax = useFiltersStore((s) => s.precioMax);

  return useMemo(
    () => ({
      fecha_inicio: fechaInicio || undefined,
      fecha_fin: fechaFin || undefined,
      productos: productos.length > 0 ? productos : undefined,
      vendedores: vendedores.length > 0 ? vendedores : undefined,
      familias: familias.length > 0 ? familias : undefined,
      metodos: metodos.length > 0 ? metodos : undefined,
      proveedores: proveedores.length > 0 ? proveedores : undefined,
      precio_min: precioMin || undefined,
      precio_max: precioMax || undefined,
    }),
    [fechaInicio, fechaFin, productos, vendedores, familias, metodos, proveedores, precioMin, precioMax]
  );
}

// Query Keys
export const queryKeys = {
  metricas: (filters: FilterParams) => ['metricas', filters] as const,
  alertas: (filters: FilterParams) => ['alertas', filters] as const,
  saludInventario: ['salud-inventario'] as const,
  ventas: (filters: FilterParams & PaginationParams) => ['ventas', filters] as const,
  ventasPorDia: (filters: FilterParams) => ['ventas-por-dia', filters] as const,
  ventasPorVendedor: (filters: FilterParams) => ['ventas-por-vendedor', filters] as const,
  ventasPorFamilia: (filters: FilterParams) => ['ventas-por-familia', filters] as const,
  ventasPorMetodo: (filters: FilterParams) => ['ventas-por-metodo', filters] as const,
  filtrosOpciones: ['filtros-opciones'] as const,
  margenes: (filters: FilterParams) => ['margenes', filters] as const,
  margenesGmroi: (filters: FilterParams) => ['margenes-gmroi', filters] as const,
  predicciones: (filters: FilterParams) => ['predicciones', filters] as const,
  prediccionesBacktest: (filters: FilterParams, semanas: number) =>
    ['predicciones-backtest', filters, semanas] as const,
  abc: (filters: FilterParams, criterio: string) => ['abc', filters, criterio] as const,
  rankingVendedores: (filters: FilterParams) => ['ranking-vendedores', filters] as const,
  vendedorDetalle: (nombre: string, filters: FilterParams) =>
    ['vendedor-detalle', nombre, filters] as const,
  sugerenciasCompra: (filters: FilterParams) => ['sugerencias-compra', filters] as const,
  resumenComprasProveedores: (filters: FilterParams) => ['resumen-compras-proveedores', filters] as const,
  insights: (filters: FilterParams) => ['insights', filters] as const,
  insightsKpis: (filters: FilterParams) => ['insights-kpis', filters] as const,
  facturasProveedor: (params?: Record<string, unknown>) => ['facturas-proveedor', params ?? {}] as const,
  facturasProveedorResumen: (params?: Record<string, unknown>) => ['facturas-proveedor-resumen', params ?? {}] as const,
  productoDetalle: (nombre: string) => ['producto-detalle', nombre] as const,
  inventarioResumen: ['inventario-resumen'] as const,
  inventarioAlertas: ['inventario-alertas'] as const,
  inventarioAgotados: ['inventario-agotados'] as const,
  inventarioLista: (estado?: string) => ['inventario', 'lista', estado ?? 'all'] as const,
  inventarioPorFamilia: ['inventario', 'por-familia'] as const,
  inventarioPorProveedor: ['inventario', 'por-proveedor'] as const,
  stockoutRate: ['inventario', 'stockout-rate'] as const,
};

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
    staleTime: 60000,
  });
}

export function useSaludInventario() {
  return useQuery({
    queryKey: queryKeys.saludInventario,
    queryFn: () => apiService.getSaludInventario(),
    staleTime: 60000,
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

export function usePrediccionesBacktest(semanas: number = 4) {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.prediccionesBacktest(filters, semanas),
    queryFn: () => apiService.getPrediccionesBacktest(filters, semanas),
    staleTime: 120000,
  });
}

export function useABC(criterio: string = 'ventas') {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.abc(filters, criterio),
    queryFn: () => apiService.getABC(filters, criterio),
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

export function useVendedorDetalle(nombre: string | undefined) {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.vendedorDetalle(nombre || '', filters),
    queryFn: () => apiService.getVendedorDetalle(nombre!, filters),
    enabled: !!nombre,
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

export function useResumenComprasProveedores() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.resumenComprasProveedores(filters),
    queryFn: () => apiService.getResumenProveedoresCompra(filters),
    staleTime: 60000,
  });
}

export function useInsights() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.insights(filters),
    queryFn: () => apiService.getInsights(filters),
    staleTime: 60000,
  });
}

export function useKpisCEO() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.insightsKpis(filters),
    queryFn: () => apiService.getInsightsKpis(filters),
    staleTime: 60000,
    refetchInterval: 120000,
  });
}

export function useFacturasProveedor(params?: { proveedor?: string; dias_plazo?: number; estado?: string }) {
  return useQuery({
    queryKey: queryKeys.facturasProveedor(params),
    queryFn: () => apiService.getFacturasProveedor(params),
    staleTime: 60000,
  });
}

export function useFacturasProveedorResumen(params?: { proveedor?: string; dias_plazo?: number }) {
  return useQuery({
    queryKey: queryKeys.facturasProveedorResumen(params),
    queryFn: () => apiService.getFacturasProveedorResumen(params),
    staleTime: 60000,
  });
}

export function useProductoDetalle(nombre: string | undefined) {
  return useQuery({
    queryKey: queryKeys.productoDetalle(nombre || ''),
    queryFn: () => apiService.getProductoDetalle(nombre!),
    enabled: !!nombre,
    staleTime: 60000,
  });
}

export function useInventarioResumen() {
  return useQuery({
    queryKey: queryKeys.inventarioResumen,
    queryFn: () => apiService.getInventarioResumen(),
    staleTime: 60000,
  });
}

export function useInventarioAlertas() {
  return useQuery({
    queryKey: queryKeys.inventarioAlertas,
    queryFn: () => apiService.getInventarioAlertas(),
    staleTime: 60000,
  });
}

export function useInventarioAgotados() {
  return useQuery({
    queryKey: queryKeys.inventarioAgotados,
    queryFn: () => apiService.getInventarioAgotados(),
    staleTime: 120000,
  });
}

export function useInventarioLista(estado?: string) {
  return useQuery({
    queryKey: queryKeys.inventarioLista(estado),
    queryFn: () =>
      apiService.getInventario({
        estado,
        limite: 200,
      }),
    staleTime: 60000,
  });
}

export function useInventarioPorFamilia() {
  return useQuery({
    queryKey: queryKeys.inventarioPorFamilia,
    queryFn: () => apiService.getInventarioPorFamilia(),
    staleTime: 120000,
  });
}

export function useInventarioPorProveedor() {
  return useQuery({
    queryKey: queryKeys.inventarioPorProveedor,
    queryFn: () => apiService.getInventarioPorProveedor(),
    staleTime: 120000,
  });
}

export function useStockoutRate() {
  return useQuery({
    queryKey: queryKeys.stockoutRate,
    queryFn: () => apiService.getStockoutRate(),
    staleTime: 120000,
  });
}

export function useMargenesGmroi() {
  const filters = useFilterParams();
  return useQuery({
    queryKey: queryKeys.margenesGmroi(filters),
    queryFn: () => apiService.getMargenesGmroi(filters),
    staleTime: 120000,
  });
}

export function useGenerarOrdenCompra() {
  const filters = useFilterParams();
  return useMutation({
    mutationFn: ({
      proveedor,
      prioridadMinima,
    }: {
      proveedor: string;
      prioridadMinima?: string;
    }) => apiService.getOrdenCompraProveedor(proveedor, filters, prioridadMinima),
    onSuccess: () => {
      toast.success('Orden de compra generada');
    },
    onError: (error) => {
      toast.error(`Error al generar orden: ${error.message}`);
    },
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


// ─── Compras V2 hooks ─────────────────────────────────────────────────────────

export function useSugerenciasV2(proveedor?: string) {
  return useQuery({
    queryKey: ['sugerencias-v2', proveedor] as const,
    queryFn: () => apiService.getSugerenciasV2(proveedor),
    staleTime: 120000,
  });
}

export function useUrgenciasProveedor() {
  return useQuery({
    queryKey: ['urgencias-proveedor'] as const,
    queryFn: () => apiService.getUrgenciasProveedor(),
    staleTime: 120000,
  });
}

export function useExportPedido() {
  return useMutation({
    mutationFn: (proveedor: string) => apiService.exportPedidoExcel(proveedor),
    onSuccess: (blob, proveedor) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pedido_${proveedor.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Pedido de ${proveedor} descargado`);
    },
    onError: (error) => {
      toast.error(`Error al exportar pedido: ${(error as Error).message}`);
    },
  });
}

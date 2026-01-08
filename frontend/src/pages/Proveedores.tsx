import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
// ResponsivePie and ResponsiveLine imports removed - not used
import { ResponsiveBar } from '@nivo/bar';
import {
  Truck,
  TrendingUp,
  Package,
  DollarSign,
  Star,
  AlertTriangle,
  Search,
  ShoppingCart,
  ArrowUpRight,
  RefreshCw
} from 'lucide-react';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { api } from '../services/api';
import { useFiltersStore } from '../stores/useFiltersStore';
import { cn } from '../lib/utils';

// Hook para obtener filtros
function useFilterParams() {
  const filters = useFiltersStore();
  return {
    fecha_inicio: filters.fechaInicio || undefined,
    fecha_fin: filters.fechaFin || undefined,
  };
}

// Colores para el ranking
const rankColors = ['🥇', '🥈', '🥉'];
const chartColors = [
  'hsl(217, 91%, 60%)',
  'hsl(142, 71%, 45%)',
  'hsl(262, 83%, 58%)',
  'hsl(25, 95%, 53%)',
  'hsl(350, 89%, 60%)',
  'hsl(47, 96%, 53%)',
  'hsl(199, 89%, 48%)',
  'hsl(339, 90%, 51%)',
];

// Format currency
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

// Componente de estrellas
const StarRating = ({ score }: { score: number }) => {
  const estrellas = Math.max(1, Math.min(5, Math.round(score / 20)));
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={cn(
            "h-4 w-4",
            i <= estrellas ? "text-yellow-500 fill-yellow-500" : "text-gray-300"
          )}
        />
      ))}
      <span className="text-sm text-muted-foreground ml-1">({score})</span>
    </div>
  );
};

export function Proveedores() {
  const navigate = useNavigate();
  const [selectedProveedor, setSelectedProveedor] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [criterio, setCriterio] = useState<'ventas' | 'margen' | 'unidades' | 'productos' | 'alertas'>('ventas');
  const [activeTab, setActiveTab] = useState('stock');
  const filters = useFilterParams();

  // Query para resumen de proveedores
  const { data: resumen, isLoading: loadingResumen } = useQuery({
    queryKey: ['proveedores-resumen', filters],
    queryFn: () => api.get<any[]>('/api/proveedores/resumen', filters),
  });

  // Query para detalle del proveedor seleccionado
  const { data: detalle, isLoading: loadingDetalle } = useQuery({
    queryKey: ['proveedor-detalle', selectedProveedor, filters],
    queryFn: () => api.get<any>(`/api/proveedores/detalle/${encodeURIComponent(selectedProveedor!)}`, filters),
    enabled: !!selectedProveedor,
  });

  // Query para stock del proveedor
  const { data: stockData, isLoading: loadingStock } = useQuery({
    queryKey: ['proveedor-stock', selectedProveedor],
    queryFn: () => api.get<any[]>(`/api/proveedores/stock/${encodeURIComponent(selectedProveedor!)}`),
    enabled: !!selectedProveedor,
  });

  // Query para score del proveedor
  const { data: scoreData } = useQuery({
    queryKey: ['proveedor-score', selectedProveedor, filters],
    queryFn: () => api.get<any>(`/api/proveedores/score/${encodeURIComponent(selectedProveedor!)}`, filters),
    enabled: !!selectedProveedor,
  });

  // Query para sugerencias de compra
  const { data: sugerencias, refetch: refetchSugerencias } = useQuery({
    queryKey: ['proveedor-sugerencias', selectedProveedor],
    queryFn: () => api.get<any>(`/api/proveedores/sugerencias-compra/${encodeURIComponent(selectedProveedor!)}`),
    enabled: !!selectedProveedor,
  });

  // Query para productos agotados (última semana y 2 semanas)
  const { data: agotados } = useQuery({
    queryKey: ['productos-agotados'],
    queryFn: () => api.get<any>('/api/inventario/agotados'),
  });

  // Estado para mostrar modal de agotados
  const [showAgotados, setShowAgotados] = useState<'semana' | '2semanas' | null>(null);

  // Filtrar proveedores por búsqueda
  const proveedoresFiltrados = resumen?.filter(p =>
    p.proveedor?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Ordenar por criterio
  const proveedoresOrdenados = [...proveedoresFiltrados].sort((a, b) => {
    switch (criterio) {
      case 'ventas': return b.total_ventas - a.total_ventas;
      case 'margen': return b.margen_total - a.margen_total;
      case 'unidades': return b.unidades_vendidas - a.unidades_vendidas;
      case 'productos': return b.productos_unicos - a.productos_unicos;
      case 'alertas': return (b.productos_criticos + b.productos_bajos) - (a.productos_criticos + a.productos_bajos);
      default: return 0;
    }
  });

  // Calcular totales
  const totales = resumen?.reduce((acc, p) => ({
    ventas: acc.ventas + (p.total_ventas || 0),
    margen: acc.margen + (p.margen_total || 0),
    unidades: acc.unidades + (p.unidades_vendidas || 0),
    productos: acc.productos + (p.productos_unicos || 0),
    criticos: acc.criticos + (p.productos_criticos || 0),
    bajos: acc.bajos + (p.productos_bajos || 0),
  }), { ventas: 0, margen: 0, unidades: 0, productos: 0, criticos: 0, bajos: 0 });

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Truck className="h-8 w-8 text-primary" />
            Análisis de Proveedores
          </h1>
          <p className="text-muted-foreground mt-1">
            Evalúa rendimiento, stock crítico y genera órdenes de compra
          </p>
        </div>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {/* Métricas Globales */}
      {loadingResumen ? (
        <div className="grid gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-5">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Truck className="h-4 w-4" />
                  Total Proveedores
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{resumen?.length || 0}</div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Ventas Totales
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">
                  {formatCurrency(totales?.ventas || 0)}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Margen Total
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={cn(
                  "text-2xl font-bold",
                  (totales?.margen || 0) >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  {formatCurrency(totales?.margen || 0)}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Alerta de productos críticos */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className={cn((totales?.criticos || 0) > 0 && "border-red-500/50")}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  Stock Crítico
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{totales?.criticos || 0}</div>
                <p className="text-xs text-muted-foreground">productos</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card className={cn((totales?.bajos || 0) > 5 && "border-orange-500/50")}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Package className="h-4 w-4 text-orange-500" />
                  Stock Bajo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">{totales?.bajos || 0}</div>
                <p className="text-xs text-muted-foreground">productos</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Productos agotados última semana */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
            <Card
              className={cn(
                "cursor-pointer hover:shadow-md transition-shadow",
                (agotados?.ultima_semana?.total || 0) > 0 && "border-purple-500/50"
              )}
              onClick={() => setShowAgotados('semana')}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-purple-500" />
                  Agotados (7 días)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-600">{agotados?.ultima_semana?.total || 0}</div>
                <p className="text-xs text-muted-foreground">click para ver</p>
              </CardContent>
            </Card>
          </motion.div>

          {/* Productos agotados últimas 2 semanas */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
            <Card
              className={cn(
                "cursor-pointer hover:shadow-md transition-shadow",
                (agotados?.ultimas_2_semanas?.total || 0) > 0 && "border-indigo-500/50"
              )}
              onClick={() => setShowAgotados('2semanas')}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Package className="h-4 w-4 text-indigo-500" />
                  Agotados (14 días)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-indigo-600">{agotados?.ultimas_2_semanas?.total || 0}</div>
                <p className="text-xs text-muted-foreground">click para ver</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}

      {/* Contenido Principal */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Lista de Proveedores */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1"
        >
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Ranking de Proveedores</span>
                <Badge variant="outline">{proveedoresOrdenados.length}</Badge>
              </CardTitle>
              <div className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar proveedor..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <div className="flex gap-1 flex-wrap">
                  {(['ventas', 'margen', 'alertas', 'productos'] as const).map((c) => (
                    <Button
                      key={c}
                      variant={criterio === c ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCriterio(c)}
                      className="text-xs"
                    >
                      {c === 'alertas' ? '⚠️ Alertas' : c.charAt(0).toUpperCase() + c.slice(1)}
                    </Button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="max-h-[500px] overflow-auto">
              {loadingResumen ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {proveedoresOrdenados.map((proveedor, index) => (
                    <motion.div
                      key={proveedor.proveedor}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.03 }}
                    >
                      <button
                        onClick={() => setSelectedProveedor(proveedor.proveedor)}
                        className={cn(
                          "w-full p-3 rounded-lg border text-left transition-all hover:shadow-md",
                          selectedProveedor === proveedor.proveedor
                            ? "border-primary bg-primary/5 shadow-md"
                            : "hover:border-primary/50"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">
                              {index < 3 ? rankColors[index] : `#${index + 1}`}
                            </span>
                            <div>
                              <div className="font-medium truncate max-w-[120px]">
                                {proveedor.proveedor}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {proveedor.productos_unicos} productos
                              </div>
                              {/* Alertas de stock */}
                              {(proveedor.productos_criticos > 0 || proveedor.productos_bajos > 0) && (
                                <div className="flex gap-1 mt-1">
                                  {proveedor.productos_criticos > 0 && (
                                    <Badge variant="destructive" className="text-[10px] px-1 py-0">
                                      🔴 {proveedor.productos_criticos}
                                    </Badge>
                                  )}
                                  {proveedor.productos_bajos > 0 && (
                                    <Badge className="bg-orange-500 text-[10px] px-1 py-0">
                                      🟠 {proveedor.productos_bajos}
                                    </Badge>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold text-primary text-sm">
                              {formatCurrency(proveedor.total_ventas)}
                            </div>
                            <div className={cn(
                              "text-xs",
                              (proveedor.margen_porcentaje_promedio || 0) >= 0
                                ? "text-green-600"
                                : "text-red-600"
                            )}>
                              {proveedor.margen_porcentaje_promedio?.toFixed(1) || 0}% margen
                            </div>
                          </div>
                        </div>
                      </button>
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Detalle del Proveedor */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2"
        >
          {!selectedProveedor ? (
            <Card className="h-full flex items-center justify-center min-h-[400px]">
              <div className="text-center text-muted-foreground">
                <Truck className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Selecciona un proveedor para ver su detalle</p>
              </div>
            </Card>
          ) : loadingDetalle ? (
            <Card className="h-full">
              <CardContent className="p-6 space-y-4">
                <Skeleton className="h-8 w-48" />
                <div className="grid grid-cols-3 gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-20" />
                  ))}
                </div>
                <Skeleton className="h-[300px]" />
              </CardContent>
            </Card>
          ) : detalle ? (
            <Card className="max-h-[85vh] overflow-auto">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Truck className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <div className="text-xl flex items-center gap-2">
                        {detalle.proveedor}
                        {/* Tendencia */}
                        {detalle.tendencia && (
                          <Badge variant="outline" className={cn(
                            detalle.tendencia.tendencia === 'creciendo' && 'border-green-500 text-green-600',
                            detalle.tendencia.tendencia === 'decreciendo' && 'border-red-500 text-red-600',
                          )}>
                            {detalle.tendencia.icono} {detalle.tendencia.cambio_porcentaje > 0 ? '+' : ''}{detalle.tendencia.cambio_porcentaje}%
                          </Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground font-normal flex items-center gap-2">
                        {detalle.metricas.productos_unicos} productos · {detalle.metricas.vendedores_activos} vendedores
                        {/* Score */}
                        {scoreData && <StarRating score={scoreData.score} />}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {detalle.alertas_stock?.criticos > 0 && (
                      <Badge variant="destructive">
                        🔴 {detalle.alertas_stock.criticos} críticos
                      </Badge>
                    )}
                    {(detalle.metricas.margen_porcentaje_promedio || 0) >= 20 ? (
                      <Badge className="bg-green-500">
                        <Star className="h-3 w-3 mr-1" /> Rentable
                      </Badge>
                    ) : (detalle.metricas.margen_porcentaje_promedio || 0) < 0 ? (
                      <Badge variant="destructive">
                        <AlertTriangle className="h-3 w-3 mr-1" /> Revisar
                      </Badge>
                    ) : null}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Métricas del Proveedor */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Ventas Totales</div>
                    <div className="text-xl font-bold text-primary">
                      {formatCurrency(detalle.metricas.total_ventas)}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Margen Total</div>
                    <div className={cn(
                      "text-xl font-bold",
                      (detalle.metricas.margen_total || 0) >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {formatCurrency(detalle.metricas.margen_total)}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Margen Promedio</div>
                    <div className={cn(
                      "text-xl font-bold",
                      (detalle.metricas.margen_porcentaje_promedio || 0) >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {detalle.metricas.margen_porcentaje_promedio?.toFixed(1) || 0}%
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Unidades Vendidas</div>
                    <div className="text-xl font-bold">
                      {detalle.metricas.unidades_vendidas?.toLocaleString()}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Precio Promedio</div>
                    <div className="text-xl font-bold">
                      {formatCurrency(detalle.metricas.precio_promedio)}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Costo Promedio</div>
                    <div className="text-xl font-bold">
                      {detalle.metricas.costo_promedio ? formatCurrency(detalle.metricas.costo_promedio) : '-'}
                    </div>
                  </div>
                </div>

                {/* Tabs con gráficos y tablas */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="stock" className="relative">
                      📦 Stock
                      {detalle.alertas_stock?.criticos > 0 && (
                        <span className="absolute -top-1 -right-1 h-4 w-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
                          {detalle.alertas_stock.criticos}
                        </span>
                      )}
                    </TabsTrigger>
                    <TabsTrigger value="compras">🛒 Compras</TabsTrigger>
                    <TabsTrigger value="productos">📊 Productos</TabsTrigger>
                    <TabsTrigger value="ventas">📈 Ventas</TabsTrigger>
                  </TabsList>

                  {/* Tab Stock */}
                  <TabsContent value="stock" className="mt-4">
                    <div className="max-h-[350px] overflow-auto">
                      {loadingStock ? (
                        <Skeleton className="h-[300px]" />
                      ) : stockData && stockData.length > 0 ? (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Estado</TableHead>
                              <TableHead>Producto</TableHead>
                              <TableHead className="text-right">Stock</TableHead>
                              <TableHead className="text-right">Venta/día</TableHead>
                              <TableHead className="text-right">Días Cob.</TableHead>
                              <TableHead className="text-right">Comprar</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {stockData.slice(0, 30).map((p: any, i: number) => (
                              <TableRow
                                key={i}
                                className="cursor-pointer hover:bg-muted/50"
                                onClick={() => navigate(`/producto/${encodeURIComponent(p.nombre)}`)}
                              >
                                <TableCell>
                                  <span className={cn(
                                    "px-2 py-1 rounded text-xs font-medium whitespace-nowrap",
                                    p.estado?.includes('Crítico') && "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
                                    p.estado?.includes('Bajo') && "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
                                    p.estado?.includes('Normal') && "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
                                    p.estado?.includes('Exceso') && "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
                                  )}>
                                    {p.estado}
                                  </span>
                                </TableCell>
                                <TableCell className="font-medium max-w-[180px] truncate">
                                  <div className="flex items-center gap-1">
                                    {p.nombre}
                                    <ArrowUpRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                                  </div>
                                </TableCell>
                                <TableCell className="text-right font-mono">
                                  <span className={cn(
                                    p.stock_actual === 0 && "text-red-600 font-bold"
                                  )}>
                                    {p.stock_actual ?? '-'}
                                  </span>
                                </TableCell>
                                <TableCell className="text-right font-mono">
                                  {p.venta_diaria?.toFixed(1) || '0'}
                                </TableCell>
                                <TableCell className="text-right font-mono">
                                  {p.dias_cobertura != null ? (
                                    <span className={cn(
                                      p.dias_cobertura <= 3 && "text-red-600 font-bold",
                                      p.dias_cobertura > 3 && p.dias_cobertura <= 7 && "text-orange-600"
                                    )}>
                                      {p.dias_cobertura.toFixed(0)}
                                    </span>
                                  ) : '∞'}
                                </TableCell>
                                <TableCell className="text-right">
                                  {p.cantidad_sugerida > 0 ? (
                                    <Badge variant="destructive" className="font-mono">
                                      +{p.cantidad_sugerida}
                                    </Badge>
                                  ) : '-'}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      ) : (
                        <div className="text-center py-8 text-muted-foreground">
                          No hay productos de este proveedor en el inventario
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  {/* Tab Compras Sugeridas */}
                  <TabsContent value="compras" className="mt-4">
                    {sugerencias?.productos?.length > 0 ? (
                      <div className="space-y-4">
                        {/* Resumen */}
                        <div className="grid grid-cols-3 gap-4">
                          <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                            <div className="text-sm text-muted-foreground">⚠️ Productos a comprar</div>
                            <div className="text-2xl font-bold text-red-600">{sugerencias.resumen.total_productos}</div>
                          </div>
                          <div className="p-4 rounded-lg bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800">
                            <div className="text-sm text-muted-foreground">Unidades totales</div>
                            <div className="text-2xl font-bold text-orange-600">{sugerencias.resumen.total_unidades}</div>
                          </div>
                          <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
                            <div className="text-sm text-muted-foreground">Inversión estimada</div>
                            <div className="text-2xl font-bold text-blue-600">{formatCurrency(sugerencias.resumen.inversion_estimada)}</div>
                          </div>
                        </div>

                        {/* Lista de productos */}
                        <div className="max-h-[250px] overflow-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Estado</TableHead>
                                <TableHead>Producto</TableHead>
                                <TableHead className="text-right">Stock</TableHead>
                                <TableHead className="text-right">Días Cob.</TableHead>
                                <TableHead className="text-right">Comprar</TableHead>
                                <TableHead className="text-right">Inversión</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {sugerencias.productos.map((p: any, i: number) => (
                                <TableRow key={i} className="hover:bg-muted/50">
                                  <TableCell>
                                    <span className={cn(
                                      "px-2 py-1 rounded text-xs font-medium whitespace-nowrap",
                                      p.estado?.includes('Crítico') && "bg-red-100 text-red-800",
                                      p.estado?.includes('Bajo') && "bg-orange-100 text-orange-800",
                                    )}>
                                      {p.estado}
                                    </span>
                                  </TableCell>
                                  <TableCell className="font-medium max-w-[150px] truncate">
                                    {p.nombre}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right font-mono",
                                    p.stock_actual === 0 && "text-red-600 font-bold"
                                  )}>
                                    {p.stock_actual}
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    <span className={cn(
                                      p.dias_cobertura != null && p.dias_cobertura <= 3 && "text-red-600 font-bold"
                                    )}>
                                      {p.dias_cobertura?.toFixed(0) || '0'}
                                    </span>
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <Badge variant="destructive" className="font-mono">
                                      +{p.cantidad_sugerida}
                                    </Badge>
                                  </TableCell>
                                  <TableCell className="text-right font-mono">
                                    {formatCurrency(p.cantidad_sugerida * (p.precio_compra || p.precio_venta * 0.7))}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>

                        <div className="flex gap-2">
                          <Button onClick={() => refetchSugerencias()} variant="outline" size="sm">
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Actualizar
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <ShoppingCart className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>✅ No hay productos que necesiten reabastecimiento</p>
                        <p className="text-sm">Todos los productos tienen stock suficiente</p>
                      </div>
                    )}
                  </TabsContent>

                  {/* Tab Productos */}
                  <TabsContent value="productos" className="mt-4">
                    <div className="max-h-[300px] overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Producto</TableHead>
                            <TableHead>Familia</TableHead>
                            <TableHead className="text-right">Cantidad</TableHead>
                            <TableHead className="text-right">Ventas</TableHead>
                            <TableHead className="text-right">Margen %</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {detalle.productos?.slice(0, 15).map((p: any, i: number) => (
                            <TableRow
                              key={i}
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => navigate(`/producto/${encodeURIComponent(p.nombre)}`)}
                            >
                              <TableCell className="font-medium max-w-[150px] truncate">
                                <div className="flex items-center gap-1">
                                  {p.nombre}
                                  <ArrowUpRight className="h-3 w-3 text-muted-foreground" />
                                </div>
                              </TableCell>
                              <TableCell>{p.familia || '-'}</TableCell>
                              <TableCell className="text-right">
                                {p.cantidad_vendida?.toLocaleString()}
                              </TableCell>
                              <TableCell className="text-right">
                                {formatCurrency(p.total_ventas)}
                              </TableCell>
                              <TableCell className="text-right">
                                <span className={cn(
                                  (p.margen_porcentaje || 0) >= 0 ? "text-green-600" : "text-red-600"
                                )}>
                                  {p.margen_porcentaje?.toFixed(1) || '-'}%
                                </span>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>

                  {/* Tab Ventas */}
                  <TabsContent value="ventas" className="mt-4">
                    <div className="h-[300px]">
                      {detalle.ventas_por_dia?.length > 0 ? (
                        <ResponsiveLine
                          data={[{
                            id: 'Ventas',
                            data: detalle.ventas_por_dia.map((d: any) => ({
                              x: d.fecha,
                              y: d.total_venta,
                            })),
                          }]}
                          margin={{ top: 20, right: 20, bottom: 50, left: 60 }}
                          xScale={{ type: 'point' }}
                          yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                          curve="monotoneX"
                          axisBottom={{
                            tickRotation: -45,
                          }}
                          axisLeft={{
                            format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                          }}
                          colors={[chartColors[0]]}
                          lineWidth={3}
                          pointSize={8}
                          pointColor={{ theme: 'background' }}
                          pointBorderWidth={2}
                          pointBorderColor={{ from: 'serieColor' }}
                          enableArea={true}
                          areaOpacity={0.15}
                          useMesh={true}
                          theme={{
                            axis: {
                              ticks: {
                                text: { fill: 'hsl(var(--muted-foreground))' },
                              },
                            },
                            grid: {
                              line: { stroke: 'hsl(var(--border))' },
                            },
                          }}
                        />
                      ) : (
                        <div className="h-full flex items-center justify-center text-muted-foreground">
                          Sin datos de ventas
                        </div>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ) : null}
        </motion.div>
      </div>

      {/* Gráfico de distribución */}
      {!loadingResumen && resumen && resumen.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Distribución de Ventas por Proveedor (Top 10)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveBar
                  data={proveedoresOrdenados.slice(0, 10).map(p => ({
                    proveedor: p.proveedor?.substring(0, 15) || 'N/A',
                    ventas: p.total_ventas,
                    margen: p.margen_total,
                  }))}
                  keys={['ventas', 'margen']}
                  indexBy="proveedor"
                  margin={{ top: 20, right: 130, bottom: 60, left: 80 }}
                  padding={0.3}
                  groupMode="grouped"
                  colors={[chartColors[0], chartColors[1]]}
                  borderRadius={4}
                  axisBottom={{
                    tickRotation: -45,
                  }}
                  axisLeft={{
                    format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                  }}
                  enableLabel={false}
                  legends={[
                    {
                      dataFrom: 'keys',
                      anchor: 'bottom-right',
                      direction: 'column',
                      translateX: 120,
                      itemWidth: 100,
                      itemHeight: 20,
                      itemTextColor: 'hsl(var(--muted-foreground))',
                      symbolSize: 12,
                      symbolShape: 'circle',
                    },
                  ]}
                  theme={{
                    axis: {
                      ticks: {
                        text: { fill: 'hsl(var(--muted-foreground))' },
                      },
                    },
                    grid: {
                      line: { stroke: 'hsl(var(--border))' },
                    },
                  }}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Modal de productos agotados */}
      {showAgotados && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowAgotados(null)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-background rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold flex items-center gap-2">
                  {showAgotados === 'semana' ? (
                    <>
                      <AlertTriangle className="h-5 w-5 text-purple-500" />
                      Productos Agotados - Última Semana
                    </>
                  ) : (
                    <>
                      <Package className="h-5 w-5 text-indigo-500" />
                      Productos Agotados - Últimas 2 Semanas
                    </>
                  )}
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {showAgotados === 'semana'
                    ? `${agotados?.ultima_semana?.total || 0} productos con stock 0 que tuvieron ventas en los últimos 7 días`
                    : `${agotados?.ultimas_2_semanas?.total || 0} productos con stock 0 que tuvieron ventas hace 8-14 días`
                  }
                </p>
              </div>
              <button
                onClick={() => setShowAgotados(null)}
                className="p-2 hover:bg-muted rounded-lg"
              >
                ✕
              </button>
            </div>

            <div className="p-6 overflow-auto max-h-[60vh]">
              {/* Resumen */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200">
                  <div className="text-sm text-muted-foreground">Total productos agotados</div>
                  <div className="text-2xl font-bold text-red-600">
                    {showAgotados === 'semana'
                      ? agotados?.ultima_semana?.total || 0
                      : agotados?.ultimas_2_semanas?.total || 0
                    }
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-orange-50 dark:bg-orange-950/30 border border-orange-200">
                  <div className="text-sm text-muted-foreground">💰 Ventas perdidas estimadas</div>
                  <div className="text-2xl font-bold text-orange-600">
                    {formatCurrency(
                      showAgotados === 'semana'
                        ? agotados?.ultima_semana?.ingresos_perdidos_estimados || 0
                        : agotados?.ultimas_2_semanas?.ingresos_perdidos_estimados || 0
                    )}
                  </div>
                </div>
              </div>

              {/* Lista de productos */}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Proveedor</TableHead>
                    <TableHead className="text-right">Última venta</TableHead>
                    <TableHead className="text-right">Venta/día</TableHead>
                    <TableHead className="text-right">Comprar</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(showAgotados === 'semana'
                    ? agotados?.ultima_semana?.productos
                    : agotados?.ultimas_2_semanas?.productos
                  )?.map((p: any, i: number) => (
                    <TableRow
                      key={i}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => {
                        setShowAgotados(null);
                        navigate(`/producto/${encodeURIComponent(p.nombre)}`);
                      }}
                    >
                      <TableCell className="font-medium max-w-[200px] truncate">
                        <div className="flex items-center gap-1">
                          {p.nombre}
                          <ArrowUpRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-[120px] truncate">
                        {p.proveedor || '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {p.ultima_venta ? new Date(p.ultima_venta).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {p.venta_diaria?.toFixed(1)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge variant="destructive" className="font-mono">
                          +{p.cantidad_sugerida}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

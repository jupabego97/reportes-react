import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShoppingCart, AlertTriangle, Package, TrendingUp, DollarSign,
  ArrowUpRight, Download, RefreshCw, X, Truck, BarChart3, Clock
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
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

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

// Hook para obtener parámetros de filtro
const useFilterParams = () => {
  const { fechaInicio, fechaFin, productos, vendedores, familias } = useFiltersStore();
  return {
    fecha_inicio: fechaInicio,
    fecha_fin: fechaFin,
    productos: productos?.join(',') || undefined,
    vendedores: vendedores?.join(',') || undefined,
    familias: familias?.join(',') || undefined,
  };
};

export function Compras() {
  const filters = useFilterParams();
  const [activeTab, setActiveTab] = useState('resumen');
  const [selectedProveedor, setSelectedProveedor] = useState<string | null>(null);
  const [showOrdenModal, setShowOrdenModal] = useState(false);

  // Query principal con resumen completo
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['compras-resumen-completo', filters],
    queryFn: () => api.get<any>('/api/compras/resumen-completo', filters),
  });

  // Query para puntos de reorden
  const { data: puntosReorden } = useQuery({
    queryKey: ['puntos-reorden', filters],
    queryFn: () => api.get<any[]>('/api/compras/puntos-reorden', filters),
  });

  // Query para orden de proveedor específico
  const { data: ordenProveedor, isLoading: loadingOrden } = useQuery({
    queryKey: ['orden-proveedor', selectedProveedor, filters],
    queryFn: () => api.get<any>(`/api/compras/orden-proveedor/${encodeURIComponent(selectedProveedor!)}`, filters),
    enabled: !!selectedProveedor && showOrdenModal,
  });

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {(error as Error).message}
      </div>
    );
  }

  const resumen = data?.resumen;
  const porPrioridad = data?.por_prioridad;
  const porProveedor = data?.por_proveedor;
  const agotados = data?.agotados;
  const sugerencias = data?.sugerencias;

  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <ShoppingCart className="h-8 w-8 text-primary" />
            Centro de Compras
          </h1>
          <p className="text-muted-foreground">
            Gestión inteligente de reposición con ROI y alertas automatizadas
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualizar
        </Button>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Skeleton className="h-[140px]" />
            <Skeleton className="h-[140px]" />
            <Skeleton className="h-[140px]" />
            <Skeleton className="h-[140px]" />
          </div>
          <Skeleton className="h-[400px]" />
        </div>
      ) : data ? (
        <>
          {/* Métricas principales con ROI */}
          <div className="grid gap-4 md:grid-cols-4">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-blue-500" />
                    Inversión Requerida
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-blue-600">
                    {formatCurrency(resumen?.inversion_total || 0)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {resumen?.total_productos || 0} productos | {resumen?.total_unidades || 0} unidades
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card className="bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-500/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-green-500" />
                    Ventas Esperadas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-600">
                    {formatCurrency(resumen?.ventas_esperadas || 0)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    ROI esperado: <span className="font-semibold text-green-600">+{resumen?.roi_esperado || 0}%</span>
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className="bg-gradient-to-br from-red-500/10 to-red-600/5 border-red-500/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                    Urgentes + Altos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-red-600">
                    {(porPrioridad?.urgentes?.count || 0) + (porPrioridad?.altas?.count || 0)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    🔴 {porPrioridad?.urgentes?.count || 0} urgentes | 🟠 {porPrioridad?.altas?.count || 0} altas
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Package className="h-4 w-4 text-purple-500" />
                    Productos Agotados
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-purple-600">
                    {(agotados?.ultima_semana?.total || 0) + (agotados?.ultimas_2_semanas?.total || 0)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Ventas perdidas: {formatCurrency((agotados?.ultima_semana?.ventas_perdidas || 0) + (agotados?.ultimas_2_semanas?.ventas_perdidas || 0))}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Tabs principales */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="resumen">📊 Resumen</TabsTrigger>
              <TabsTrigger value="proveedores">🏭 Por Proveedor</TabsTrigger>
              <TabsTrigger value="productos">📦 Productos</TabsTrigger>
              <TabsTrigger value="agotados">⚠️ Agotados</TabsTrigger>
              <TabsTrigger value="reorden">🔄 Punto Reorden</TabsTrigger>
            </TabsList>

            {/* Tab Resumen */}
            <TabsContent value="resumen" className="mt-4">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Resumen por prioridad */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" />
                      Desglose por Prioridad
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {[
                        { key: 'urgentes', label: 'Urgente', icon: '🔴', color: 'bg-red-500' },
                        { key: 'altas', label: 'Alta', icon: '🟠', color: 'bg-orange-500' },
                        { key: 'medias', label: 'Media', icon: '🟡', color: 'bg-yellow-500' },
                        { key: 'bajas', label: 'Baja', icon: '🟢', color: 'bg-green-500' },
                      ].map((item) => {
                        const prioridadData = porPrioridad?.[item.key as keyof typeof porPrioridad];
                        const count = (prioridadData as any)?.count || 0;
                        const inversion = (prioridadData as any)?.inversion || 0;
                        const total = resumen?.total_productos || 1;
                        const percentage = (count / total) * 100;

                        return (
                          <div key={item.key} className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                              <span className="flex items-center gap-2">
                                <span>{item.icon}</span>
                                <span className="font-medium">{item.label}</span>
                              </span>
                              <span className="text-muted-foreground">
                                {count} productos • {formatCurrency(inversion)}
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                              <div
                                className={cn("h-full rounded-full transition-all", item.color)}
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>

                {/* Top proveedores por urgencia */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Truck className="h-5 w-5" />
                      Proveedores Prioritarios
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 max-h-[300px] overflow-auto">
                      {porProveedor?.slice(0, 8).map((prov: any, i: number) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-3 rounded-lg bg-muted/50 cursor-pointer hover:bg-muted transition-colors"
                          onClick={() => {
                            setSelectedProveedor(prov.proveedor);
                            setShowOrdenModal(true);
                          }}
                        >
                          <div className="flex-1">
                            <div className="font-medium truncate max-w-[180px]">{prov.proveedor}</div>
                            <div className="text-xs text-muted-foreground">
                              {prov.productos} productos • {prov.unidades} unidades
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-semibold text-primary">{formatCurrency(prov.inversion)}</div>
                            <div className="flex gap-1">
                              {prov.urgentes > 0 && (
                                <Badge variant="destructive" className="text-[10px] px-1">
                                  {prov.urgentes} 🔴
                                </Badge>
                              )}
                              {prov.altas > 0 && (
                                <Badge variant="secondary" className="text-[10px] px-1">
                                  {prov.altas} 🟠
                                </Badge>
                              )}
                            </div>
                          </div>
                          <ArrowUpRight className="h-4 w-4 text-muted-foreground ml-2" />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Tab Proveedores */}
            <TabsContent value="proveedores" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Truck className="h-5 w-5" />
                    Órdenes de Compra por Proveedor
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Proveedor</TableHead>
                        <TableHead className="text-right">Productos</TableHead>
                        <TableHead className="text-right">Unidades</TableHead>
                        <TableHead className="text-right">Urgentes</TableHead>
                        <TableHead className="text-right">Inversión</TableHead>
                        <TableHead className="text-right">Acción</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {porProveedor?.map((prov: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium max-w-[200px] truncate">
                            {prov.proveedor}
                          </TableCell>
                          <TableCell className="text-right">{prov.productos}</TableCell>
                          <TableCell className="text-right">{prov.unidades}</TableCell>
                          <TableCell className="text-right">
                            {prov.urgentes > 0 && (
                              <Badge variant="destructive">{prov.urgentes}</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right font-semibold">
                            {formatCurrency(prov.inversion)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setSelectedProveedor(prov.proveedor);
                                setShowOrdenModal(true);
                              }}
                            >
                              <Download className="h-3 w-3 mr-1" />
                              Orden
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Tab Productos */}
            <TabsContent value="productos" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Package className="h-5 w-5" />
                    Todos los Productos a Comprar
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[500px] overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Prioridad</TableHead>
                          <TableHead>Producto</TableHead>
                          <TableHead>Proveedor</TableHead>
                          <TableHead className="text-right">Stock</TableHead>
                          <TableHead className="text-right">Días Stock</TableHead>
                          <TableHead className="text-right">Cantidad</TableHead>
                          <TableHead className="text-right">Inversión</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sugerencias?.map((p: any, i: number) => (
                          <TableRow key={i}>
                            <TableCell>
                              <Badge variant={
                                p.prioridad?.includes('Urgente') ? 'destructive' :
                                  p.prioridad?.includes('Alta') ? 'default' :
                                    p.prioridad?.includes('Media') ? 'secondary' : 'outline'
                              }>
                                {p.prioridad}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-medium max-w-[200px] truncate">
                              {p.nombre}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground max-w-[150px] truncate">
                              {p.proveedor || '-'}
                            </TableCell>
                            <TableCell className={cn(
                              "text-right",
                              p.cantidad_disponible === 0 && "text-red-600 font-bold"
                            )}>
                              {p.cantidad_disponible}
                            </TableCell>
                            <TableCell className="text-right">
                              <span className={cn(
                                p.dias_stock <= 3 && "text-red-600",
                                p.dias_stock > 3 && p.dias_stock <= 7 && "text-orange-600"
                              )}>
                                {p.dias_stock?.toFixed(0)}
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-bold">
                              +{p.cantidad_sugerida}
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {formatCurrency(p.costo_estimado)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Tab Agotados */}
            <TabsContent value="agotados" className="mt-4">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Última semana */}
                <Card className="border-purple-500/30">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-purple-600">
                      <Clock className="h-5 w-5" />
                      Agotados Última Semana
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {agotados?.ultima_semana?.total || 0} productos •
                      Ventas perdidas: {formatCurrency(agotados?.ultima_semana?.ventas_perdidas || 0)}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-[350px] overflow-auto space-y-2">
                      {agotados?.ultima_semana?.productos?.map((p: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-purple-50 dark:bg-purple-950/30">
                          <div className="flex-1">
                            <div className="font-medium truncate max-w-[200px]">{p.nombre}</div>
                            <div className="text-xs text-muted-foreground">{p.proveedor}</div>
                          </div>
                          <div className="text-right">
                            <Badge variant="destructive">+{p.cantidad_sugerida}</Badge>
                            <div className="text-xs text-muted-foreground">
                              {p.venta_diaria}/día
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Últimas 2 semanas */}
                <Card className="border-indigo-500/30">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-indigo-600">
                      <Clock className="h-5 w-5" />
                      Agotados Últimas 2 Semanas
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {agotados?.ultimas_2_semanas?.total || 0} productos •
                      Ventas perdidas: {formatCurrency(agotados?.ultimas_2_semanas?.ventas_perdidas || 0)}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-[350px] overflow-auto space-y-2">
                      {agotados?.ultimas_2_semanas?.productos?.map((p: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-indigo-50 dark:bg-indigo-950/30">
                          <div className="flex-1">
                            <div className="font-medium truncate max-w-[200px]">{p.nombre}</div>
                            <div className="text-xs text-muted-foreground">{p.proveedor}</div>
                          </div>
                          <div className="text-right">
                            <Badge variant="secondary">+{p.cantidad_sugerida}</Badge>
                            <div className="text-xs text-muted-foreground">
                              {p.venta_diaria}/día
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Tab Punto de Reorden */}
            <TabsContent value="reorden" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <RefreshCw className="h-5 w-5" />
                    Puntos de Reorden Automático
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Configuración: Lead time 7 días + Stock seguridad 3 días
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[500px] overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Estado</TableHead>
                          <TableHead>Producto</TableHead>
                          <TableHead>Proveedor</TableHead>
                          <TableHead className="text-right">Stock Actual</TableHead>
                          <TableHead className="text-right">Punto Reorden</TableHead>
                          <TableHead className="text-right">Stock Objetivo</TableHead>
                          <TableHead className="text-right">Pedir</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {puntosReorden?.map((p: any, i: number) => (
                          <TableRow key={i}>
                            <TableCell>
                              <Badge variant={p.estado?.includes('🔴') ? 'destructive' : 'outline'}>
                                {p.estado}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-medium max-w-[200px] truncate">
                              {p.nombre}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground max-w-[150px] truncate">
                              {p.proveedor || '-'}
                            </TableCell>
                            <TableCell className={cn(
                              "text-right font-mono",
                              p.stock_actual < p.punto_reorden && "text-red-600 font-bold"
                            )}>
                              {p.stock_actual}
                            </TableCell>
                            <TableCell className="text-right font-mono text-orange-600">
                              {p.punto_reorden}
                            </TableCell>
                            <TableCell className="text-right font-mono text-green-600">
                              {p.stock_objetivo}
                            </TableCell>
                            <TableCell className="text-right">
                              {p.cantidad_pedir > 0 ? (
                                <Badge variant="destructive">+{p.cantidad_pedir}</Badge>
                              ) : '-'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Modal de Orden de Compra por Proveedor */}
          <AnimatePresence>
            {showOrdenModal && selectedProveedor && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowOrdenModal(false)}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-background rounded-lg shadow-xl max-w-4xl w-full max-h-[85vh] overflow-hidden"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="p-6 border-b flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold flex items-center gap-2">
                        <Truck className="h-5 w-5" />
                        Orden de Compra: {selectedProveedor}
                      </h2>
                      <p className="text-sm text-muted-foreground mt-1">
                        Fecha: {ordenProveedor?.fecha_generacion}
                      </p>
                    </div>
                    <button onClick={() => setShowOrdenModal(false)} className="p-2 hover:bg-muted rounded-lg">
                      <X className="h-5 w-5" />
                    </button>
                  </div>

                  {loadingOrden ? (
                    <div className="p-6">
                      <Skeleton className="h-[300px]" />
                    </div>
                  ) : ordenProveedor && (
                    <div className="p-6 overflow-auto max-h-[65vh]">
                      {/* Resumen de la orden */}
                      <div className="grid grid-cols-4 gap-4 mb-6">
                        <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30">
                          <div className="text-sm text-muted-foreground">Productos</div>
                          <div className="text-2xl font-bold">{ordenProveedor.total_productos}</div>
                        </div>
                        <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-950/30">
                          <div className="text-sm text-muted-foreground">Unidades</div>
                          <div className="text-2xl font-bold">{ordenProveedor.total_unidades}</div>
                        </div>
                        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30">
                          <div className="text-sm text-muted-foreground">Inversión</div>
                          <div className="text-2xl font-bold text-red-600">{formatCurrency(ordenProveedor.inversion_total)}</div>
                        </div>
                        <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30">
                          <div className="text-sm text-muted-foreground">Ganancia Esperada</div>
                          <div className="text-2xl font-bold text-green-600">{formatCurrency(ordenProveedor.ganancia_esperada)}</div>
                        </div>
                      </div>

                      {/* Tabla de items */}
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Prioridad</TableHead>
                            <TableHead>Producto</TableHead>
                            <TableHead className="text-right">Stock</TableHead>
                            <TableHead className="text-right">Días</TableHead>
                            <TableHead className="text-right">Cantidad</TableHead>
                            <TableHead className="text-right">P. Unitario</TableHead>
                            <TableHead className="text-right">Subtotal</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {ordenProveedor.items?.map((item: any, i: number) => (
                            <TableRow key={i}>
                              <TableCell>
                                <Badge variant={
                                  item.prioridad?.includes('Urgente') ? 'destructive' :
                                    item.prioridad?.includes('Alta') ? 'default' : 'secondary'
                                }>
                                  {item.prioridad?.split(' ')[0]}
                                </Badge>
                              </TableCell>
                              <TableCell className="font-medium max-w-[200px] truncate">
                                {item.nombre}
                              </TableCell>
                              <TableCell className="text-right">{item.stock_actual}</TableCell>
                              <TableCell className="text-right">{item.dias_stock?.toFixed(0)}</TableCell>
                              <TableCell className="text-right font-bold">+{item.cantidad}</TableCell>
                              <TableCell className="text-right font-mono">
                                {formatCurrency(item.precio_unitario || 0)}
                              </TableCell>
                              <TableCell className="text-right font-mono font-semibold">
                                {formatCurrency(item.subtotal || 0)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>

                      {/* Total */}
                      <div className="mt-4 p-4 rounded-lg bg-muted flex items-center justify-between">
                        <span className="font-semibold">TOTAL A PAGAR:</span>
                        <span className="text-2xl font-bold text-primary">{formatCurrency(ordenProveedor.inversion_total)}</span>
                      </div>
                    </div>
                  )}
                </motion.div>
              </div>
            )}
          </AnimatePresence>
        </>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground">
              <Package className="h-12 w-12" />
              <p>No hay sugerencias de compra en este momento</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsivePie } from '@nivo/pie';
import { ResponsiveLine } from '@nivo/line';
import { 
  Truck, 
  TrendingUp, 
  Package, 
  DollarSign, 
  Star,
  AlertTriangle,
  Search
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

export function Proveedores() {
  const [selectedProveedor, setSelectedProveedor] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [criterio, setCriterio] = useState<'ventas' | 'margen' | 'unidades' | 'productos'>('ventas');
  const [activeTab, setActiveTab] = useState('ventas');
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
      default: return 0;
    }
  });

  // Calcular totales
  const totales = resumen?.reduce((acc, p) => ({
    ventas: acc.ventas + (p.total_ventas || 0),
    margen: acc.margen + (p.margen_total || 0),
    unidades: acc.unidades + (p.unidades_vendidas || 0),
    productos: acc.productos + (p.productos_unicos || 0),
  }), { ventas: 0, margen: 0, unidades: 0, productos: 0 });

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
            Evalúa el rendimiento y rentabilidad de cada proveedor
          </p>
        </div>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {/* Métricas Globales */}
      {loadingResumen ? (
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
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
                  ${totales?.ventas.toLocaleString() || 0}
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
                  ${totales?.margen.toLocaleString() || 0}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Productos Únicos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totales?.productos || 0}</div>
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
                  {(['ventas', 'margen', 'unidades', 'productos'] as const).map((c) => (
                    <Button
                      key={c}
                      variant={criterio === c ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCriterio(c)}
                      className="text-xs"
                    >
                      {c.charAt(0).toUpperCase() + c.slice(1)}
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
                              <div className="font-medium truncate max-w-[150px]">
                                {proveedor.proveedor}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {proveedor.productos_unicos} productos
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold text-primary">
                              ${proveedor.total_ventas?.toLocaleString()}
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
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Truck className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <div className="text-xl">{detalle.proveedor}</div>
                      <div className="text-sm text-muted-foreground font-normal">
                        {detalle.metricas.productos_unicos} productos · {detalle.metricas.vendedores_activos} vendedores
                      </div>
                    </div>
                  </div>
                  {(detalle.metricas.margen_porcentaje_promedio || 0) >= 20 ? (
                    <Badge className="bg-green-500">
                      <Star className="h-3 w-3 mr-1" /> Rentable
                    </Badge>
                  ) : (detalle.metricas.margen_porcentaje_promedio || 0) < 0 ? (
                    <Badge variant="destructive">
                      <AlertTriangle className="h-3 w-3 mr-1" /> Revisar
                    </Badge>
                  ) : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Métricas del Proveedor */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Ventas Totales</div>
                    <div className="text-xl font-bold text-primary">
                      ${detalle.metricas.total_ventas?.toLocaleString()}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Margen Total</div>
                    <div className={cn(
                      "text-xl font-bold",
                      (detalle.metricas.margen_total || 0) >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      ${detalle.metricas.margen_total?.toLocaleString()}
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
                      ${detalle.metricas.precio_promedio?.toLocaleString()}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Costo Promedio</div>
                    <div className="text-xl font-bold">
                      ${detalle.metricas.costo_promedio?.toLocaleString() || '-'}
                    </div>
                  </div>
                </div>

                {/* Tabs con gráficos y tablas */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="ventas">Ventas</TabsTrigger>
                    <TabsTrigger value="productos">Productos</TabsTrigger>
                    <TabsTrigger value="familias">Familias</TabsTrigger>
                  </TabsList>

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
                            <TableRow key={i}>
                              <TableCell className="font-medium max-w-[150px] truncate">
                                {p.nombre}
                              </TableCell>
                              <TableCell>{p.familia || '-'}</TableCell>
                              <TableCell className="text-right">
                                {p.cantidad_vendida?.toLocaleString()}
                              </TableCell>
                              <TableCell className="text-right">
                                ${p.total_ventas?.toLocaleString()}
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

                  <TabsContent value="familias" className="mt-4">
                    <div className="h-[300px]">
                      {detalle.ventas_por_familia?.length > 0 ? (
                        <ResponsivePie
                          data={detalle.ventas_por_familia.slice(0, 8).map((f: any, i: number) => ({
                            id: f.familia,
                            label: f.familia,
                            value: f.total_venta,
                            color: chartColors[i % chartColors.length],
                          }))}
                          margin={{ top: 20, right: 80, bottom: 20, left: 80 }}
                          innerRadius={0.5}
                          padAngle={0.7}
                          cornerRadius={3}
                          colors={{ datum: 'data.color' }}
                          borderWidth={1}
                          borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
                          arcLinkLabelsTextColor="hsl(var(--foreground))"
                          arcLinkLabelsThickness={2}
                          arcLinkLabelsColor={{ from: 'color' }}
                          arcLabelsTextColor="#ffffff"
                        />
                      ) : (
                        <div className="h-full flex items-center justify-center text-muted-foreground">
                          Sin datos de familias
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
              <CardTitle>Distribución de Ventas por Proveedor</CardTitle>
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
    </div>
  );
}



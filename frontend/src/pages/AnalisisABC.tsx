import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsivePie } from '@nivo/pie';
import { ResponsiveLine } from '@nivo/line';
import {
  Package,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Lightbulb,
  Filter
} from 'lucide-react';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { Select } from '../components/ui/select';
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

// Types
interface ProductoABC {
  nombre: string;
  categoria: string;
  total_venta: number;
  cantidad: number;
  transacciones: number;
  margen: number | null;
  margen_porcentaje: number | null;
  familia: string | null;
  proveedor: string | null;
  porcentaje: number;
  porcentaje_acumulado: number;
}

interface ResumenCategoria {
  categoria: string;
  productos: number;
  total_ventas: number;
  total_cantidad: number;
  total_margen: number | null;
  margen_promedio: number | null;
  porcentaje_productos: number;
  porcentaje_ventas: number;
  porcentaje_margen: number | null;
}

interface InsightABC {
  tipo: string;
  icono: string;
  titulo: string;
  descripcion: string;
  accion: string | null;
  categoria: string | null;
}

interface CambioCategoria {
  nombre: string;
  categoria_anterior: string;
  categoria_actual: string;
  mejora: boolean;
  icono: string;
  total_venta: number;
}

interface ABCResponse {
  productos: ProductoABC[];
  resumen: ResumenCategoria[];
  insights: InsightABC[];
  criterio_usado: string;
  totales: {
    productos: number;
    ventas: number;
    margen: number | null;
  };
}

const categoryColors = {
  A: 'hsl(142, 71%, 45%)',  // green
  B: 'hsl(47, 96%, 53%)',   // yellow
  C: 'hsl(350, 89%, 60%)',  // red
};

const categoryBgColors = {
  A: 'bg-green-100 dark:bg-green-900/30 border-green-500/50',
  B: 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-500/50',
  C: 'bg-red-100 dark:bg-red-900/30 border-red-500/50',
};

const criterioOptions = [
  { value: 'ventas', label: '💰 Por Ventas ($)' },
  { value: 'cantidad', label: '📦 Por Cantidad' },
  { value: 'margen', label: '📈 Por Margen' },
  { value: 'frecuencia', label: '🔄 Por Frecuencia' },
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

// API hooks
const useABC = (criterio: string) => {
  const filters = useFiltersStore();
  return useQuery({
    queryKey: ['abc', criterio, filters.fechaInicio, filters.fechaFin],
    queryFn: () => api.get<ABCResponse>('/api/abc', {
      criterio,
      fecha_inicio: filters.fechaInicio,
      fecha_fin: filters.fechaFin,
    }),
  });
};

const useCambiosCategoria = () => {
  const filters = useFiltersStore();
  return useQuery({
    queryKey: ['abc-cambios', filters.fechaInicio, filters.fechaFin],
    queryFn: () => api.get<CambioCategoria[]>('/api/abc/cambios', {
      fecha_inicio: filters.fechaInicio,
      fecha_fin: filters.fechaFin,
    }),
  });
};

export function AnalisisABC() {
  const navigate = useNavigate();
  const [criterio, setCriterio] = useState('ventas');
  const [filtroCategoria, setFiltroCategoria] = useState<string | null>(null);

  const { data, isLoading, error } = useABC(criterio);
  const { data: cambios } = useCambiosCategoria();

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  // Filtrar productos por categoría seleccionada
  const productosFiltrados = data?.productos?.filter(p =>
    !filtroCategoria || p.categoria === filtroCategoria
  ) || [];

  // Datos para curva de Pareto (línea + barras)
  const paretoData = data?.productos?.slice(0, 20).map((p, i) => ({
    producto: p.nombre?.substring(0, 12) || `P${i + 1}`,
    ventas: p.total_venta,
    acumulado: p.porcentaje_acumulado,
    color: categoryColors[p.categoria as keyof typeof categoryColors],
  })) || [];

  // Datos para línea de Pareto
  const lineData = [{
    id: '% Acumulado',
    data: paretoData.map(p => ({
      x: p.producto,
      y: p.acumulado,
    })),
  }];

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center md:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">📊 Análisis ABC (Pareto)</h1>
          <p className="text-muted-foreground">
            Clasificación de productos por contribución a las ventas
          </p>
        </div>

        {/* Selector de criterio */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Ordenar por:</span>
          <Select
            value={criterio}
            onChange={(e) => setCriterio(e.target.value)}
            options={criterioOptions}
            className="w-[180px]"
          />
        </div>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[400px]" />
          <Skeleton className="h-[400px]" />
        </div>
      ) : data ? (
        <>
          {/* Insights Accionables */}
          {data.insights && data.insights.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
            >
              {data.insights.map((insight, idx) => (
                <Card
                  key={idx}
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-md",
                    insight.tipo === 'success' && 'border-green-500/50 bg-green-50/50 dark:bg-green-950/20',
                    insight.tipo === 'info' && 'border-blue-500/50 bg-blue-50/50 dark:bg-blue-950/20',
                    insight.tipo === 'warning' && 'border-orange-500/50 bg-orange-50/50 dark:bg-orange-950/20',
                  )}
                  onClick={() => insight.categoria && setFiltroCategoria(insight.categoria)}
                >
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">{insight.icono}</span>
                      <div>
                        <h4 className="font-semibold text-sm">{insight.titulo}</h4>
                        <p className="text-xs text-muted-foreground mt-1">
                          {insight.descripcion}
                        </p>
                        {insight.accion && (
                          <Button
                            variant="link"
                            size="sm"
                            className="p-0 h-auto mt-2 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              insight.categoria && setFiltroCategoria(insight.categoria);
                            }}
                          >
                            {insight.accion} →
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </motion.div>
          )}

          {/* Resumen por categoría - Clickeable para filtrar */}
          <div className="grid gap-4 md:grid-cols-3">
            {data.resumen?.map((cat, index) => (
              <motion.div
                key={cat.categoria}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    "cursor-pointer transition-all hover:shadow-lg",
                    filtroCategoria === cat.categoria && "ring-2 ring-primary",
                    categoryBgColors[cat.categoria as keyof typeof categoryBgColors]
                  )}
                  onClick={() => setFiltroCategoria(
                    filtroCategoria === cat.categoria ? null : cat.categoria
                  )}
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center justify-between">
                      <Badge
                        style={{ backgroundColor: categoryColors[cat.categoria as keyof typeof categoryColors] }}
                        className="text-white text-lg px-3 py-1"
                      >
                        {cat.categoria}
                      </Badge>
                      {filtroCategoria === cat.categoria && (
                        <Filter className="h-4 w-4 text-primary" />
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Productos:</span>
                        <span className="font-bold">{cat.productos} ({cat.porcentaje_productos}%)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">% Ventas:</span>
                        <span className="font-bold">{cat.porcentaje_ventas}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total:</span>
                        <span className="font-bold">{formatCurrency(cat.total_ventas)}</span>
                      </div>
                      {cat.margen_promedio !== null && (
                        <div className="flex justify-between border-t pt-2 mt-2">
                          <span className="text-muted-foreground">Margen Prom:</span>
                          <span className={cn(
                            "font-bold",
                            cat.margen_promedio < 15 && "text-red-600",
                            cat.margen_promedio >= 25 && "text-green-600"
                          )}>
                            {cat.margen_promedio}%
                          </span>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Cambios de categoría */}
          {cambios && cambios.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <TrendingUp className="h-5 w-5" />
                    Cambios de Categoría vs Período Anterior
                  </CardTitle>
                  <CardDescription>
                    Productos que mejoraron o empeoraron su clasificación
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {cambios.slice(0, 10).map((cambio, idx) => (
                      <Badge
                        key={idx}
                        variant="outline"
                        className={cn(
                          "cursor-pointer text-sm py-1",
                          cambio.mejora
                            ? "border-green-500 bg-green-50 dark:bg-green-950/30"
                            : "border-red-500 bg-red-50 dark:bg-red-950/30"
                        )}
                        onClick={() => navigate(`/producto/${encodeURIComponent(cambio.nombre)}`)}
                      >
                        {cambio.icono} {cambio.nombre.substring(0, 20)}
                        <span className="ml-1 opacity-70">
                          {cambio.categoria_anterior}→{cambio.categoria_actual}
                        </span>
                      </Badge>
                    ))}
                    {cambios.length > 10 && (
                      <Badge variant="secondary">+{cambios.length - 10} más</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Gráficos */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Distribución por categoría */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Distribución de Ventas por Categoría</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    {data.resumen && data.resumen.length > 0 ? (
                      <ResponsivePie
                        data={data.resumen.map((r) => ({
                          id: `Cat. ${r.categoria}`,
                          label: `${r.categoria}`,
                          value: r.total_ventas,
                          color: categoryColors[r.categoria as keyof typeof categoryColors],
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
                        tooltip={({ datum }) => (
                          <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                            <div className="font-medium">{datum.id}</div>
                            <div className="text-primary font-bold">
                              {formatCurrency(Number(datum.value))}
                            </div>
                          </div>
                        )}
                      />
                    ) : (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        Sin datos
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Curva de Pareto con línea */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Curva de Pareto (Top 20)</CardTitle>
                  <CardDescription>Barras = Ventas | Línea = % Acumulado</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px] relative">
                    {paretoData.length > 0 ? (
                      <>
                        {/* Barras */}
                        <ResponsiveBar
                          data={paretoData}
                          keys={['ventas']}
                          indexBy="producto"
                          margin={{ top: 20, right: 50, bottom: 80, left: 60 }}
                          padding={0.3}
                          colors={({ data }) => data.color}
                          borderRadius={2}
                          axisBottom={{
                            tickSize: 5,
                            tickPadding: 5,
                            tickRotation: -45,
                          }}
                          axisLeft={{
                            tickSize: 5,
                            tickPadding: 5,
                            format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                          }}
                          enableLabel={false}
                          tooltip={({ indexValue, value, data }) => (
                            <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                              <div className="font-medium">{indexValue}</div>
                              <div className="text-primary font-bold">
                                {formatCurrency(Number(value))}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                Acumulado: {data.acumulado?.toFixed(1)}%
                              </div>
                            </div>
                          )}
                          theme={{
                            axis: {
                              ticks: {
                                text: {
                                  fill: 'hsl(var(--muted-foreground))',
                                  fontSize: 10,
                                },
                              },
                            },
                            grid: {
                              line: {
                                stroke: 'hsl(var(--border))',
                              },
                            },
                          }}
                          layers={[
                            'grid',
                            'axes',
                            'bars',
                            // Línea del 80%
                            ({ bars, yScale }) => {
                              const y80 = yScale(80 as never);
                              return (
                                <line
                                  x1={0}
                                  x2="100%"
                                  y1={y80}
                                  y2={y80}
                                  stroke="hsl(var(--destructive))"
                                  strokeDasharray="4 4"
                                  strokeWidth={2}
                                  opacity={0.5}
                                />
                              );
                            },
                            'markers',
                            'legends',
                            'annotations',
                          ]}
                        />
                      </>
                    ) : (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        Sin datos
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Limpiar filtro */}
          {filtroCategoria && (
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-sm">
                Mostrando solo Categoría {filtroCategoria}
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFiltroCategoria(null)}
              >
                Limpiar filtro ✕
              </Button>
            </div>
          )}

          {/* Tabla de productos */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5" />
                  Detalle de Productos
                  <Badge variant="secondary" className="ml-2">
                    {productosFiltrados.length} productos
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead>Cat.</TableHead>
                        <TableHead>Familia</TableHead>
                        <TableHead className="text-right">Cantidad</TableHead>
                        <TableHead className="text-right">Total Ventas</TableHead>
                        <TableHead className="text-right">Margen</TableHead>
                        <TableHead className="text-right">% Total</TableHead>
                        <TableHead className="text-right">% Acum.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {productosFiltrados.slice(0, 30).map((producto, index) => (
                        <TableRow
                          key={index}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/producto/${encodeURIComponent(producto.nombre)}`)}
                        >
                          <TableCell className="font-medium max-w-[200px]">
                            <div className="flex items-center gap-2">
                              <span className="truncate">{producto.nombre}</span>
                              <ArrowUpRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge
                              style={{ backgroundColor: categoryColors[producto.categoria as keyof typeof categoryColors] }}
                              className="text-white"
                            >
                              {producto.categoria}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {producto.familia || '-'}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {producto.cantidad?.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {formatCurrency(producto.total_venta)}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            <span className={cn(
                              producto.margen_porcentaje !== null && producto.margen_porcentaje < 10 && "text-red-600",
                              producto.margen_porcentaje !== null && producto.margen_porcentaje >= 25 && "text-green-600"
                            )}>
                              {producto.margen_porcentaje?.toFixed(1) || '-'}%
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {producto.porcentaje?.toFixed(2)}%
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {producto.porcentaje_acumulado?.toFixed(1)}%
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {productosFiltrados.length > 30 && (
                    <div className="text-center py-4 text-muted-foreground">
                      Mostrando 30 de {productosFiltrados.length} productos
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </>
      ) : null}
    </div>
  );
}

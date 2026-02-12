import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { TrendingUp, TrendingDown, AlertTriangle, Info, Download } from 'lucide-react';
import { toast } from 'sonner';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { useMargenes } from '../hooks/useApi';
import { cn, exportToCSV } from '../lib/utils';
import { MetricTooltip } from '../components/ui/metric-tooltip';
import { ProductLink } from '../components/ProductLink';

export function Margenes() {
  const { data, isLoading, error } = useMargenes();

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Análisis de Márgenes</h1>
        <p className="text-muted-foreground">
          Rentabilidad por producto y familia
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[400px]" />
          <Skeleton className="h-[400px]" />
        </div>
      ) : data?.sin_datos_costo ? (
        /* Mensaje cuando no hay datos de costo */
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="border-yellow-500/50">
            <CardContent className="py-12">
              <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground">
                <Info className="h-12 w-12 text-yellow-500" />
                <h3 className="text-lg font-semibold text-foreground">Sin datos de costo disponibles</h3>
                <p className="text-center max-w-md">
                  No se encontraron precios de compra en el período seleccionado.
                  Para calcular márgenes, es necesario que los productos tengan un precio promedio de compra registrado.
                </p>
                <p className="text-xs text-center max-w-md">
                  Intenta ampliar el rango de fechas o verificar que los proveedores tengan precios de compra actualizados.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ) : data ? (
        <>
          {/* Resumen de márgenes */}
          <div className="grid gap-4 md:grid-cols-4">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    Margen Promedio
                    <MetricTooltip text="Margen = precio_venta - precio_compra. Margen promedio es el promedio ponderado por unidades vendidas." />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold">${data.margen_promedio?.toFixed(2) || 0}</span>
                    {(data.margen_promedio || 0) > 0 ? (
                      <TrendingUp className="h-5 w-5 text-green-500" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    Total Margen Generado
                    <MetricTooltip text="Margen total = suma de (margen unitario x cantidad vendida) para todos los productos del periodo." />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={cn("text-2xl font-bold", (data.margen_total || 0) >= 0 ? "text-green-600" : "text-red-600")}>
                    ${data.margen_total?.toLocaleString() || 0}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Ventas con Margen Analizado</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${(data.ventas_con_margen_total || 0).toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    % Margen global:{' '}
                    <span className={cn(
                      'font-semibold',
                      data.ventas_con_margen_total > 0 && data.margen_total / data.ventas_con_margen_total * 100 > 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {data.ventas_con_margen_total > 0 ? ((data.margen_total / data.ventas_con_margen_total) * 100).toFixed(1) : 0}%
                    </span>
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Rentables / No Rentables</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-green-600">{data.ventas_rentables || 0}</span>
                    <span className="text-muted-foreground">/</span>
                    <span className="text-2xl font-bold text-red-600">{data.ventas_no_rentables || 0}</span>
                    {(data.ventas_no_rentables || 0) > 0 && <AlertTriangle className="h-5 w-5 text-red-500" />}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Márgenes por familia */}
          {data.margenes_por_familia && data.margenes_por_familia.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <Card>
                <CardHeader>
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <CardTitle>Margenes por Familia</CardTitle>
                    <Button variant="outline" size="sm" onClick={() => {
                      const headers = ['Familia', 'Ventas Totales', 'Margen Total', '% Margen', 'Cantidad'];
                      const rows = (data.margenes_por_familia || []).map((f: any) => [
                        f.familia || '',
                        String(f.ventas_totales || 0),
                        String(f.margen_total || 0),
                        String((f.margen_porcentaje || 0).toFixed(1)),
                        String(f.cantidad_total || 0),
                      ]);
                      exportToCSV(headers, rows, `margenes_familia_${new Date().toISOString().slice(0, 10)}.csv`);
                      toast.success('Margenes por familia exportados como CSV');
                    }}>
                      <Download className="h-4 w-4 mr-1" /> CSV
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Familia</TableHead>
                        <TableHead className="text-right">Ventas Totales</TableHead>
                        <TableHead className="text-right">Margen Total</TableHead>
                        <TableHead className="text-right">% Margen</TableHead>
                        <TableHead className="text-right">Cantidad</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.margenes_por_familia.map((f: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{f.familia}</TableCell>
                          <TableCell className="text-right">${Number(f.ventas_totales || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-right">
                            <span className={cn((f.margen_total || 0) >= 0 ? 'text-green-600' : 'text-red-600', 'font-semibold')}>
                              ${Number(f.margen_total || 0).toLocaleString()}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge variant={(f.margen_porcentaje || 0) >= 0 ? 'secondary' : 'destructive'}>
                              {(f.margen_porcentaje || 0).toFixed(1)}%
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">{Number(f.cantidad_total || 0).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Gráfico de Top Márgenes */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                  Top 10 Productos por Margen
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px]">
                  {data.top_margen && data.top_margen.length > 0 ? (
                    <ResponsiveBar
                      data={data.top_margen.map((p: any) => ({
                        producto: p.nombre?.substring(0, 20) || 'N/A',
                        margen: p.total_margen,
                        color: p.total_margen >= 0 ? 'hsl(142, 71%, 45%)' : 'hsl(350, 89%, 60%)',
                      }))}
                      keys={['margen']}
                      indexBy="producto"
                      margin={{ top: 20, right: 20, bottom: 80, left: 80 }}
                      padding={0.3}
                      layout="horizontal"
                      valueScale={{ type: 'linear' }}
                      colors={({ data }) => String(data.color)}
                      borderRadius={4}
                      axisBottom={{
                        tickSize: 5,
                        tickPadding: 5,
                        format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                      }}
                      axisLeft={{
                        tickSize: 5,
                        tickPadding: 5,
                        tickRotation: 0,
                      }}
                      enableLabel={true}
                      label={(d) => `$${Number(d.value).toLocaleString()}`}
                      labelTextColor="#ffffff"
                      labelSkipWidth={60}
                      tooltip={({ indexValue, value }) => (
                        <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                          <div className="font-medium">{indexValue}</div>
                          <div className={cn('font-bold', Number(value) >= 0 ? 'text-green-600' : 'text-red-600')}>
                            ${Number(value).toLocaleString()}
                          </div>
                        </div>
                      )}
                      theme={{
                        axis: {
                          ticks: {
                            text: {
                              fill: 'hsl(var(--muted-foreground))',
                              fontSize: 11,
                            },
                          },
                        },
                        grid: {
                          line: {
                            stroke: 'hsl(var(--border))',
                          },
                        },
                      }}
                    />
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      Sin datos disponibles
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Tabla de productos con peor margen */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  Productos con Peor Margen
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead className="text-right">Margen Unitario</TableHead>
                      <TableHead className="text-right">Margen Total</TableHead>
                      <TableHead className="text-right">Cantidad</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.bottom_margen?.slice(0, 10).map((producto: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell className="max-w-[200px]"><ProductLink nombre={producto.nombre} className="truncate block" /></TableCell>
                        <TableCell className="text-right">
                          <span className={cn((producto.margen || 0) < 0 ? 'text-red-600' : 'text-green-600')}>
                            ${producto.margen?.toFixed(2) || 0}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant={(producto.total_margen || 0) < 0 ? 'destructive' : 'secondary'}>
                            ${producto.total_margen?.toLocaleString() || 0}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{producto.cantidad?.toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </motion.div>
        </>
      ) : null}
    </div>
  );
}

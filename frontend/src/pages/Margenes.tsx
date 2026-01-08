import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
import { cn } from '../lib/utils';

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
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
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
      ) : data ? (
        <>
          {/* Resumen de márgenes */}
          <div className="grid gap-4 md:grid-cols-3">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Margen Promedio
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold">
                      ${data.margen_promedio?.toFixed(2) || 0}
                    </span>
                    {(data.margen_promedio || 0) > 0 ? (
                      <TrendingUp className="h-5 w-5 text-green-500" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Total Margen Generado
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={cn(
                    "text-2xl font-bold",
                    (data.margen_total || 0) >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    ${data.margen_total?.toLocaleString() || 0}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Ventas Rentables / No Rentables
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-green-600">
                      {data.ventas_rentables || 0}
                    </span>
                    <span className="text-muted-foreground">/</span>
                    <span className="text-2xl font-bold text-red-600">
                      {data.ventas_no_rentables || 0}
                    </span>
                    {(data.ventas_no_rentables || 0) > 0 && (
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Gráfico de Top Márgenes */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
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
                      colors={({ data }) => data.color}
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
                          <div className={cn(
                            'font-bold',
                            Number(value) >= 0 ? 'text-green-600' : 'text-red-600'
                          )}>
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
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
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
                        <TableCell className="font-medium max-w-[200px] truncate">
                          {producto.nombre}
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={cn(
                            (producto.margen || 0) < 0 ? 'text-red-600' : 'text-green-600'
                          )}>
                            ${producto.margen?.toFixed(2) || 0}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant={(producto.total_margen || 0) < 0 ? 'destructive' : 'secondary'}
                          >
                            ${producto.total_margen?.toLocaleString() || 0}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {producto.cantidad?.toLocaleString()}
                        </TableCell>
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

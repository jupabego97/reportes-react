import { useParams, Link } from 'react-router-dom';
import { buttonVariants } from '../components/ui/button';
import { motion } from 'framer-motion';
import { ResponsiveLine } from '@nivo/line';
import {
  Package,
  TrendingUp,
  TrendingDown,
  Minus,
  ShoppingCart,
  ArrowLeft,
  BarChart3,
} from 'lucide-react';
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
import { useProductoDetalle } from '../hooks/useApi';
import { formatCurrency, formatNumber } from '../lib/utils';
import { cn } from '../lib/utils';

export function ProductoDetalle() {
  const { nombre } = useParams<{ nombre: string }>();
  const { data, isLoading, error } = useProductoDetalle(nombre);

  if (!nombre) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Producto no especificado</p>
        <Link to="/" className={cn(buttonVariants({ variant: 'link' }), 'mt-2')}>
          Volver al inicio
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">Error: {error.message}</p>
        <Link to="/" className={cn(buttonVariants({ variant: 'link' }), 'mt-2')}>
          Volver al inicio
        </Link>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
        <Skeleton className="h-[350px]" />
      </div>
    );
  }

  const tendenciaIcon =
    (data.tendencia ?? 0) > 5 ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : (data.tendencia ?? 0) < -5 ? (
      <TrendingDown className="h-4 w-4 text-red-600" />
    ) : (
      <Minus className="h-4 w-4 text-muted-foreground" />
    );

  // Datos para grafico de linea (historial invertido para fechas ascendentes)
  const chartData = (data.historial_ventas || [])
    .slice()
    .reverse()
    .map((v: any) => ({
      x: v.fecha_venta || v.fecha || '',
      y: Number(v.cantidad || 0),
    }));

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to="/"
          className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'mb-2 inline-flex items-center gap-1')}
        >
          <ArrowLeft className="h-4 w-4" /> Volver
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight truncate">{data.nombre}</h1>
          {data.clasificacion_abc && (
            <Badge variant={data.clasificacion_abc === 'A' ? 'default' : data.clasificacion_abc === 'B' ? 'secondary' : 'outline'}>
              ABC {data.clasificacion_abc}
            </Badge>
          )}
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            {tendenciaIcon}
            <span>{data.tendencia_label || 'Estable'}</span>
          </div>
          {data.familia && (
            <Badge variant="outline">{data.familia}</Badge>
          )}
          {data.proveedor && (
            <span className="text-sm text-muted-foreground">Proveedor: {data.proveedor}</span>
          )}
        </div>
      </motion.div>

      {/* Cards metricas */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Package className="h-4 w-4" /> Stock actual
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(data.stock_actual ?? 0)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Dias de cobertura</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={cn(
                'text-2xl font-bold',
                (data.dias_cobertura ?? 999) <= 7 && 'text-red-600',
                (data.dias_cobertura ?? 0) > 7 && (data.dias_cobertura ?? 0) <= 14 && 'text-amber-600'
              )}
            >
              {data.dias_cobertura != null ? data.dias_cobertura.toFixed(1) : '-'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Venta diaria</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(data.venta_diaria ?? 0)}</div>
            <p className="text-xs text-muted-foreground">ultimos 30 dias</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Margen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {data.margen_porcentaje != null ? `${data.margen_porcentaje.toFixed(1)}%` : '-'}
            </div>
            <p className="text-xs text-muted-foreground">
              Venta: {formatCurrency(data.precio_venta ?? 0)} | Compra: {data.precio_compra_promedio != null ? formatCurrency(data.precio_compra_promedio) : '-'}
            </p>
          </CardContent>
        </Card>
      </div>

      {data.fill_rate_estimado != null && (
        <Card>
          <CardContent className="py-3">
            <span className="text-sm text-muted-foreground">Fill rate estimado: </span>
            <span className="font-semibold">{data.fill_rate_estimado}%</span>
          </CardContent>
        </Card>
      )}

      {/* Grafico historial ventas */}
      {chartData.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" /> Comportamiento de ventas en el tiempo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveLine
                  data={[{ id: 'cantidad', data: chartData, color: 'hsl(var(--primary))' }]}
                  margin={{ top: 20, right: 30, bottom: 60, left: 50 }}
                  xScale={{ type: 'point' }}
                  yScale={{ type: 'linear', min: 0, max: 'auto' }}
                  curve="monotoneX"
                  axisTop={null}
                  axisRight={null}
                  axisBottom={{
                    tickSize: 5,
                    tickPadding: 10,
                    tickRotation: -45,
                    format: (v) => String(v).slice(0, 10),
                  }}
                  axisLeft={{
                    tickSize: 5,
                    tickPadding: 5,
                  }}
                  enableGridX={false}
                  enableGridY={true}
                  colors={['hsl(var(--primary))']}
                  lineWidth={2}
                  pointSize={6}
                  pointColor="hsl(var(--primary))"
                  pointBorderWidth={2}
                  pointBorderColor="#fff"
                  enableArea={true}
                  areaOpacity={0.2}
                  useMesh={true}
                  theme={{
                    axis: { ticks: { text: { fill: 'hsl(var(--muted-foreground))', fontSize: 11 } } },
                    grid: { line: { stroke: 'hsl(var(--border))' } },
                  }}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Tabla historial */}
      {data.historial_ventas && data.historial_ventas.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Historial de ventas diarias</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Total venta</TableHead>
                  <TableHead>Vendedores</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data.historial_ventas as any[]).slice(0, 30).map((v: any, i: number) => (
                  <TableRow key={i}>
                    <TableCell>{v.fecha_venta || v.fecha}</TableCell>
                    <TableCell className="text-right">{formatNumber(v.cantidad ?? 0)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(v.total_venta ?? 0)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{v.vendedores || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Sugerencia de compra */}
      {data.sugerencia_compra && (data.dias_cobertura == null || data.dias_cobertura < 14) && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="border-primary/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <ShoppingCart className="h-5 w-5" /> Sugerencia de compra
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Cantidad sugerida: </span>
                  <span className="font-bold">{formatNumber(data.sugerencia_compra.cantidad_sugerida ?? 0)}</span>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Costo estimado: </span>
                  <span className="font-bold">{formatCurrency(data.sugerencia_compra.costo_estimado ?? 0)}</span>
                </div>
                <div>
                  <Badge variant={data.sugerencia_compra.prioridad?.includes('Urgente') ? 'destructive' : 'secondary'}>
                    {data.sugerencia_compra.prioridad || '-'}
                  </Badge>
                </div>
                {data.sugerencia_compra.dias_stock != null && (
                  <div>
                    <span className="text-sm text-muted-foreground">Dias stock actual: </span>
                    <span className="font-bold">{data.sugerencia_compra.dias_stock}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

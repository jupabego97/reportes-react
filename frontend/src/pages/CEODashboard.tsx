import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsiveLine } from '@nivo/line';
import { ResponsiveScatterPlot } from '@nivo/scatterplot';
import {
  BarChart3,
  DollarSign,
  Package,
  Percent,
  RefreshCw,
  ShoppingCart,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { FilterPanel } from '../components/filters/FilterPanel';
import { MetricTooltip } from '../components/ui/metric-tooltip';
import { useMetricasSector } from '../hooks/useApi';
import { cn } from '../lib/utils';
import type { ResumenVentanaTemporal, SectorMetric, VariacionVentanaTemporal } from '../types';

const ABC_COLORS: Record<string, string> = { A: '#2563eb', B: '#f59e0b', C: '#94a3b8' };

function variacionChip(v?: number | null) {
  if (v === null || v === undefined) return null;
  const up = Number(v) >= 0;
  return (
    <span className={cn('text-xs font-medium', up ? 'text-green-600' : 'text-red-600')}>
      {up ? '+' : ''}
      {formatNumber(v, 1)}% vs periodo ant.
    </span>
  );
}

function TemporalVentanaCard({
  titulo,
  resumen,
  variacion,
}: {
  titulo: string;
  resumen?: ResumenVentanaTemporal;
  variacion?: VariacionVentanaTemporal;
}) {
  if (!resumen) return null;
  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{titulo}</CardTitle>
        <CardDescription>
          Ticket: {formatCurrency(resumen.ticket_promedio)} · {formatNumber(resumen.facturas)} facturas
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-3xl font-bold">{formatNumber(resumen.unidades)}</div>
        <p className="text-sm text-muted-foreground">
          unidades · <span className="font-medium text-foreground">{formatNumber(resumen.lineas)}</span> líneas
        </p>
        <p className="text-sm text-muted-foreground">Ventas: {formatCurrency(resumen.ventas)}</p>
        <div className="flex flex-wrap gap-2 pt-1">
          {variacionChip(variacion?.unidades_pct)}
          {variacionChip(variacion?.ticket_pct)}
        </div>
      </CardContent>
    </Card>
  );
}

function formatCurrency(value: unknown) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

function formatNumber(value: unknown, digits = 0) {
  return new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value) || 0);
}

function metricValue(metric: SectorMetric | undefined, type: 'currency' | 'pct' | 'number' | 'ratio' = 'number') {
  const value = metric?.value;
  if (value === null || value === undefined) return '—';
  if (type === 'currency') return formatCurrency(value);
  if (type === 'pct') return `${formatNumber(value, 1)}%`;
  if (type === 'ratio') return formatNumber(value, 2);
  return formatNumber(value, 0);
}

function qualityLabel(metric: SectorMetric | undefined) {
  if (!metric) return null;
  if (metric.quality === 'proxy') return <Badge variant="secondary">proxy</Badge>;
  if (metric.quality === 'unavailable') return <Badge variant="destructive">sin fuente</Badge>;
  return <Badge variant="outline">estándar</Badge>;
}

type KpiCardProps = {
  id: string;
  metric?: SectorMetric;
  icon: ReactNode;
  type?: 'currency' | 'pct' | 'number' | 'ratio';
  className?: string;
};

function KpiCard({ id, metric, icon, type = 'number', className }: KpiCardProps) {
  const tooltip = metric ? `${metric.formula}. ${metric.source_note}` : '';
  return (
    <Card className={cn('min-h-[120px]', className)}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="min-w-0">
          <CardTitle className="flex items-center text-sm font-medium text-muted-foreground">
            <span className="truncate">{metric?.label ?? id}</span>
            {metric && <MetricTooltip text={tooltip} />}
          </CardTitle>
        </div>
        <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center text-primary shrink-0">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tracking-normal">{metricValue(metric, type)}</div>
        <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
          {qualityLabel(metric)}
        </div>
      </CardContent>
    </Card>
  );
}

function ChartFrame({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="h-[280px]">{children}</div>
      </CardContent>
    </Card>
  );
}

export function CEODashboard() {
  const { data, isLoading, error, refetch } = useMetricasSector();
  const k = data?.kpis ?? {};

  if (error) {
    return <div className="text-center py-8 text-destructive">Error al cargar métricas: {error.message}</div>;
  }

  const rt = data?.resumen_temporal;
  const varRt = rt?.variacion;

  const ventasLine = [
    {
      id: 'Ventas',
      data: (data?.ventas_diarias ?? []).map((d) => ({ x: String(d.fecha), y: Number(d.ventas) || 0 })),
    },
    {
      id: 'Media 7d',
      data: (data?.ventas_diarias ?? []).map((d) => ({ x: String(d.fecha), y: Number(d.media_movil_7d) || 0 })),
    },
  ];

  const unidadesTicketLine = [
    {
      id: 'Unidades',
      data: (data?.ventas_diarias ?? []).map((d) => ({ x: String(d.fecha), y: Number(d.unidades) || 0 })),
    },
    {
      id: 'Ticket',
      data: (data?.ventas_diarias ?? []).map((d) => ({ x: String(d.fecha), y: Number(d.ticket_promedio) || 0 })),
    },
  ];

  const semanaData = (data?.ventas_por_semana ?? []).map((d) => ({
    periodo: String(d.periodo ?? '').slice(5),
    unidades: Number(d.unidades) || 0,
    ticket: Number(d.ticket_promedio) || 0,
  }));

  const mesData = (data?.ventas_por_mes ?? []).map((d) => ({
    periodo: String(d.periodo ?? ''),
    unidades: Number(d.unidades) || 0,
    ticket: Number(d.ticket_promedio) || 0,
  }));

  const margenDiarioLine = [
    {
      id: 'Margen %',
      data: (data?.margen_diario ?? []).map((d) => ({
        x: String(d.fecha),
        y: Number(d.margen_bruto_pct) || 0,
      })),
    },
  ];

  const forecastDetalle = data?.forecast_backtest?.detalle ?? [];
  const forecastLine = [
    {
      id: 'Real',
      data: forecastDetalle.map((d: Record<string, unknown>, idx: number) => ({
        x: String(d.semana ?? idx + 1),
        y: Number(d.real) || 0,
      })),
    },
    {
      id: 'Predicho',
      data: forecastDetalle.map((d: Record<string, unknown>, idx: number) => ({
        x: String(d.semana ?? idx + 1),
        y: Number(d.predicho) || 0,
      })),
    },
  ];

  const familiaData = (data?.ventas_por_familia ?? []).map((d) => ({
    familia: String(d.familia ?? 'Sin familia').slice(0, 18),
    ventas: Number(d.ventas) || 0,
    margen: Number(d.margen_bruto) || 0,
    margen_pct: Number(d.margen_pct) || 0,
  }));

  const ticketVendedorData = (data?.ticket_por_vendedor ?? []).map((d) => ({
    vendedor: String(d.vendedor ?? 'Sin vendedor').slice(0, 16),
    unidades: Number(d.unidades_por_ticket) || 0,
    lineas: Number(d.lineas_por_ticket) || 0,
  }));

  const saludData = [
    { estado: 'Sano', porcentaje: Number(data?.salud_inventario?.stock_sano_pct) || 0 },
    { estado: 'Riesgo', porcentaje: Number(data?.salud_inventario?.stock_riesgo_pct) || 0 },
    { estado: 'Exceso', porcentaje: Number(data?.salud_inventario?.stock_exceso_pct) || 0 },
  ];

  const scatterData = (['A', 'B', 'C'] as const).map((cat) => ({
    id: `ABC ${cat}`,
    data: (data?.inventario_scatter ?? [])
      .filter((d) => (d.categoria || 'C') === cat)
      .map((d) => ({
        x: Math.min(Number(d.dias_cobertura) || 0, 180),
        y: Number(d.margen_pct) || 0,
        nombre: d.nombre,
      })),
  }));

  const abcLine = [
    {
      id: 'Acumulado',
      data: (data?.abc_pareto ?? []).map((d, idx) => ({ x: idx + 1, y: Number(d.acumulado) || 0 })),
    },
  ];

  const proveedorData = (data?.proveedores_vencimientos ?? []).map((d) => ({
    proveedor: String(d.proveedor ?? 'Sin proveedor').slice(0, 18),
    vencido: Number(d.monto_vencido) || 0,
    proximo: Number(d.monto_proximo) || 0,
  }));

  const waterfallData = [
    { concepto: 'Ventas c/costo', valor: Number(k.ventas_con_costo?.value) || 0 },
    { concepto: 'COGS', valor: Number(k.cogs_estimado?.value) || 0 },
    { concepto: 'Margen', valor: Number(k.margen_bruto?.value) || 0 },
  ];

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between gap-4"
      >
        <div className="min-w-0">
          <h1 className="text-3xl font-bold tracking-tight">Dashboard Ejecutivo</h1>
          <p className="text-muted-foreground">
            Métricas retail con fuentes estándar y proxies marcados
          </p>
        </div>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </motion.div>

      <FilterPanel />

      {isLoading || !data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-[120px]" />
          ))}
        </div>
      ) : (
        <>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid gap-4 md:grid-cols-3"
          >
            <TemporalVentanaCard titulo="Hoy" resumen={rt?.hoy} variacion={varRt?.hoy_vs_ayer} />
            <TemporalVentanaCard
              titulo="Últimos 7 días"
              resumen={rt?.ultimos_7d}
              variacion={varRt?.ultimos_7d_vs_previos_7d}
            />
            <TemporalVentanaCard
              titulo="Últimos 30 días"
              resumen={rt?.ultimos_30d}
              variacion={varRt?.ultimos_30d_vs_previos_30d}
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
          >
            <KpiCard metric={k.ventas_totales} id="ventas_totales" icon={<DollarSign className="h-4 w-4" />} type="currency" />
            <KpiCard metric={k.unidades_vendidas} id="unidades_vendidas" icon={<Package className="h-4 w-4" />} />
            <KpiCard metric={k.asp} id="asp" icon={<DollarSign className="h-4 w-4" />} type="currency" />
            <KpiCard metric={k.lineas_vendidas} id="lineas_vendidas" icon={<ShoppingCart className="h-4 w-4" />} />
            <KpiCard metric={k.variacion_vs_periodo_anterior} id="variacion_vs_periodo_anterior" icon={<TrendingUp className="h-4 w-4" />} type="pct" />
            <KpiCard metric={k.margen_bruto_pct} id="margen_bruto_pct" icon={<Percent className="h-4 w-4" />} type="pct" />
            <KpiCard metric={k.cobertura_costo_pct} id="cobertura_costo_pct" icon={<BarChart3 className="h-4 w-4" />} type="pct" />
            <KpiCard metric={k.stockout_rate_sku} id="stockout_rate_sku" icon={<Package className="h-4 w-4" />} type="pct" />
            <KpiCard metric={k.sell_through_proxy} id="sell_through_proxy" icon={<TrendingUp className="h-4 w-4" />} type="pct" />
            <KpiCard metric={k.gmroi_proxy} id="gmroi_proxy" icon={<Target className="h-4 w-4" />} type="ratio" />
            <KpiCard metric={k.wape_forecast} id="wape_forecast" icon={<BarChart3 className="h-4 w-4" />} type="pct" />
            <KpiCard metric={k.bias_forecast_pct} id="bias_forecast_pct" icon={<TrendingUp className="h-4 w-4" />} type="pct" />
          </motion.div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartFrame title="Ventas diarias" description="Ventas y media móvil de 7 días">
              <ResponsiveLine
                data={ventasLine}
                margin={{ top: 20, right: 24, bottom: 58, left: 70 }}
                xScale={{ type: 'point' }}
                yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                axisBottom={{ tickRotation: -35, tickSize: 0, tickPadding: 12 }}
                axisLeft={{ format: (v) => `$${Number(v) / 1000}k` }}
                pointSize={4}
                enableGridX={false}
                useMesh
              />
            </ChartFrame>

            <ChartFrame title="Unidades y ticket por día" description="Unidades vendidas y ticket promedio diario">
              <ResponsiveLine
                data={unidadesTicketLine}
                margin={{ top: 20, right: 24, bottom: 58, left: 70 }}
                xScale={{ type: 'point' }}
                yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                axisBottom={{ tickRotation: -35, tickSize: 0, tickPadding: 12 }}
                pointSize={4}
                enableGridX={false}
                useMesh
              />
            </ChartFrame>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartFrame title="Por semana" description="Unidades por semana">
              <ResponsiveBar data={semanaData} keys={['unidades']} indexBy="periodo" margin={{ top: 20, right: 20, bottom: 50, left: 54 }} padding={0.3} />
            </ChartFrame>
            <ChartFrame title="Por mes" description="Unidades por mes">
              <ResponsiveBar data={mesData} keys={['unidades']} indexBy="periodo" margin={{ top: 20, right: 20, bottom: 50, left: 54 }} padding={0.3} />
            </ChartFrame>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartFrame title="Margen bruto % diario" description="Evolución del margen">
              <ResponsiveLine data={margenDiarioLine} margin={{ top: 20, right: 24, bottom: 58, left: 54 }} xScale={{ type: 'point' }} yScale={{ type: 'linear', min: 0, max: 'auto' }} axisBottom={{ tickRotation: -35 }} axisLeft={{ format: (v) => `${v}%` }} pointSize={4} enableGridX={false} useMesh />
            </ChartFrame>
            <ChartFrame title="Forecast backtest" description="Real vs predicho">
              <ResponsiveLine data={forecastLine} margin={{ top: 20, right: 24, bottom: 48, left: 70 }} xScale={{ type: 'point' }} yScale={{ type: 'linear', min: 'auto', max: 'auto' }} axisLeft={{ format: (v) => `$${Number(v) / 1000}k` }} pointSize={4} enableGridX={false} useMesh />
            </ChartFrame>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <ChartFrame title="Familias" description="Ventas, margen bruto y margen %">
              <ResponsiveBar
                data={familiaData}
                keys={['ventas', 'margen', 'margen_pct']}
                indexBy="familia"
                margin={{ top: 20, right: 20, bottom: 80, left: 70 }}
                padding={0.25}
                groupMode="grouped"
                axisBottom={{ tickRotation: -45 }}
                axisLeft={{ format: (v) => `$${Number(v) / 1000}k` }}
              />
            </ChartFrame>

            <ChartFrame title="Margen bruto" description="Ventas con costo, COGS y margen">
              <ResponsiveBar
                data={waterfallData}
                keys={['valor']}
                indexBy="concepto"
                margin={{ top: 20, right: 20, bottom: 50, left: 70 }}
                padding={0.35}
                colors={['#2563eb', '#dc2626', '#16a34a']}
                axisLeft={{ format: (v) => `$${Number(v) / 1000}k` }}
              />
            </ChartFrame>

            <ChartFrame title="Salud inventario" description="Sano, riesgo y exceso separados">
              <ResponsiveBar
                data={saludData}
                keys={['porcentaje']}
                indexBy="estado"
                margin={{ top: 20, right: 20, bottom: 48, left: 54 }}
                padding={0.35}
                valueScale={{ type: 'linear', min: 0, max: 100 }}
                axisLeft={{ format: (v) => `${v}%` }}
              />
            </ChartFrame>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartFrame title="Inventario" description="Cobertura vs margen por curva ABC">
              <ResponsiveScatterPlot
                data={scatterData}
                margin={{ top: 20, right: 24, bottom: 58, left: 70 }}
                xScale={{ type: 'linear', min: 0, max: 180 }}
                yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                axisBottom={{ legend: 'Días cobertura', legendOffset: 42, legendPosition: 'middle' }}
                axisLeft={{ legend: 'Margen %', legendOffset: -52, legendPosition: 'middle' }}
                colors={(d) => ABC_COLORS[String(d.serieId).replace('ABC ', '')] ?? '#94a3b8'}
                nodeSize={7}
                useMesh
              />
            </ChartFrame>

            <ChartFrame title="Pareto ABC" description="Contribución acumulada por SKU">
              <ResponsiveLine
                data={abcLine}
                margin={{ top: 20, right: 24, bottom: 48, left: 54 }}
                xScale={{ type: 'linear', min: 1, max: 'auto' }}
                yScale={{ type: 'linear', min: 0, max: 100 }}
                axisBottom={{ legend: 'Ranking SKU', legendOffset: 38, legendPosition: 'middle' }}
                axisLeft={{ format: (v) => `${v}%` }}
                pointSize={4}
                enableGridX={false}
                useMesh
              />
            </ChartFrame>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartFrame title="Tickets por vendedor" description="Unidades y líneas por factura">
              <ResponsiveBar
                data={ticketVendedorData}
                keys={['unidades', 'lineas']}
                indexBy="vendedor"
                margin={{ top: 20, right: 20, bottom: 80, left: 54 }}
                padding={0.25}
                groupMode="grouped"
                axisBottom={{ tickRotation: -45 }}
              />
            </ChartFrame>

            <ChartFrame title="Proveedores" description="Vencido y próximo por proveedor">
              <ResponsiveBar
                data={proveedorData}
                keys={['vencido', 'proximo']}
                indexBy="proveedor"
                margin={{ top: 20, right: 20, bottom: 80, left: 70 }}
                padding={0.25}
                groupMode="stacked"
                axisBottom={{ tickRotation: -45 }}
                axisLeft={{ format: (v) => `$${Number(v) / 1000}k` }}
              />
            </ChartFrame>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Users className="h-4 w-4" />
                Calidad de datos
              </CardTitle>
              <CardDescription>
                Clientes y márgenes dependen de captura de cliente y costo promedio
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              {[
                { id: 'clientes_identificados', metric: k.clientes_identificados, type: 'number' as const },
                { id: 'repeat_customer_rate_proxy', metric: k.repeat_customer_rate_proxy, type: 'pct' as const },
                { id: 'margen_promedio_simple', metric: k.margen_promedio_simple, type: 'pct' as const },
                { id: 'compras_por_proveedor', metric: k.compras_por_proveedor, type: 'currency' as const },
                { id: 'mae_forecast', metric: k.mae_forecast, type: 'currency' as const },
              ].map(({ id, metric, type }) => (
                <div key={id} className="rounded-md border p-4">
                  <div className="flex items-center justify-between gap-2 text-sm text-muted-foreground">
                    <span>{metric?.label ?? id}</span>
                    {metric && <MetricTooltip text={`${metric.formula}. ${metric.source_note}`} />}
                  </div>
                  <div className="mt-2 text-xl font-bold">{metricValue(metric, type)}</div>
                  <div className="mt-2">{qualityLabel(metric)}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  DollarSign,
  ShoppingCart,
  TrendingUp,
  TrendingDown,
  Package,
  Lightbulb,
  BarChart3,
  Users,
  RefreshCw,
  Target,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { FilterPanel } from '../components/filters/FilterPanel';
import { cn } from '../lib/utils';
import { useKpisCEO } from '../hooks/useApi';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

type InsightCard = {
  tipo: string;
  icono: string;
  titulo: string;
  descripcion: string;
};

export function CEODashboard() {
  const { data: k, isLoading, error, refetch } = useKpisCEO();

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar KPIs: {error.message}
      </div>
    );
  }

  const cards = (k?.insight_cards as InsightCard[] | undefined) ?? [];

  const n = (v: unknown) => Number(v ?? 0);
  const s = (v: unknown) => (v == null ? '' : String(v));

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard Ejecutivo</h1>
          <p className="text-muted-foreground">
            KPIs consolidados según los filtros de fecha y segmento (misma fuente que operaciones)
          </p>
        </div>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </motion.div>

      <FilterPanel />

      {isLoading || !k ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-[120px]" />
          ))}
        </div>
      ) : (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
          >
            <Card className="border-blue-500/20 bg-gradient-to-br from-blue-500/10 to-transparent">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Ventas hoy</CardTitle>
                <DollarSign className="h-5 w-5 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(Number(k.ventas_hoy) || 0)}</div>
                <div className="flex items-center gap-2 mt-1 text-sm">
                  {Number(k.delta_vs_ayer) >= 0 ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  )}
                  <span
                    className={cn(
                      Number(k.delta_vs_ayer) >= 0 ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {Number(k.delta_vs_ayer ?? 0) >= 0 ? '+' : ''}
                    {s(k.delta_vs_ayer)}% vs ayer
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{n(k.transacciones_hoy)} lineas hoy</p>
              </CardContent>
            </Card>

            <Card className="border-green-500/20 bg-gradient-to-br from-green-500/10 to-transparent">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Ventas (periodo filtrado)</CardTitle>
                <BarChart3 className="h-5 w-5 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(Number(k.ventas_mes) || 0)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {k.delta_ventas_periodo_str
                    ? `vs anterior: ${s(k.delta_ventas_periodo_str)}`
                    : 'Sin comparativo'}
                </p>
                <p className="text-xs text-muted-foreground">{n(k.transacciones_mes)} registros</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Margen y ticket</CardTitle>
                <Target className="h-5 w-5 text-purple-500" />
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{formatCurrency(Number(k.margen_total) || 0)}</div>
                <p className="text-sm text-muted-foreground">
                  Bruto {Number(k.margen_bruto_pct ?? 0).toFixed(1)}% sobre ventas con costo
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Ticket linea ~ {formatCurrency(Number(k.ticket_promedio_linea) || 0)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Forecast (precision)</CardTitle>
                <TrendingUp className="h-5 w-5 text-orange-500" />
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold">
                  WAPE {k.wape_forecast != null ? `${s(k.wape_forecast)}%` : '—'}
                </p>
                <p className="text-xs text-muted-foreground">
                  MAPE {k.mape_forecast != null ? `${s(k.mape_forecast)}%` : '—'} (4 sem. backtest)
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Inventario ($)</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xl font-bold">{formatCurrency(Number(k.valor_inventario_total) || 0)}</p>
                <p className="text-xs text-muted-foreground">
                  Criticos {formatCurrency(Number(k.valor_criticos) || 0)} · Exceso{' '}
                  {formatCurrency(Number(k.valor_exceso) || 0)}
                </p>
                <p className="text-xs mt-1">Salud {Number(k.salud_inventario_pct ?? 0).toFixed(0)}%</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Stockout rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{Number(k.stockout_pct ?? 0).toFixed(1)}%</p>
                <p className="text-xs text-muted-foreground">
                  {n(k.stockout_sin_stock)}/{n(k.stockout_activos)} SKU activos sin stock
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Concentracion margen</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{Number(k.concentracion_margen_top10_pct ?? 0).toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground">Top 10 SKU por margen ($)</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Costo oportunidad (7d)</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xl font-bold">
                  {formatCurrency(Number(k.costo_oportunidad_estimado) || 0)}
                </p>
                <p className="text-xs text-muted-foreground">Estimado por roturas</p>
              </CardContent>
            </Card>
          </motion.div>

          {(Array.isArray(k.gmroi_top_familias) && k.gmroi_top_familias.length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle>GMROI por familia (proxy)</CardTitle>
                <CardDescription>Margen del periodo / valor inventario actual</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="text-sm space-y-1">
                  {(k.gmroi_top_familias as { familia: string; gmroi: number }[]).slice(0, 5).map((row) => (
                    <li key={row.familia} className="flex justify-between gap-2">
                      <span>{row.familia}</span>
                      <span className="font-mono">{row.gmroi}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Urgencias (top 5)</CardTitle>
                <CardDescription>Productos en riesgo (sugerencias con forecast)</CardDescription>
              </CardHeader>
              <CardContent className="text-sm space-y-2 max-h-[220px] overflow-y-auto">
                {(k.top_urgencias as Record<string, unknown>[] | undefined)?.length ? (
                  (k.top_urgencias as Record<string, unknown>[]).map((u, i) => (
                    <div key={i} className="border-b pb-1 last:border-0">
                      <span className="font-medium">{String(u.nombre)}</span>
                      <span className="text-muted-foreground"> · {String(u.prioridad ?? '')}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground">Sin urgencias en este filtro</p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Oportunidades (top 5)</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2 max-h-[220px] overflow-y-auto">
                {(k.top_oportunidades as Record<string, unknown>[] | undefined)?.length ? (
                  (k.top_oportunidades as Record<string, unknown>[]).map((u, i) => (
                    <div key={i} className="border-b pb-1 last:border-0">
                      <span className="font-medium">{String(u.nombre)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground">Sin datos</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                Insights automaticos
              </CardTitle>
              <CardDescription>Resumen accionable (no sustituye la pestaña Insights)</CardDescription>
            </CardHeader>
            <CardContent>
              {cards.length === 0 ? (
                <p className="text-muted-foreground text-center py-6">Sin alertas destacadas</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {cards.map((insight, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        'p-4 rounded-lg border',
                        insight.tipo === 'positive' && 'bg-green-50/50 border-green-500/20 dark:bg-green-950/20',
                        insight.tipo === 'warning' && 'bg-orange-50/50 border-orange-500/20 dark:bg-orange-950/20',
                        insight.tipo === 'negative' && 'bg-red-50/50 border-red-500/20 dark:bg-red-950/20',
                        insight.tipo === 'info' && 'bg-muted/40 border-border'
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">{insight.icono}</span>
                        <div>
                          <h4 className="font-semibold">{insight.titulo}</h4>
                          <p className="text-sm text-muted-foreground mt-1">{insight.descripcion}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            <Link to="/inventario" className="block">
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
                    <Package className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Inventario</h3>
                    <p className="text-sm text-muted-foreground">Stock y alertas</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
            <Card className="hover:bg-muted/50 transition-colors">
              <Link to="/compras" className="block">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
                    <ShoppingCart className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Compras</h3>
                    <p className="text-sm text-muted-foreground">Prioridad y pedidos</p>
                  </div>
                </CardContent>
              </Link>
            </Card>
            <Card className="hover:bg-muted/50 transition-colors">
              <Link to="/vendedores" className="block">
                <CardContent className="flex items-center gap-4 pt-6">
                  <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
                    <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Equipo comercial</h3>
                    <p className="text-sm text-muted-foreground">Ranking</p>
                  </div>
                </CardContent>
              </Link>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  CalendarCheck,
  PackageSearch,
  Warehouse,
  Truck,
  AlertTriangle,
  TrendingDown,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { buttonVariants } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import {
  useSugerenciasCompra,
  useResumenComprasProveedores,
  useSaludInventario,
  useInventarioResumen,
  useInventarioAgotados,
  useKpisCEO,
} from '../hooks/useApi';
import { useProveedoresUrgenciaAgrupados, useUrgenciasCompraRows } from '../hooks/useUrgencias';
import { cn, formatCurrency, formatNumber } from '../lib/utils';
import { ProductLink } from '../components/ProductLink';
import { FilterPanel } from '../components/filters/FilterPanel';

export function Hoy() {
  const { data: sugerencias, isLoading: loadingSug } = useSugerenciasCompra();
  const { data: resumenProv } = useResumenComprasProveedores();
  const { data: salud, isLoading: loadingSalud } = useSaludInventario();
  const { data: invResumen, isLoading: loadingInv } = useInventarioResumen();
  const { data: agotados, isLoading: loadingAgot } = useInventarioAgotados();
  const { data: kpisCeo, isLoading: loadingKpis } = useKpisCEO();

  const rows = Array.isArray(sugerencias) ? sugerencias : [];
  const comprarHoy = useUrgenciasCompraRows(rows, { umbralDias: 2 });

  const inversionHoy = useMemo(
    () => comprarHoy.reduce((acc: number, s: { costo_estimado?: number }) => acc + Number(s.costo_estimado || 0), 0),
    [comprarHoy]
  );

  const proveedoresAgrup = useProveedoresUrgenciaAgrupados(comprarHoy);
  const topProveedores = useMemo(() => proveedoresAgrup.slice(0, 5), [proveedoresAgrup]);

  const agotadosTotal =
    (agotados?.resumen?.total_agotados as number | undefined) ??
    ((agotados?.ultima_semana?.total as number | undefined) || 0) +
      ((agotados?.ultimas_2_semanas?.total as number | undefined) || 0);

  const loading = loadingSug || loadingSalud || loadingInv || loadingAgot || loadingKpis;

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <CalendarCheck className="h-8 w-8 text-primary" />
          Hoy
        </h1>
        <p className="text-muted-foreground max-w-2xl">
          Resumen operativo: qué comprar con urgencia, proveedores a contactar y riesgos de inventario. Los filtros
          aplican también a las sugerencias de compra.
        </p>
      </motion.div>

      <FilterPanel />

      {!loading && kpisCeo && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="pt-4 pb-3">
              <p className="text-xs text-muted-foreground">Ventas hoy</p>
              <p className="text-lg font-bold">{formatCurrency(Number(kpisCeo.ventas_hoy) || 0)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Período (filtros): {formatCurrency(Number(kpisCeo.ventas_mes) || 0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-xs text-muted-foreground">Margen bruto %</p>
              <p className="text-lg font-bold">{Number(kpisCeo.margen_bruto_pct ?? 0).toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground mt-1">
                WAPE (4 sem.): {kpisCeo.wape_forecast != null ? `${kpisCeo.wape_forecast}%` : '—'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-xs text-muted-foreground">Stockout (SKU activos)</p>
              <p className="text-lg font-bold">{Number(kpisCeo.stockout_pct ?? 0).toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground mt-1">
                Inventario: {formatCurrency(Number(kpisCeo.valor_inventario_total) || 0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-xs text-muted-foreground">Salud inventario</p>
              <p className="text-lg font-bold">{Number(kpisCeo.salud_inventario_pct ?? 0).toFixed(0)}%</p>
              <p className="text-xs text-muted-foreground mt-1">
                <Link className={buttonVariants({ variant: 'link', className: 'h-auto p-0 text-xs' })} to="/ceo">
                  Ver vista CEO
                </Link>
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[130px]" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <PackageSearch className="h-4 w-4" />
                Comprar hoy
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(comprarHoy.length)}</div>
              <p className="text-xs text-muted-foreground">Urgente / alta o stock ≤ 2 días</p>
              <p className="text-sm font-semibold text-primary mt-2">{formatCurrency(inversionHoy)}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Truck className="h-4 w-4" />
                Proveedores en esta ronda
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(topProveedores.length)}</div>
              <p className="text-xs text-muted-foreground">
                Con pedidos sugeridos · {resumenProv && Array.isArray(resumenProv) ? `${resumenProv.length} en total` : ''}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                Inventario crítico
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(invResumen?.productos_criticos ?? 0)}</div>
              <p className="text-xs text-muted-foreground">
                Salud {salud?.salud_porcentaje != null ? `${Math.round(salud.salud_porcentaje)}%` : '—'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-red-600" />
                Riesgo agotamiento
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(agotadosTotal)}</div>
              <p className="text-xs text-muted-foreground">SKUs con ventas y stock 0 (reciente)</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle>Prioridad inmediata</CardTitle>
              <CardDescription>Hasta 8 líneas · ir a Compras para la lista completa</CardDescription>
            </div>
            <Link
              className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
              to="/compras"
            >
              Compras <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-2">
            {loadingSug ? (
              <Skeleton className="h-40" />
            ) : comprarHoy.length === 0 ? (
              <p className="text-sm text-muted-foreground">No hay líneas urgentes con los filtros actuales.</p>
            ) : (
              comprarHoy.slice(0, 8).map((s: any) => (
                <div
                  key={s.nombre}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-2 text-sm"
                >
                  <div className="min-w-0 flex-1">
                    <ProductLink nombre={s.nombre} className="font-medium truncate block" />
                    <span className="text-muted-foreground">{s.proveedor || 'Sin proveedor'}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={s.prioridad === '🔴 Urgente' ? 'destructive' : 'secondary'}>{s.prioridad}</Badge>
                    <span className="tabular-nums">{s.cantidad_sugerida} u</span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle>Proveedores a contactar</CardTitle>
              <CardDescription>Ordenados por inversión estimada en la ventana urgente</CardDescription>
            </div>
            <Link
              className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
              to="/proveedores"
            >
              Proveedores <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-2">
            {topProveedores.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin agrupación hasta que haya sugerencias urgentes.</p>
            ) : (
              topProveedores.map((p) => (
                <div key={p.proveedor} className="flex justify-between gap-2 rounded-lg border p-3 text-sm">
                  <span className="font-medium truncate">{p.proveedor}</span>
                  <span className="text-muted-foreground shrink-0">
                    {p.productos} SKU · {formatCurrency(p.costo)}
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Warehouse className="h-5 w-5" />
              Capital e inventario
            </CardTitle>
            <CardDescription>
              Valor en exceso o crítico según el último cálculo del servidor
            </CardDescription>
          </div>
          <Link className={cn(buttonVariants({ variant: 'default' }))} to="/inventario">
            Ver inventario
          </Link>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3 text-sm">
          <div>
            <div className="text-muted-foreground">Valor total inventario</div>
            <div className="text-lg font-semibold">
              {invResumen?.valor_total != null ? formatCurrency(invResumen.valor_total) : '—'}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Valor en exceso</div>
            <div className="text-lg font-semibold text-blue-700 dark:text-blue-400">
              {invResumen?.valor_exceso != null ? formatCurrency(invResumen.valor_exceso) : '—'}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Valor crítico</div>
            <div className="text-lg font-semibold text-red-700 dark:text-red-400">
              {invResumen?.valor_criticos != null ? formatCurrency(invResumen.valor_criticos) : '—'}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

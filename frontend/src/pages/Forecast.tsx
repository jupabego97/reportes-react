import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Database, LineChart, PackageX, RefreshCw, Target } from 'lucide-react';
import { toast } from 'sonner';
import { apiService } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { cn } from '../lib/utils';

const dinero = (v: number | null | undefined) =>
  v == null
    ? '—'
    : new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0,
      }).format(v);

const pct = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`);

const urgenciaEstilo: Record<string, string> = {
  quiebre: 'bg-red-600 text-white',
  pedir_ya: 'bg-orange-500 text-white',
  planificar: 'bg-yellow-500 text-black',
  ok: 'bg-green-600 text-white',
};

export function Forecast() {
  const queryClient = useQueryClient();

  const { data: backtest, isLoading: cargandoBacktest, error: errorBacktest } = useQuery({
    queryKey: ['forecast-backtest'],
    queryFn: () => apiService.getUltimoBacktest(),
    staleTime: 60000,
  });

  const { data: precision } = useQuery({
    queryKey: ['forecast-precision'],
    queryFn: () => apiService.getPrecisionForecast(28),
    staleTime: 60000,
  });

  const { data: ventaPerdida, isLoading: cargandoVP } = useQuery({
    queryKey: ['venta-perdida'],
    queryFn: () => apiService.getVentaPerdida(30),
    staleTime: 60000,
  });

  const { data: sugerencias, isLoading: cargandoSug } = useQuery<any[]>({
    queryKey: ['reabastecimiento-sugerencias'],
    queryFn: () => apiService.getSugerenciasReabastecimiento(),
    staleTime: 60000,
  });

  const invalidarTodo = () => {
    queryClient.invalidateQueries({ queryKey: ['forecast-backtest'] });
    queryClient.invalidateQueries({ queryKey: ['forecast-precision'] });
    queryClient.invalidateQueries({ queryKey: ['venta-perdida'] });
    queryClient.invalidateQueries({ queryKey: ['reabastecimiento-sugerencias'] });
  };

  const consolidar = useMutation({
    mutationFn: () => apiService.consolidarHistorial(),
    onSuccess: (r) =>
      toast.success(
        `Historial consolidado: ${r.productos_con_historia} productos (${r.historia_desde} → ${r.historia_hasta})`,
      ),
    onError: (e: Error) => toast.error(e.message),
  });

  const generar = useMutation({
    mutationFn: () => apiService.generarForecast(28),
    onSuccess: (r) => {
      toast.success(`Forecast generado para ${r.productos_pronosticados} productos`);
      invalidarTodo();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const correrBacktest = useMutation({
    mutationFn: () => apiService.ejecutarBacktest(14),
    onSuccess: () => {
      toast.success('Backtest ejecutado');
      invalidarTodo();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const tieneBacktest = backtest && backtest.wmape_champion != null;
  const championGana =
    tieneBacktest &&
    backtest.wmape_baseline != null &&
    backtest.wmape_champion < backtest.wmape_baseline;

  const pedirYa = (sugerencias ?? []).filter(
    (s) => s.urgencia === 'quiebre' || s.urgencia === 'pedir_ya',
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Forecast y disponibilidad</h1>
          <p className="text-sm text-muted-foreground">
            Un solo pronóstico probabilístico alimenta compras, reabastecimiento y venta perdida.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => consolidar.mutate()}
            disabled={consolidar.isPending}
          >
            <Database className="mr-2 h-4 w-4" /> Consolidar historial
          </Button>
          <Button variant="outline" onClick={() => generar.mutate()} disabled={generar.isPending}>
            <LineChart className="mr-2 h-4 w-4" /> Generar forecast
          </Button>
          <Button onClick={() => correrBacktest.mutate()} disabled={correrBacktest.isPending}>
            <RefreshCw
              className={cn('mr-2 h-4 w-4', correrBacktest.isPending && 'animate-spin')}
            />
            Correr backtest
          </Button>
        </div>
      </div>

      {errorBacktest != null && (
        <Card className="border-red-300 bg-red-50">
          <CardContent className="py-4 text-sm text-red-700">
            {(errorBacktest as Error).message}
          </CardContent>
        </Card>
      )}

      {/* Gobernanza del modelo */}
      <Card className={cn(tieneBacktest && !championGana && 'border-orange-500/60')}>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-4 w-4" />
            Gobernanza del modelo (backtest honesto)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cargandoBacktest ? (
            <Skeleton className="h-16 w-full" />
          ) : !tieneBacktest ? (
            <p className="text-sm text-muted-foreground">
              Aún no hay backtest. Consolida el historial y corre el primero: el modelo solo se usa
              si le gana al baseline ingenuo (promedio del mismo día de semana).
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <div>
                <p className="text-xl font-bold">{pct(backtest.wmape_champion)}</p>
                <p className="text-xs text-muted-foreground">WMAPE modelo</p>
              </div>
              <div>
                <p className="text-xl font-bold">{pct(backtest.wmape_baseline)}</p>
                <p className="text-xs text-muted-foreground">WMAPE baseline</p>
              </div>
              <div>
                <p className="text-xl font-bold">
                  {backtest.sesgo_champion_pct != null ? `${backtest.sesgo_champion_pct}%` : '—'}
                </p>
                <p className="text-xs text-muted-foreground">Sesgo (+ sobra, − falta)</p>
              </div>
              <div>
                <p className="text-xl font-bold">{backtest.productos_evaluados}</p>
                <p className="text-xs text-muted-foreground">Productos evaluados</p>
              </div>
              <div>
                <Badge className={championGana ? 'bg-green-600 text-white' : 'bg-orange-500 text-white'}>
                  {championGana ? 'Modelo aprobado' : 'Usar baseline'}
                </Badge>
                <p className="mt-1 text-xs text-muted-foreground">
                  {championGana
                    ? 'Le gana al método ingenuo'
                    : 'No supera al método ingenuo todavía'}
                </p>
              </div>
            </div>
          )}
          {precision && precision.evaluaciones > 0 && (
            <p className="mt-3 text-xs text-muted-foreground">
              Precisión real (forecast usado vs venta observada, 28 días): WMAPE{' '}
              {pct(precision.wmape)} · sesgo {precision.sesgo_pct}% ·{' '}
              {precision.evaluaciones.toLocaleString('es-CO')} evaluaciones
            </p>
          )}
        </CardContent>
      </Card>

      {/* Venta perdida */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <PackageX className="h-4 w-4" />
            Venta perdida por quiebres (30 días) — la métrica que financia el programa
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cargandoVP ? (
            <Skeleton className="h-24 w-full" />
          ) : !ventaPerdida || ventaPerdida.productos_en_quiebre === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin quiebres con demanda comprobada en la ventana. Consolida el historial para
              mantener esta medición viva.
            </p>
          ) : (
            <>
              <div className="mb-3 grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xl font-bold text-red-600">
                    {dinero(ventaPerdida.venta_perdida_total)}
                  </p>
                  <p className="text-xs text-muted-foreground">Venta no realizada</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-red-600">
                    {dinero(ventaPerdida.margen_perdido_total)}
                  </p>
                  <p className="text-xs text-muted-foreground">Margen no capturado</p>
                </div>
                <div>
                  <p className="text-xl font-bold">{ventaPerdida.productos_en_quiebre}</p>
                  <p className="text-xs text-muted-foreground">Productos en quiebre</p>
                </div>
              </div>
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-2 py-1.5 text-left">Producto</th>
                      <th className="px-2 py-1.5 text-right">Días en quiebre</th>
                      <th className="px-2 py-1.5 text-right">Venta diaria previa</th>
                      <th className="px-2 py-1.5 text-right">Venta perdida</th>
                      <th className="px-2 py-1.5 text-right">Margen perdido</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ventaPerdida.detalle.slice(0, 10).map((d: any) => (
                      <tr key={d.nombre} className="border-t">
                        <td className="px-2 py-1.5">{d.nombre}</td>
                        <td className="px-2 py-1.5 text-right">{d.dias_en_quiebre}</td>
                        <td className="px-2 py-1.5 text-right">{d.venta_diaria_previa}</td>
                        <td className="px-2 py-1.5 text-right font-medium">
                          {dinero(d.venta_perdida)}
                        </td>
                        <td className="px-2 py-1.5 text-right">{dinero(d.margen_perdido)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Reabastecimiento con SS dinámico */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            Reabastecimiento con stock de seguridad dinámico (A: 99% · B: 97% · C: 92%)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cargandoSug ? (
            <Skeleton className="h-32 w-full" />
          ) : !sugerencias || sugerencias.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin datos suficientes. Consolida el historial de ventas primero.
            </p>
          ) : (
            <>
              <p className="mb-3 text-sm text-muted-foreground">
                {pedirYa.length} productos requieren pedido inmediato (en quiebre o bajo su punto
                de reorden) de {sugerencias.length} analizados.
              </p>
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-2 py-1.5 text-left">Producto</th>
                      <th className="px-2 py-1.5 text-left">ABC</th>
                      <th className="px-2 py-1.5 text-right">Stock</th>
                      <th className="px-2 py-1.5 text-right">Demanda/día</th>
                      <th className="px-2 py-1.5 text-right">SS</th>
                      <th className="px-2 py-1.5 text-right">ROP</th>
                      <th className="px-2 py-1.5 text-right">Sugerido</th>
                      <th className="px-2 py-1.5 text-right">Costo</th>
                      <th className="px-2 py-1.5 text-left">Urgencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sugerencias.slice(0, 25).map((s) => (
                      <tr key={s.nombre} className="border-t">
                        <td className="px-2 py-1.5">{s.nombre}</td>
                        <td className="px-2 py-1.5">
                          <Badge variant="outline">{s.abc}</Badge>
                        </td>
                        <td className="px-2 py-1.5 text-right">{s.stock_actual}</td>
                        <td className="px-2 py-1.5 text-right">{s.demanda_diaria}</td>
                        <td className="px-2 py-1.5 text-right">{s.stock_seguridad}</td>
                        <td className="px-2 py-1.5 text-right">{s.punto_reorden}</td>
                        <td className="px-2 py-1.5 text-right font-medium">
                          {s.cantidad_sugerida}
                        </td>
                        <td className="px-2 py-1.5 text-right">{dinero(s.costo_estimado)}</td>
                        <td className="px-2 py-1.5">
                          <Badge className={urgenciaEstilo[s.urgencia] ?? ''}>
                            {s.urgencia.replace('_', ' ')}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowDownRight,
  BarChart3,
  Database,
  Layers,
  RefreshCw,
  Tag,
  TrendingDown,
} from 'lucide-react';
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

const accionEstilo: Record<string, string> = {
  potenciar: 'bg-green-600 text-white',
  mantener: 'bg-gray-200 text-gray-800',
  reducir: 'bg-yellow-500 text-black',
  eliminar: 'bg-red-600 text-white',
};

export function PrecioSurtido() {
  const queryClient = useQueryClient();

  const { data: oportunidades, isLoading: cargandoOpp } = useQuery<any[]>({
    queryKey: ['pricing-oportunidades'],
    queryFn: () => apiService.getOportunidadesPrecio(),
    staleTime: 60000,
  });

  const { data: surtido, isLoading: cargandoSurtido } = useQuery<any[]>({
    queryKey: ['surtido-revision'],
    queryFn: () => apiService.getRevisionSurtido(),
    staleTime: 60000,
  });

  const { data: diagnostico, isLoading: cargandoDiag } = useQuery<any>({
    queryKey: ['diagnostico-descomposicion'],
    queryFn: () => apiService.getDescomposicionCausal(),
    staleTime: 60000,
  });

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['pricing-oportunidades'] });
    queryClient.invalidateQueries({ queryKey: ['surtido-revision'] });
    queryClient.invalidateQueries({ queryKey: ['diagnostico-descomposicion'] });
  };

  const consolidar = useMutation({
    mutationFn: () => apiService.consolidarPrecios(),
    onSuccess: (r) =>
      toast.success(
        `Precios consolidados: ${r.productos_con_precio} productos (${r.historia_desde} → ${r.historia_hasta})`,
      ),
    onError: (e: Error) => toast.error(e.message),
  });

  const markdowns = useMutation({
    mutationFn: () => apiService.generarMarkdowns(),
    onSuccess: (r) => {
      toast.success(`${r.recomendaciones_emitidas} markdowns generados`);
      invalidar();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const revision = useMutation({
    mutationFn: () => apiService.generarRevisionSurtido(),
    onSuccess: (r) => {
      toast.success(`Revisión: ${r.recomendaciones_emitidas} recomendaciones`);
      invalidar();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const baja = useMutation({
    mutationFn: (productoId: number) => apiService.aplicarBajaSurtido(productoId),
    onSuccess: () => {
      toast.success('SKU dado de baja lógica');
      invalidar();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const efectos = diagnostico
    ? [
        { label: 'Volumen', valor: diagnostico.efecto_volumen, color: 'bg-blue-500' },
        { label: 'Precio', valor: diagnostico.efecto_precio, color: 'bg-indigo-500' },
        { label: 'Mix', valor: diagnostico.efecto_mix, color: 'bg-violet-500' },
      ]
    : [];
  const maxEfecto = Math.max(...efectos.map((e) => Math.abs(e.valor || 0)), 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Precio y surtido</h1>
          <p className="text-sm text-muted-foreground">
            Markdowns para capital atrapado, matriz GMROI×velocidad y diagnóstico causal
            volumen/precio/mix.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => consolidar.mutate()}
            disabled={consolidar.isPending}
          >
            <Database className="mr-2 h-4 w-4" /> Consolidar precios
          </Button>
          <Button variant="outline" onClick={() => markdowns.mutate()} disabled={markdowns.isPending}>
            <Tag className="mr-2 h-4 w-4" /> Generar markdowns
          </Button>
          <Button onClick={() => revision.mutate()} disabled={revision.isPending}>
            <RefreshCw className={cn('mr-2 h-4 w-4', revision.isPending && 'animate-spin')} />
            Revisar surtido
          </Button>
        </div>
      </div>

      {/* Oportunidades de precio */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <ArrowDownRight className="h-4 w-4" />
            Oportunidades de precio / markdowns
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cargandoOpp ? (
            <Skeleton className="h-24 w-full" />
          ) : !oportunidades || oportunidades.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin recomendaciones pendientes. Ejecuta «Consolidar precios» y «Generar markdowns».
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="pb-2 pr-3">Producto</th>
                    <th className="pb-2 pr-3 text-right">Actual</th>
                    <th className="pb-2 pr-3 text-right">Sugerido</th>
                    <th className="pb-2 pr-3 text-right">Descuento</th>
                    <th className="pb-2 pr-3 text-right">Capital</th>
                    <th className="pb-2">Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {oportunidades.map((o) => (
                    <tr key={o.id} className="border-t">
                      <td className="py-1.5 pr-3">{o.nombre}</td>
                      <td className="py-1.5 pr-3 text-right">{dinero(o.precio_actual)}</td>
                      <td className="py-1.5 pr-3 text-right font-medium text-green-700">
                        {dinero(o.precio_sugerido)}
                      </td>
                      <td className="py-1.5 pr-3 text-right">
                        {o.descuento_pct != null ? `−${o.descuento_pct}%` : '—'}
                      </td>
                      <td className="py-1.5 pr-3 text-right">{dinero(o.impacto_estimado)}</td>
                      <td className="py-1.5 text-muted-foreground">{o.motivo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Revisión de surtido */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Layers className="h-4 w-4" />
            Revisión de surtido (GMROI × velocidad)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cargandoSurtido ? (
            <Skeleton className="h-24 w-full" />
          ) : !surtido || surtido.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Ejecuta «Revisar surtido» para clasificar productos. GMROI usa inventario actual
              como proxy (documentado).
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="pb-2 pr-3">Producto</th>
                    <th className="pb-2 pr-3 text-right">GMROI</th>
                    <th className="pb-2 pr-3 text-right">Vel. rel.</th>
                    <th className="pb-2 pr-3">Acción</th>
                    <th className="pb-2 pr-3 text-right">Inv. costo</th>
                    <th className="pb-2 pr-3">Transfer. proxy</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {surtido
                    .filter((s) => s.accion !== 'mantener')
                    .slice(0, 25)
                    .map((s) => (
                      <tr key={s.producto_id} className="border-t">
                        <td className="py-1.5 pr-3">{s.nombre}</td>
                        <td className="py-1.5 pr-3 text-right">
                          {s.gmroi != null ? s.gmroi.toFixed(2) : '—'}
                        </td>
                        <td className="py-1.5 pr-3 text-right">{s.velocidad_relativa}x</td>
                        <td className="py-1.5 pr-3">
                          <Badge className={accionEstilo[s.accion] ?? ''}>{s.accion}</Badge>
                        </td>
                        <td className="py-1.5 pr-3 text-right">{dinero(s.inventario_costo)}</td>
                        <td className="py-1.5 pr-3 text-muted-foreground">
                          {s.transferencia_proxy_pct != null
                            ? `${s.transferencia_proxy_pct}%`
                            : '—'}
                        </td>
                        <td className="py-1.5">
                          {s.accion === 'eliminar' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => baja.mutate(s.producto_id)}
                              disabled={baja.isPending}
                            >
                              Baja lógica
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diagnóstico causal */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-4 w-4" />
            Diagnóstico causal (últimos 7d vs 7d previos)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cargandoDiag ? (
            <Skeleton className="h-32 w-full" />
          ) : !diagnostico ? (
            <p className="text-sm text-muted-foreground">Sin datos de ventas para comparar.</p>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div>
                  <p className="text-xs text-muted-foreground">Δ Venta</p>
                  <p
                    className={cn(
                      'text-lg font-semibold',
                      diagnostico.delta_venta >= 0 ? 'text-green-600' : 'text-red-600',
                    )}
                  >
                    {dinero(diagnostico.delta_venta)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Δ Margen</p>
                  <p
                    className={cn(
                      'text-lg font-semibold',
                      diagnostico.delta_margen >= 0 ? 'text-green-600' : 'text-red-600',
                    )}
                  >
                    {dinero(diagnostico.delta_margen)}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-xs text-muted-foreground">Interpretación</p>
                  <p className="text-sm">{diagnostico.interpretacion}</p>
                </div>
              </div>

              <div className="space-y-2">
                {efectos.map((e) => (
                  <div key={e.label} className="flex items-center gap-3">
                    <span className="w-16 text-xs text-muted-foreground">{e.label}</span>
                    <div className="relative h-5 flex-1 rounded bg-muted">
                      <div
                        className={cn('absolute top-0 h-5 rounded', e.color)}
                        style={{
                          width: `${(Math.abs(e.valor) / maxEfecto) * 100}%`,
                          left: e.valor >= 0 ? '50%' : undefined,
                          right: e.valor < 0 ? '50%' : undefined,
                        }}
                      />
                    </div>
                    <span
                      className={cn(
                        'w-24 text-right text-sm font-medium',
                        e.valor >= 0 ? 'text-green-600' : 'text-red-600',
                      )}
                    >
                      {dinero(e.valor)}
                    </span>
                  </div>
                ))}
              </div>

              {diagnostico.detalle?.length > 0 && (
                <div>
                  <p className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-muted-foreground">
                    <TrendingDown className="h-3 w-3" /> Top productos que explican la variación
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-muted-foreground">
                          <th className="pb-1 pr-2">Producto</th>
                          <th className="pb-1 pr-2 text-right">Δ Venta</th>
                          <th className="pb-1 pr-2 text-right">Vol.</th>
                          <th className="pb-1 pr-2 text-right">Precio</th>
                          <th className="pb-1 text-right">Mix</th>
                        </tr>
                      </thead>
                      <tbody>
                        {diagnostico.detalle.slice(0, 8).map((d: any) => (
                          <tr key={d.nombre} className="border-t">
                            <td className="py-1 pr-2">{d.nombre}</td>
                            <td className="py-1 pr-2 text-right">{dinero(d.delta_venta)}</td>
                            <td className="py-1 pr-2 text-right">{dinero(d.efecto_volumen)}</td>
                            <td className="py-1 pr-2 text-right">{dinero(d.efecto_precio)}</td>
                            <td className="py-1 text-right">{dinero(d.efecto_mix)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

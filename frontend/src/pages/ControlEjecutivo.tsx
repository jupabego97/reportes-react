import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  Gauge,
  Play,
  Shield,
  Sparkles,
  Timer,
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

export function ControlEjecutivo() {
  const queryClient = useQueryClient();

  const { data: resumen, isLoading, error } = useQuery({
    queryKey: ['control-resumen'],
    queryFn: () => apiService.getControlResumen(),
    staleTime: 30000,
  });

  const { data: politicas } = useQuery({
    queryKey: ['autonomia-politicas'],
    queryFn: () => apiService.getPoliticasAutonomia(),
    staleTime: 60000,
  });

  const { data: jobs } = useQuery({
    queryKey: ['orquestador-jobs'],
    queryFn: () => apiService.getOrquestadorJobs(5),
    staleTime: 30000,
  });

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['control-resumen'] });
    queryClient.invalidateQueries({ queryKey: ['orquestador-jobs'] });
    queryClient.invalidateQueries({ queryKey: ['autonomia-politicas'] });
    queryClient.invalidateQueries({ queryKey: ['decisiones'] });
  };

  const correr = useMutation({
    mutationFn: () => apiService.correrOrquestador(),
    onSuccess: (r) => {
      toast.success(
        `Ciclo completado: ${r.pasos?.autonomia_nivel1?.decisiones_resueltas ?? 0} auto-resueltas, ${r.pasos?.autonomia_nivel1?.oc_aprobadas ?? 0} OC aprobadas`,
      );
      invalidar();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const togglePolitica = useMutation({
    mutationFn: ({ codigo, habilitado }: { codigo: string; habilitado: boolean }) =>
      apiService.actualizarPoliticaAutonomia(codigo, { habilitado }),
    onSuccess: () => {
      toast.success('Política actualizada');
      invalidar();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Control ejecutivo</h1>
          <p className="text-sm text-muted-foreground">
            Orquestación nocturna, autonomía Nivel 1 y mapa de riesgos/oportunidades.
          </p>
        </div>
        <Button onClick={() => correr.mutate()} disabled={correr.isPending}>
          <Play className={cn('mr-2 h-4 w-4', correr.isPending && 'animate-pulse')} />
          Correr ciclo nocturno ahora
        </Button>
      </div>

      {error != null && (
        <Card className="border-red-300 bg-red-50">
          <CardContent className="py-4 text-sm text-red-700">
            {(error as Error).message}
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-28 w-full" />
      ) : resumen ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Dinero en riesgo</p>
              <p className="text-xl font-bold text-red-600">{dinero(resumen.dinero_en_riesgo)}</p>
              <p className="text-xs text-muted-foreground">{resumen.riesgos_activos} alertas</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Oportunidades</p>
              <p className="text-xl font-bold text-green-600">
                {dinero(resumen.dinero_en_oportunidades)}
              </p>
              <p className="text-xs text-muted-foreground">
                {resumen.oportunidades_activas} items
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Tasa aceptación</p>
              <p className="text-xl font-bold">
                {resumen.tasa_aceptacion_pct != null
                  ? `${resumen.tasa_aceptacion_pct}%`
                  : '—'}
              </p>
              <p className="text-xs text-muted-foreground">
                Auto Nivel 1:{' '}
                {resumen.pct_auto_nivel1 != null ? `${resumen.pct_auto_nivel1}%` : '—'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <Timer className="h-3 w-3" /> Último ciclo
              </p>
              <p className="text-xl font-bold">
                {resumen.horas_desde_ultimo_ciclo != null
                  ? `${resumen.horas_desde_ultimo_ciclo}h`
                  : 'Nunca'}
              </p>
              <p className="text-xs text-muted-foreground">
                {resumen.politicas_habilitadas} políticas activas
              </p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              Top riesgos
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!resumen?.top_riesgos?.length ? (
              <p className="text-sm text-muted-foreground">Sin riesgos activos en la bandeja.</p>
            ) : (
              <ul className="space-y-2">
                {resumen.top_riesgos.map((r: any) => (
                  <li key={r.decision_id} className="border-b pb-2 text-sm last:border-0">
                    <div className="flex justify-between gap-2">
                      <span>{r.titulo}</span>
                      <Badge variant="outline">{r.prioridad}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {dinero(r.impacto_dinero)} · score {r.score}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-green-600" />
              Top oportunidades
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!resumen?.top_oportunidades?.length ? (
              <p className="text-sm text-muted-foreground">Sin oportunidades cuantificadas.</p>
            ) : (
              <ul className="space-y-2">
                {resumen.top_oportunidades.map((o: any, i: number) => (
                  <li key={`${o.codigo}-${i}`} className="border-b pb-2 text-sm last:border-0">
                    <div className="flex justify-between gap-2">
                      <span>{o.titulo}</span>
                      <span className="font-medium text-green-700">{dinero(o.impacto_dinero)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {o.codigo} · score {o.score}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-4 w-4" />
            Políticas de autonomía Nivel 1
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!politicas?.length ? (
            <p className="text-sm text-muted-foreground">Sin políticas (¿migración 006 aplicada?).</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="pb-2 pr-3">Código</th>
                    <th className="pb-2 pr-3">Descripción</th>
                    <th className="pb-2 pr-3 text-right">Umbral $</th>
                    <th className="pb-2">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {politicas.map((p: any) => (
                    <tr key={p.codigo} className="border-t">
                      <td className="py-1.5 pr-3 font-mono text-xs">{p.codigo}</td>
                      <td className="py-1.5 pr-3">{p.descripcion}</td>
                      <td className="py-1.5 pr-3 text-right">{dinero(p.auto_max_impacto)}</td>
                      <td className="py-1.5">
                        <Button
                          size="sm"
                          variant={p.habilitado ? 'default' : 'outline'}
                          onClick={() =>
                            togglePolitica.mutate({
                              codigo: p.codigo,
                              habilitado: !p.habilitado,
                            })
                          }
                          disabled={togglePolitica.isPending}
                        >
                          {p.habilitado ? 'Activa' : 'Off'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Gauge className="h-4 w-4" />
            Últimas corridas del orquestador
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!jobs?.length ? (
            <p className="text-sm text-muted-foreground">
              Aún no hay corridas. Pulsa «Correr ciclo nocturno ahora» o configura un cron a{' '}
              <code className="text-xs">POST /api/orquestador/correr</code>.
            </p>
          ) : (
            <ul className="space-y-2 text-sm">
              {jobs.map((j: any) => (
                <li key={j.id} className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                  <span>
                    #{j.id} · {j.iniciado_en}
                  </span>
                  <Badge
                    className={
                      j.estado === 'ok'
                        ? 'bg-green-600 text-white'
                        : j.estado === 'error'
                          ? 'bg-red-600 text-white'
                          : ''
                    }
                  >
                    {j.estado}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {resumen?.modulos_sin_datos?.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="py-4 text-sm text-muted-foreground">
            <p className="mb-1 font-medium text-foreground">Módulos pendientes (sin datos)</p>
            Red multi-tienda/CD, transferencias, fraude POS, dotación/turnos, promociones
            causales y CLV/market basket requieren fuentes nuevas. No se fingen en esta fase.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

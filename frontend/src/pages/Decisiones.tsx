import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiService } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { cn } from '../lib/utils';

interface Decision {
  id: number;
  codigo_alerta: string;
  prioridad: 'P1' | 'P2' | 'P3' | 'P4';
  titulo: string;
  que_pasa: string;
  por_que: string;
  que_hacer: string;
  impacto_dinero: number | null;
  dueno: string;
  vence_en: string | null;
  estado: string;
  datos: unknown;
  created_at: string;
}

const prioridadEstilo: Record<string, { label: string; className: string }> = {
  P1: { label: 'P1 · Crítica (horas)', className: 'bg-red-600 text-white' },
  P2: { label: 'P2 · Alta (hoy)', className: 'bg-orange-500 text-white' },
  P3: { label: 'P3 · Media (semana)', className: 'bg-yellow-500 text-black' },
  P4: { label: 'P4 · Estructural', className: 'bg-blue-500 text-white' },
};

const duenoLabel: Record<string, string> = {
  comprador: 'Comprador',
  pricing: 'Pricing',
  gerente_tienda: 'Gerente de tienda',
  finanzas: 'Finanzas',
  admin: 'Administración',
};

const formatoDinero = (valor: number | null) =>
  valor == null
    ? '—'
    : new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0,
      }).format(valor);

function DatosDetalle({ datos }: { datos: unknown }) {
  if (!datos) return null;
  const filas = Array.isArray(datos) ? datos : [datos];
  if (filas.length === 0 || typeof filas[0] !== 'object') return null;
  const columnas = Object.keys(filas[0] as Record<string, unknown>);

  return (
    <div className="mt-3 overflow-x-auto rounded-md border">
      <table className="w-full text-xs">
        <thead className="bg-muted/50">
          <tr>
            {columnas.map((c) => (
              <th key={c} className="px-2 py-1.5 text-left font-medium capitalize">
                {c.replaceAll('_', ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.slice(0, 15).map((fila, i) => (
            <tr key={i} className="border-t">
              {columnas.map((c) => {
                const v = (fila as Record<string, unknown>)[c];
                return (
                  <td key={c} className="px-2 py-1.5">
                    {typeof v === 'number'
                      ? new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 }).format(v)
                      : String(v ?? '—')}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {filas.length > 15 && (
        <p className="px-2 py-1.5 text-xs italic text-muted-foreground">
          … y {filas.length - 15} filas más
        </p>
      )}
    </div>
  );
}

function DecisionCard({ decision }: { decision: Decision }) {
  const [expandida, setExpandida] = useState(false);
  const queryClient = useQueryClient();

  const resolver = useMutation({
    mutationFn: ({ estado, nota }: { estado: 'aprobada' | 'rechazada' | 'resuelta'; nota?: string }) =>
      apiService.resolverDecision(decision.id, estado, nota),
    onSuccess: (_, vars) => {
      toast.success(`Decisión ${vars.estado}`);
      queryClient.invalidateQueries({ queryKey: ['decisiones'] });
      queryClient.invalidateQueries({ queryKey: ['decisiones-resumen'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const estilo = prioridadEstilo[decision.prioridad] ?? prioridadEstilo.P3;
  const vence = decision.vence_en ? new Date(decision.vence_en) : null;

  return (
    <Card className={cn(decision.prioridad === 'P1' && 'border-red-500/60')}>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={estilo.className}>{estilo.label}</Badge>
          <Badge variant="outline">{duenoLabel[decision.dueno] ?? decision.dueno}</Badge>
          {vence && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              vence {vence.toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })}
            </span>
          )}
          <span className="ml-auto text-sm font-semibold">
            {formatoDinero(decision.impacto_dinero)}
          </span>
        </div>
        <CardTitle className="text-base">{decision.titulo}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>
          <span className="font-semibold">Qué pasa: </span>
          {decision.que_pasa}
        </p>
        <p>
          <span className="font-semibold">Por qué: </span>
          {decision.por_que}
        </p>
        <p>
          <span className="font-semibold">Qué hacer: </span>
          {decision.que_hacer}
        </p>

        {decision.datos != null && (
          <Button
            variant="ghost"
            size="sm"
            className="h-auto p-0 text-xs"
            onClick={() => setExpandida(!expandida)}
          >
            {expandida ? (
              <>
                <ChevronUp className="mr-1 h-3 w-3" /> Ocultar detalle
              </>
            ) : (
              <>
                <ChevronDown className="mr-1 h-3 w-3" /> Ver detalle
              </>
            )}
          </Button>
        )}
        {expandida && <DatosDetalle datos={decision.datos} />}

        <div className="flex gap-2 pt-2">
          <Button
            size="sm"
            disabled={resolver.isPending}
            onClick={() => resolver.mutate({ estado: 'aprobada' })}
          >
            <CheckCircle2 className="mr-1 h-4 w-4" /> Aprobar acción
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={resolver.isPending}
            onClick={() => resolver.mutate({ estado: 'resuelta', nota: 'Resuelta manualmente' })}
          >
            Marcar resuelta
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-red-600"
            disabled={resolver.isPending}
            onClick={() => resolver.mutate({ estado: 'rechazada' })}
          >
            <XCircle className="mr-1 h-4 w-4" /> Rechazar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function Decisiones() {
  const [dueno, setDueno] = useState<string | undefined>(undefined);
  const queryClient = useQueryClient();

  const { data: resumen } = useQuery({
    queryKey: ['decisiones-resumen'],
    queryFn: () => apiService.getDecisionesResumen(),
    staleTime: 30000,
  });

  const { data: decisiones, isLoading } = useQuery<Decision[]>({
    queryKey: ['decisiones', dueno ?? 'todos'],
    queryFn: () => apiService.getDecisiones({ dueno, estado: 'pendiente', limite: 100 }),
    staleTime: 30000,
  });

  const evaluar = useMutation({
    mutationFn: () => apiService.evaluarDecisiones(),
    onSuccess: (r) => {
      toast.success(`Evaluación completa: ${r.decisiones_emitidas} decisiones nuevas`);
      queryClient.invalidateQueries({ queryKey: ['decisiones'] });
      queryClient.invalidateQueries({ queryKey: ['decisiones-resumen'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const duenos = ['comprador', 'pricing', 'gerente_tienda', 'finanzas'];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Bandeja de decisiones</h1>
          <p className="text-sm text-muted-foreground">
            Cada decisión indica qué pasa, por qué, qué hacer y cuánto vale. Sin acción no hay alerta.
          </p>
        </div>
        <Button onClick={() => evaluar.mutate()} disabled={evaluar.isPending}>
          <RefreshCw className={cn('mr-2 h-4 w-4', evaluar.isPending && 'animate-spin')} />
          Evaluar ahora
        </Button>
      </div>

      {resumen && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-2xl font-bold">{resumen.pendientes}</p>
              <p className="text-xs text-muted-foreground">Decisiones pendientes</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-2xl font-bold">{formatoDinero(resumen.impacto_dinero_total)}</p>
              <p className="text-xs text-muted-foreground">Dinero en juego</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-2xl font-bold text-red-600">
                {resumen.por_prioridad?.P1?.pendientes ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Críticas (P1)</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-2xl font-bold text-orange-500">
                {resumen.por_prioridad?.P2?.pendientes ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Altas (P2)</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={dueno === undefined ? 'default' : 'outline'}
          onClick={() => setDueno(undefined)}
        >
          Todos
        </Button>
        {duenos.map((d) => (
          <Button
            key={d}
            size="sm"
            variant={dueno === d ? 'default' : 'outline'}
            onClick={() => setDueno(d)}
          >
            {duenoLabel[d]}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : !decisiones || decisiones.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-10 text-muted-foreground">
            <AlertTriangle className="h-5 w-5" />
            <span>
              No hay decisiones pendientes{dueno ? ' para este rol' : ''}. Ejecuta «Evaluar ahora»
              para correr los detectores.
            </span>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {decisiones.map((d) => (
            <DecisionCard key={d.id} decision={d} />
          ))}
        </div>
      )}
    </div>
  );
}

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  PackageCheck,
  Send,
  Trash2,
  TrendingDown,
  Truck,
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

const estadoEstilo: Record<string, string> = {
  borrador: 'bg-gray-200 text-gray-800',
  aprobada: 'bg-blue-600 text-white',
  enviada: 'bg-indigo-600 text-white',
  recibida_parcial: 'bg-yellow-500 text-black',
  recibida: 'bg-green-600 text-white',
  cancelada: 'bg-gray-400 text-white line-through',
};

const estadoLabel: Record<string, string> = {
  borrador: 'Borrador',
  aprobada: 'Aprobada',
  enviada: 'Enviada',
  recibida_parcial: 'Recibida parcial',
  recibida: 'Recibida',
  cancelada: 'Cancelada',
};

function OrdenCard({ orden }: { orden: any }) {
  const [expandida, setExpandida] = useState(false);
  const queryClient = useQueryClient();

  const { data: detalle, isLoading: cargandoDetalle } = useQuery({
    queryKey: ['oc-detalle', orden.id],
    queryFn: () => apiService.getOrdenCompraDetalle(orden.id),
    enabled: expandida,
    staleTime: 30000,
  });

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['ordenes-compra'] });
    queryClient.invalidateQueries({ queryKey: ['oc-detalle', orden.id] });
  };

  const opciones = (ok: string) => ({
    onSuccess: () => {
      toast.success(ok);
      invalidar();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const aprobar = useMutation({
    mutationFn: () => apiService.aprobarOrdenCompra(orden.id),
    ...opciones('Orden aprobada'),
  });
  const enviar = useMutation({
    mutationFn: () => apiService.enviarOrdenCompra(orden.id),
    ...opciones('Orden enviada al proveedor'),
  });
  const cancelar = useMutation({
    mutationFn: () => apiService.cancelarOrdenCompra(orden.id),
    ...opciones('Orden cancelada'),
  });
  const recibirTodo = useMutation({
    mutationFn: async () => {
      const d = detalle ?? (await apiService.getOrdenCompraDetalle(orden.id));
      return apiService.recibirOrdenCompra(
        orden.id,
        d.lineas.map((l: any) => ({
          producto_id: l.producto_id,
          cantidad_recibida: l.cantidad_pedida,
        })),
      );
    },
    ...opciones('Recepción completa registrada'),
  });

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Badge className={estadoEstilo[orden.estado] ?? ''}>
              {estadoLabel[orden.estado] ?? orden.estado}
            </Badge>
            <div>
              <p className="font-semibold">{orden.numero}</p>
              <p className="text-sm text-muted-foreground">
                {orden.proveedor ?? 'Sin proveedor asignado'} · {orden.num_lineas} productos
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="font-semibold">{dinero(orden.total_costo)}</p>
              {orden.cumple_pedido_minimo === false && (
                <p className="text-xs text-orange-600">
                  No alcanza el pedido mínimo ({dinero(orden.pedido_minimo)})
                </p>
              )}
              {orden.fecha_promesa && (
                <p className="text-xs text-muted-foreground">Promesa: {orden.fecha_promesa}</p>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={() => setExpandida(!expandida)}>
              {expandida ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {orden.estado === 'borrador' && (
            <>
              <Button size="sm" onClick={() => aprobar.mutate()} disabled={aprobar.isPending}>
                <CheckCircle2 className="mr-1 h-4 w-4" /> Aprobar
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => cancelar.mutate()}
                disabled={cancelar.isPending}
              >
                <Trash2 className="mr-1 h-4 w-4" /> Descartar
              </Button>
            </>
          )}
          {orden.estado === 'aprobada' && (
            <Button size="sm" onClick={() => enviar.mutate()} disabled={enviar.isPending}>
              <Send className="mr-1 h-4 w-4" /> Enviar al proveedor
            </Button>
          )}
          {(orden.estado === 'enviada' || orden.estado === 'recibida_parcial') && (
            <Button size="sm" onClick={() => recibirTodo.mutate()} disabled={recibirTodo.isPending}>
              <PackageCheck className="mr-1 h-4 w-4" /> Recibir completa
            </Button>
          )}
        </div>

        {expandida && (
          <div className="mt-4 border-t pt-3">
            {cargandoDetalle ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-muted-foreground">
                      <th className="pb-2 pr-3">Producto</th>
                      <th className="pb-2 pr-3 text-right">Pedido</th>
                      <th className="pb-2 pr-3 text-right">Recibido</th>
                      <th className="pb-2 pr-3 text-right">Costo unit.</th>
                      <th className="pb-2 pr-3">Urgencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(detalle?.lineas ?? []).map((l: any) => (
                      <tr key={l.producto_id} className="border-t">
                        <td className="py-1.5 pr-3">{l.nombre}</td>
                        <td className="py-1.5 pr-3 text-right">{l.cantidad_pedida}</td>
                        <td className="py-1.5 pr-3 text-right">{l.cantidad_recibida}</td>
                        <td className="py-1.5 pr-3 text-right">{dinero(l.costo_unitario)}</td>
                        <td className="py-1.5 pr-3">
                          <Badge
                            variant="outline"
                            className={cn(
                              l.urgencia === 'quiebre' && 'border-red-500 text-red-600',
                              l.urgencia === 'pedir_ya' && 'border-orange-500 text-orange-600',
                            )}
                          >
                            {l.urgencia}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function OrdenesCompra() {
  const [filtroEstado, setFiltroEstado] = useState<string | undefined>(undefined);
  const queryClient = useQueryClient();

  const { data: ordenes, isLoading, error } = useQuery<any[]>({
    queryKey: ['ordenes-compra', filtroEstado ?? 'todas'],
    queryFn: () => apiService.getOrdenesCompra({ estado: filtroEstado, limite: 100 }),
    staleTime: 30000,
  });

  const { data: scorecard } = useQuery<any[]>({
    queryKey: ['scorecard-proveedores'],
    queryFn: () => apiService.getScorecardProveedores(90),
    staleTime: 60000,
  });

  const generar = useMutation({
    mutationFn: () => apiService.generarOrdenesCompra(),
    onSuccess: (r) => {
      if (r.ordenes_creadas === 0) {
        toast.info(r.mensaje ?? 'No hay productos urgentes que pedir');
      } else {
        toast.success(`${r.ordenes_creadas} órdenes en borrador (${r.lineas} productos)`);
      }
      queryClient.invalidateQueries({ queryKey: ['ordenes-compra'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const estados = ['borrador', 'aprobada', 'enviada', 'recibida', 'cancelada'];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Órdenes de compra</h1>
          <p className="text-sm text-muted-foreground">
            Del punto de reorden a la OC: cantidades redondeadas a empaque, pedido mínimo del
            proveedor y OTIF medido en cada recepción.
          </p>
        </div>
        <Button onClick={() => generar.mutate()} disabled={generar.isPending}>
          <ClipboardList className="mr-2 h-4 w-4" />
          Generar OC desde sugerencias
        </Button>
      </div>

      {error != null && (
        <Card className="border-red-300 bg-red-50">
          <CardContent className="py-4 text-sm text-red-700">
            {(error as Error).message}
          </CardContent>
        </Card>
      )}

      {/* Scorecard de proveedores */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Truck className="h-4 w-4" />
            Scorecard de proveedores (90 días, OC recibidas)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!scorecard || scorecard.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aún no hay órdenes recibidas: el OTIF se mide con el ciclo real enviada → recibida.
              A medida que registres recepciones, cada proveedor tendrá su calificación.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="pb-2 pr-3">Proveedor</th>
                    <th className="pb-2 pr-3 text-right">Órdenes</th>
                    <th className="pb-2 pr-3 text-right">OTIF</th>
                    <th className="pb-2 pr-3 text-right">Fill rate</th>
                    <th className="pb-2 pr-3 text-right">LT prometido</th>
                    <th className="pb-2 pr-3 text-right">LT real</th>
                  </tr>
                </thead>
                <tbody>
                  {scorecard.map((s) => (
                    <tr key={s.proveedor_id} className="border-t">
                      <td className="py-1.5 pr-3">{s.proveedor}</td>
                      <td className="py-1.5 pr-3 text-right">{s.ordenes}</td>
                      <td
                        className={cn(
                          'py-1.5 pr-3 text-right font-semibold',
                          s.cumple_objetivo ? 'text-green-600' : 'text-red-600',
                        )}
                      >
                        {s.otif_pct != null ? `${s.otif_pct}%` : '—'}
                        {!s.cumple_objetivo && (
                          <TrendingDown className="ml-1 inline h-3.5 w-3.5" />
                        )}
                      </td>
                      <td className="py-1.5 pr-3 text-right">
                        {s.fill_rate_pct != null ? `${s.fill_rate_pct}%` : '—'}
                      </td>
                      <td className="py-1.5 pr-3 text-right">{s.lead_time_prometido} d</td>
                      <td className="py-1.5 pr-3 text-right">
                        {s.lead_time_real_promedio != null
                          ? `${s.lead_time_real_promedio} d`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filtros de estado */}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={filtroEstado === undefined ? 'default' : 'outline'}
          onClick={() => setFiltroEstado(undefined)}
        >
          Todas
        </Button>
        {estados.map((e) => (
          <Button
            key={e}
            size="sm"
            variant={filtroEstado === e ? 'default' : 'outline'}
            onClick={() => setFiltroEstado(e)}
          >
            {estadoLabel[e]}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : !ordenes || ordenes.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No hay órdenes{filtroEstado ? ` en estado «${estadoLabel[filtroEstado]}»` : ''}. Usa
            «Generar OC desde sugerencias» para crear borradores con los productos urgentes.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {ordenes.map((o) => (
            <OrdenCard key={o.id} orden={o} />
          ))}
        </div>
      )}
    </div>
  );
}

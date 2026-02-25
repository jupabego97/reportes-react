import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShoppingCart, TrendingUp, TrendingDown, Minus,
  Download, ChevronDown, ChevronUp, AlertTriangle,
  Package, RefreshCw, Info, X,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from '../components/ui/table';
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from '../components/ui/tooltip';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { useUrgenciasProveedor, useSugerenciasV2, useExportPedido } from '../hooks/useApi';
import { cn } from '../lib/utils';

// ─── tipos ────────────────────────────────────────────────────────────────────

interface OtroProveedor {
  proveedor: string;
  precio_compra: number;
  fecha_ultima_compra: string;
  es_proveedor_principal: boolean;
}

interface Sugerencia {
  nombre: string;
  familia?: string;
  proveedor_principal?: string;
  stock_actual: number;
  velocidad_diaria: number;
  dias_stock: number;
  cantidad_sugerida: number;
  precio_ultimo?: number;
  costo_estimado: number;
  urgencia: string;
  clasificacion_abc: string;
  tendencia: string;
  factor_estacional: number;
  otros_proveedores: OtroProveedor[];
}

interface UrgenciaProveedor {
  proveedor: string;
  urgente: number;
  alta: number;
  media: number;
  ok: number;
  total_productos_activos: number;
  inversion_estimada: number;
}

// ─── helpers de estilos ───────────────────────────────────────────────────────

const urgenciaConfig: Record<string, { label: string; badgeClass: string; rowClass: string }> = {
  urgente: { label: 'URGENTE', badgeClass: 'bg-red-600 text-white', rowClass: 'bg-red-50 dark:bg-red-950/20' },
  alta:    { label: 'Alta',    badgeClass: 'bg-orange-500 text-white', rowClass: 'bg-orange-50 dark:bg-orange-950/20' },
  media:   { label: 'Media',   badgeClass: 'bg-yellow-500 text-white', rowClass: '' },
  baja:    { label: 'Baja',    badgeClass: 'bg-blue-500 text-white',   rowClass: '' },
  ok:      { label: 'OK',      badgeClass: 'bg-green-600 text-white',  rowClass: '' },
};

const abcVariant: Record<string, 'default' | 'secondary' | 'outline'> = {
  A: 'default', B: 'secondary', C: 'outline',
};

function DiasStockCell({ dias }: { dias: number }) {
  const color =
    dias <= 7  ? 'text-red-600 font-bold' :
    dias <= 14 ? 'text-orange-500 font-semibold' :
    dias <= 30 ? 'text-yellow-600' : 'text-green-600';
  return <span className={color}>{dias === 999 ? '∞' : dias.toFixed(0)}</span>;
}

function TendenciaIcon({ t }: { t: string }) {
  if (t === 'creciente')  return <TrendingUp  className="h-4 w-4 text-green-600 inline" />;
  if (t === 'decreciente') return <TrendingDown className="h-4 w-4 text-red-500 inline" />;
  return <Minus className="h-4 w-4 text-muted-foreground inline" />;
}

function PrecioComparativo({ otros }: { otros: OtroProveedor[] }) {
  if (otros.length <= 1) return null;
  const alternativas = otros.filter(p => !p.es_proveedor_principal);
  if (alternativas.length === 0) return null;
  const masBarato = alternativas.reduce((a, b) => a.precio_compra < b.precio_compra ? a : b);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="ml-1 cursor-help text-blue-500 text-xs underline underline-offset-2">
          ★ {masBarato.proveedor.slice(0, 10)}…
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p className="font-semibold mb-1">Otros proveedores para este SKU:</p>
        <div className="space-y-1">
          {otros.map(p => (
            <div key={p.proveedor} className="flex justify-between gap-4 text-xs">
              <span className={p.es_proveedor_principal ? 'font-bold' : ''}>{p.proveedor}</span>
              <span>${p.precio_compra.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

// ─── tarjeta de proveedor ─────────────────────────────────────────────────────

function ProveedorCard({
  prov,
  selected,
  onClick,
}: {
  prov: UrgenciaProveedor;
  selected: boolean;
  onClick: () => void;
}) {
  const tieneUrgentes = prov.urgente > 0;
  const tieneAltas = prov.alta > 0;
  return (
    <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
      <Card
        onClick={onClick}
        className={cn(
          'cursor-pointer transition-all border-2',
          selected
            ? 'border-primary shadow-md'
            : tieneUrgentes
            ? 'border-red-400'
            : tieneAltas
            ? 'border-orange-300'
            : 'border-border',
        )}
      >
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-semibold truncate">{prov.proveedor}</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="flex gap-2 flex-wrap">
            {prov.urgente > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 font-semibold">
                🔴 {prov.urgente} urgente{prov.urgente > 1 ? 's' : ''}
              </span>
            )}
            {prov.alta > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 font-semibold">
                🟠 {prov.alta} alta{prov.alta > 1 ? 's' : ''}
              </span>
            )}
            {prov.media > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400">
                🟡 {prov.media} media{prov.media > 1 ? 's' : ''}
              </span>
            )}
            {prov.urgente === 0 && prov.alta === 0 && prov.media === 0 && (
              <span className="text-xs text-muted-foreground">✓ Sin urgencias</span>
            )}
          </div>
          {prov.inversion_estimada > 0 && (
            <p className="text-xs text-muted-foreground mt-2">
              Inversión: <span className="font-semibold">${prov.inversion_estimada.toLocaleString()}</span>
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ─── fila expandible de la tabla ─────────────────────────────────────────────

function FilaSugerencia({
  item,
  checked,
  cantidadPedido,
  onCheck,
  onCantidadChange,
}: {
  item: Sugerencia;
  checked: boolean;
  cantidadPedido: number;
  onCheck: (v: boolean) => void;
  onCantidadChange: (v: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const cfg = urgenciaConfig[item.urgencia] ?? urgenciaConfig.ok;
  const tieneAlternativas = item.otros_proveedores.length > 1;
  const precioMasBarato = tieneAlternativas
    ? Math.min(...item.otros_proveedores.map(p => p.precio_compra))
    : null;
  const hayMasBarato =
    precioMasBarato !== null &&
    item.precio_ultimo !== undefined &&
    precioMasBarato < item.precio_ultimo;

  return (
    <>
      <TableRow className={cn(cfg.rowClass, checked && 'ring-1 ring-primary/40')}>
        {/* Checkbox */}
        <TableCell>
          <input
            type="checkbox"
            checked={checked}
            onChange={e => onCheck(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 cursor-pointer"
          />
        </TableCell>

        {/* Urgencia */}
        <TableCell>
          <span className={cn('text-xs px-2 py-1 rounded-full font-semibold', cfg.badgeClass)}>
            {cfg.label}
          </span>
        </TableCell>

        {/* Producto */}
        <TableCell className="max-w-[200px]">
          <div className="truncate font-medium text-sm" title={item.nombre}>{item.nombre}</div>
          {item.familia && <div className="text-xs text-muted-foreground">{item.familia}</div>}
        </TableCell>

        {/* ABC */}
        <TableCell>
          <Badge variant={abcVariant[item.clasificacion_abc] ?? 'outline'}>
            {item.clasificacion_abc}
          </Badge>
        </TableCell>

        {/* Stock */}
        <TableCell className="text-right">
          <span className={item.stock_actual === 0 ? 'text-red-600 font-bold' : ''}>
            {item.stock_actual}
          </span>
        </TableCell>

        {/* Días stock */}
        <TableCell className="text-right">
          <DiasStockCell dias={item.dias_stock} />
        </TableCell>

        {/* Velocidad */}
        <TableCell className="text-right text-xs text-muted-foreground">
          {item.velocidad_diaria}/día
          {item.factor_estacional !== 1 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3 w-3 inline ml-1 cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                Factor estacional: ×{item.factor_estacional} (este mes es{' '}
                {item.factor_estacional > 1 ? 'más alto' : 'más bajo'} que el promedio)
              </TooltipContent>
            </Tooltip>
          )}{' '}
          <TendenciaIcon t={item.tendencia} />
        </TableCell>

        {/* Último precio */}
        <TableCell className="text-right">
          <span>{item.precio_ultimo != null ? `$${item.precio_ultimo.toFixed(2)}` : '—'}</span>
          {hayMasBarato && precioMasBarato !== null && (
            <PrecioComparativo otros={item.otros_proveedores} />
          )}
        </TableCell>

        {/* Cantidad sugerida / editable */}
        <TableCell className="text-right">
          <input
            type="number"
            min={0}
            value={cantidadPedido}
            onChange={e => onCantidadChange(Math.max(0, parseInt(e.target.value) || 0))}
            className="w-20 text-right border rounded px-2 py-0.5 text-sm bg-background"
          />
        </TableCell>

        {/* Costo estimado */}
        <TableCell className="text-right font-semibold text-sm">
          ${(cantidadPedido * (item.precio_ultimo ?? 0)).toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </TableCell>

        {/* Expandir */}
        <TableCell>
          {tieneAlternativas && (
            <button
              onClick={() => setExpanded(v => !v)}
              className="text-muted-foreground hover:text-foreground"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          )}
        </TableCell>
      </TableRow>

      {/* Fila expandida: comparación de precios */}
      <AnimatePresence>
        {expanded && (
          <TableRow>
            <TableCell colSpan={11} className="p-0">
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-6 py-3 bg-muted/30 border-t">
                  <p className="text-xs font-semibold text-muted-foreground mb-2">
                    Comparación de precios para este SKU:
                  </p>
                  <div className="flex gap-4 flex-wrap">
                    {item.otros_proveedores
                      .slice()
                      .sort((a, b) => a.precio_compra - b.precio_compra)
                      .map(p => (
                        <div
                          key={p.proveedor}
                          className={cn(
                            'text-xs px-3 py-2 rounded-md border',
                            p.es_proveedor_principal
                              ? 'border-primary bg-primary/10 font-semibold'
                              : 'border-border bg-background',
                          )}
                        >
                          <div>{p.proveedor}</div>
                          <div className="font-bold">${p.precio_compra.toFixed(2)}</div>
                          <div className="text-muted-foreground">
                            {new Date(p.fecha_ultima_compra).toLocaleDateString()}
                          </div>
                          {p.es_proveedor_principal && (
                            <div className="text-primary text-xs">Principal</div>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              </motion.div>
            </TableCell>
          </TableRow>
        )}
      </AnimatePresence>
    </>
  );
}

// ─── página principal ─────────────────────────────────────────────────────────

type FiltroUrgencia = 'todos' | 'urgente' | 'alta' | 'media' | 'baja';

export function Compras() {
  const [proveedorSeleccionado, setProveedorSeleccionado] = useState<string | null>(null);
  const [filtroUrgencia, setFiltroUrgencia] = useState<FiltroUrgencia>('todos');
  const [pedido, setPedido] = useState<Record<string, number>>({});   // nombre → cantidad

  const { data: urgencias, isLoading: loadingUrgencias, refetch: refetchUrgencias } =
    useUrgenciasProveedor();
  const { data: sugerencias, isLoading: loadingSugerencias } =
    useSugerenciasV2(proveedorSeleccionado ?? undefined);
  const exportPedido = useExportPedido();

  // Cuando cambia el proveedor, reiniciamos el pedido
  const handleProveedorClick = (prov: string) => {
    const nuevo = prov === proveedorSeleccionado ? null : prov;
    setProveedorSeleccionado(nuevo);
    setPedido({});
  };

  // Sugerencias filtradas por urgencia
  const lista: Sugerencia[] = useMemo(() => {
    const raw: Sugerencia[] = Array.isArray(sugerencias) ? sugerencias : [];
    if (filtroUrgencia === 'todos') return raw;
    return raw.filter(s => s.urgencia === filtroUrgencia);
  }, [sugerencias, filtroUrgencia]);

  // Inicializar cantidad pedido con el sugerido
  const getCantidad = (nombre: string, sugerido: number) =>
    pedido[nombre] !== undefined ? pedido[nombre] : sugerido;

  const itemsMarcados = useMemo(
    () => Object.entries(pedido).filter(([, qty]) => qty > 0),
    [pedido]
  );

  const costoTotalPedido = useMemo(() => {
    return itemsMarcados.reduce((acc, [nombre, qty]) => {
      const item = lista.find(s => s.nombre === nombre);
      return acc + qty * (item?.precio_ultimo ?? 0);
    }, 0);
  }, [itemsMarcados, lista]);

  const handleCheck = (nombre: string, sugerido: number, checked: boolean) => {
    setPedido(prev => ({ ...prev, [nombre]: checked ? sugerido : 0 }));
  };

  const handleExport = () => {
    if (!proveedorSeleccionado) return;
    exportPedido.mutate(proveedorSeleccionado);
  };

  const isLoading = loadingUrgencias || loadingSugerencias;

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Compras</h1>
          <p className="text-muted-foreground">
            Qué pedir, a quién, y cuánto — basado en 40 meses de historial real
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetchUrgencias()}
          disabled={loadingUrgencias}
        >
          <RefreshCw className={cn('h-4 w-4 mr-2', loadingUrgencias && 'animate-spin')} />
          Actualizar
        </Button>
      </motion.div>

      {/* Selector de proveedor */}
      <div className="space-y-4">
        <div className="flex items-center gap-3 flex-wrap">
          {loadingUrgencias ? (
            <Skeleton className="h-10 w-[280px]" />
          ) : (
            <Select
              value={proveedorSeleccionado ?? ''}
              onValueChange={(v) => { setProveedorSeleccionado(v); setPedido({}); setFiltroUrgencia('todos'); }}
            >
              <SelectTrigger className="w-[280px]">
                <SelectValue placeholder="Seleccioná un proveedor…" />
              </SelectTrigger>
              <SelectContent>
                {(urgencias as UrgenciaProveedor[] | undefined)?.length === 0 && (
                  <SelectItem value="__empty__" disabled>Sin datos de proveedores</SelectItem>
                )}
                {(urgencias as UrgenciaProveedor[] | undefined)?.map(prov => (
                  <SelectItem key={prov.proveedor} value={prov.proveedor}>
                    <span className="flex items-center gap-2">
                      {prov.proveedor}
                      {prov.urgente > 0 && (
                        <span className="text-xs text-red-600 font-semibold">🔴 {prov.urgente}</span>
                      )}
                      {prov.alta > 0 && (
                        <span className="text-xs text-orange-500 font-semibold">🟠 {prov.alta}</span>
                      )}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {proveedorSeleccionado && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setProveedorSeleccionado(null); setPedido({}); }}
            >
              <X className="h-4 w-4 mr-1" />
              Limpiar
            </Button>
          )}
        </div>

        {/* Tarjetas resumen de proveedores */}
        {!loadingUrgencias && (urgencias as UrgenciaProveedor[] | undefined)?.length ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {(urgencias as UrgenciaProveedor[]).map(prov => (
              <ProveedorCard
                key={prov.proveedor}
                prov={prov}
                selected={prov.proveedor === proveedorSeleccionado}
                onClick={() => handleProveedorClick(prov.proveedor)}
              />
            ))}
          </div>
        ) : loadingUrgencias ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-[100px]" />
            ))}
          </div>
        ) : null}
      </div>

      {/* Panel de proveedor seleccionado */}
      <AnimatePresence mode="wait">
        {proveedorSeleccionado && (
          <motion.div
            key={proveedorSeleccionado}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-4"
          >
            {/* Barra de acciones */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold">{proveedorSeleccionado}</span>
                {/* Filtros de urgencia */}
                {(['todos', 'urgente', 'alta', 'media', 'baja'] as FiltroUrgencia[]).map(u => (
                  <button
                    key={u}
                    onClick={() => setFiltroUrgencia(u)}
                    className={cn(
                      'text-xs px-3 py-1 rounded-full border transition-all',
                      filtroUrgencia === u
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'border-border hover:border-primary',
                    )}
                  >
                    {u === 'todos' ? 'Todos' : urgenciaConfig[u]?.label ?? u}
                    {u !== 'todos' && (
                      <span className="ml-1 opacity-70">
                        ({lista.filter(s => s.urgencia === u).length || (Array.isArray(sugerencias) ? (sugerencias as Sugerencia[]).filter(s => s.urgencia === u).length : 0)})
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Resumen del pedido + exportar */}
              <div className="flex items-center gap-3">
                {itemsMarcados.length > 0 && (
                  <div className="text-sm text-muted-foreground">
                    <span className="font-semibold text-foreground">{itemsMarcados.length}</span> ítems seleccionados ·{' '}
                    <span className="font-semibold text-primary">
                      ${costoTotalPedido.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                )}
                <Button
                  size="sm"
                  onClick={handleExport}
                  disabled={exportPedido.isPending}
                >
                  <Download className={cn('h-4 w-4 mr-2', exportPedido.isPending && 'animate-spin')} />
                  Exportar pedido Excel
                </Button>
              </div>
            </div>

            {/* Tabla */}
            {loadingSugerencias ? (
              <Skeleton className="h-[400px]" />
            ) : lista.length === 0 ? (
              <Card>
                <CardContent className="py-12 flex flex-col items-center gap-3 text-muted-foreground">
                  <Package className="h-10 w-10" />
                  <p>
                    {filtroUrgencia === 'todos'
                      ? 'No hay productos con necesidad de reposición para este proveedor'
                      : `No hay productos con urgencia "${urgenciaConfig[filtroUrgencia]?.label}" para este proveedor`}
                  </p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ShoppingCart className="h-5 w-5" />
                    {lista.length} producto{lista.length !== 1 ? 's' : ''}
                    {filtroUrgencia !== 'todos' && ` · ${urgenciaConfig[filtroUrgencia]?.label}`}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-8"></TableHead>
                          <TableHead>Urgencia</TableHead>
                          <TableHead>Producto</TableHead>
                          <TableHead>ABC</TableHead>
                          <TableHead className="text-right">Stock</TableHead>
                          <TableHead className="text-right">Días</TableHead>
                          <TableHead className="text-right">Velocidad</TableHead>
                          <TableHead className="text-right">Último precio</TableHead>
                          <TableHead className="text-right">Cant. pedido</TableHead>
                          <TableHead className="text-right">Costo est.</TableHead>
                          <TableHead className="w-8"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {lista.map(item => (
                          <FilaSugerencia
                            key={item.nombre}
                            item={item}
                            checked={(pedido[item.nombre] ?? 0) > 0}
                            cantidadPedido={getCantidad(item.nombre, item.cantidad_sugerida)}
                            onCheck={checked => handleCheck(item.nombre, item.cantidad_sugerida, checked)}
                            onCantidadChange={qty => setPedido(prev => ({ ...prev, [item.nombre]: qty }))}
                          />
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Alerta si hay productos sin precio */}
            {lista.some(s => !s.precio_ultimo) && (
              <div className="flex items-center gap-2 text-sm text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 px-4 py-2 rounded-md">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                Algunos productos no tienen precio de compra registrado. El costo estimado puede estar incompleto.
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Estado inicial — sin proveedor seleccionado */}
      {!proveedorSeleccionado && !isLoading && (
        <Card>
          <CardContent className="py-16 flex flex-col items-center gap-3 text-muted-foreground">
            <ShoppingCart className="h-12 w-12 opacity-30" />
            <p className="text-lg">Seleccioná un proveedor arriba para ver sus productos</p>
            <p className="text-sm">
              Los productos están ordenados por urgencia de reposición según historial de 40 meses
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

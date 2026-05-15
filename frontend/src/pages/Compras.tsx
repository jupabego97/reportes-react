import { useState, useMemo, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ShoppingCart,
  Download,
  AlertTriangle,
  Package,
  Search,
  Target,
  Truck,
  ClipboardList,
  CheckSquare,
  Eraser,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Input } from '../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { FilterPanel } from '../components/filters/FilterPanel';
import { ProductLink } from '../components/ProductLink';
import { MetricTooltip } from '../components/ui/metric-tooltip';
import { useSugerenciasCompra } from '../hooks/useApi';
import { useFiltersStore } from '../stores/useFiltersStore';
import { apiService, type FilterParams } from '../services/api';
import {
  CLASIFICACIONES_ABC,
  CURVA_A,
  PRIORIDAD_URGENCIA,
  PRIORIDADES_V1,
  filtrarPorAbc,
  normalizarAbc,
  useProveedoresCardResumen,
  useProveedoresUrgenciaAgrupados,
  useUrgenciaConfig,
  useUrgenciasCompraRows,
  type ClasificacionAbc,
  type ProveedorCardResumen,
  type SugerenciaCompraRow,
} from '../hooks/useUrgencias';
import { cn, exportToCSV, formatCurrency, formatNumber } from '../lib/utils';

const STORAGE_KEY = 'compras:pedido-v1';

type VentanaDecision = 'hoy' | '48h' | '7d';
type FiltroPrioridad = 'todos' | (typeof PRIORIDADES_V1)[number];
type FiltroAbc = 'todos' | ClasificacionAbc;

const abcBadgeVariant: Record<ClasificacionAbc, 'default' | 'secondary' | 'outline'> = {
  A: 'default',
  B: 'secondary',
  C: 'outline',
};

type StoredCompras = {
  pedido: Record<string, number>;
  proveedorSeleccionado: string | null;
};

function useFilterParamsLocal(): FilterParams {
  const fechaInicio = useFiltersStore((s) => s.fechaInicio);
  const fechaFin = useFiltersStore((s) => s.fechaFin);
  const productos = useFiltersStore((s) => s.productos);
  const vendedores = useFiltersStore((s) => s.vendedores);
  const familias = useFiltersStore((s) => s.familias);
  const metodos = useFiltersStore((s) => s.metodos);
  const proveedores = useFiltersStore((s) => s.proveedores);
  const precioMin = useFiltersStore((s) => s.precioMin);
  const precioMax = useFiltersStore((s) => s.precioMax);

  return useMemo(
    () => ({
      fecha_inicio: fechaInicio || undefined,
      fecha_fin: fechaFin || undefined,
      productos: productos.length > 0 ? productos : undefined,
      vendedores: vendedores.length > 0 ? vendedores : undefined,
      familias: familias.length > 0 ? familias : undefined,
      metodos: metodos.length > 0 ? metodos : undefined,
      proveedores: proveedores.length > 0 ? proveedores : undefined,
      precio_min: precioMin || undefined,
      precio_max: precioMax || undefined,
    }),
    [fechaInicio, fechaFin, productos, vendedores, familias, metodos, proveedores, precioMin, precioMax]
  );
}

function DiasStockCell({ dias }: { dias: number }) {
  const color =
    dias <= 7 ? 'text-red-600 font-bold' :
    dias <= 14 ? 'text-orange-500 font-semibold' :
    dias <= 30 ? 'text-yellow-600' : 'text-green-600';
  return <span className={color}>{dias >= 999 ? '∞' : dias.toFixed(0)}</span>;
}

function PrioridadBadge({ prioridad }: { prioridad?: string }) {
  const cfg = useUrgenciaConfig(prioridad);
  return <Badge variant={cfg.badgeVariant}>{prioridad || cfg.label}</Badge>;
}

function TendenciaCell({ tendencia }: { tendencia?: string }) {
  if (tendencia === 'creciente') {
    return (
      <span className="inline-flex items-center gap-1 text-green-600 text-xs">
        <TrendingUp className="h-3.5 w-3.5" /> Crec.
      </span>
    );
  }
  if (tendencia === 'decreciente') {
    return (
      <span className="inline-flex items-center gap-1 text-red-500 text-xs">
        <TrendingDown className="h-3.5 w-3.5" /> Decr.
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-muted-foreground text-xs">
      <Minus className="h-3.5 w-3.5" /> Est.
    </span>
  );
}

function FiltroChips<T extends string>({
  label,
  value,
  options,
  onChange,
  renderLabel,
}: {
  label: string;
  value: T;
  options: readonly T[];
  onChange: (v: T) => void;
  renderLabel?: (opt: T) => string;
}) {
  return (
    <motion.div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground font-medium">{label}</span>
      <button
        type="button"
        onClick={() => onChange('todos' as T)}
        className={cn(
          'text-xs px-3 py-1 rounded-full border transition-all',
          value === 'todos'
            ? 'bg-primary text-primary-foreground border-primary'
            : 'border-border hover:border-primary'
        )}
      >
        Todos
      </button>
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={cn(
            'text-xs px-3 py-1 rounded-full border transition-all',
            value === opt
              ? 'bg-primary text-primary-foreground border-primary'
              : 'border-border hover:border-primary'
          )}
        >
          {renderLabel ? renderLabel(opt) : opt}
        </button>
      ))}
    </motion.div>
  );
}

function ProveedorCard({
  prov,
  selected,
  onClick,
}: {
  prov: ProveedorCardResumen;
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
                : 'border-border'
        )}
      >
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-semibold truncate">{prov.proveedor}</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <motion.div className="flex gap-2 flex-wrap">
            {prov.urgente > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 font-semibold">
                🔴 {prov.urgente}
              </span>
            )}
            {prov.alta > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 font-semibold">
                🟠 {prov.alta}
              </span>
            )}
            {prov.media > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400">
                🟡 {prov.media}
              </span>
            )}
            {prov.urgente === 0 && prov.alta === 0 && prov.media === 0 && (
              <span className="text-xs text-muted-foreground">✓ Sin urgencias</span>
            )}
          </motion.div>
          {prov.costo > 0 && (
            <p className="text-xs text-muted-foreground mt-2">
              Inversión: <span className="font-semibold">{formatCurrency(prov.costo)}</span>
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function Compras() {
  const filters = useFilterParamsLocal();
  const { data: sugerencias, isLoading, error } = useSugerenciasCompra();

  const [ventana, setVentana] = useState<VentanaDecision>('hoy');
  const [busqueda, setBusqueda] = useState('');
  const [filtroPrioridad, setFiltroPrioridad] = useState<FiltroPrioridad>('todos');
  const [filtroAbc, setFiltroAbc] = useState<FiltroAbc>('todos');
  const [proveedorSeleccionado, setProveedorSeleccionado] = useState<string | null>(null);
  const [pedido, setPedido] = useState<Record<string, number>>({});
  const [exportingExcel, setExportingExcel] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  const umbralDias = ventana === 'hoy' ? 1 : ventana === '48h' ? 2 : 7;

  const tituloVentana =
    ventana === 'hoy' ? 'Comprar hoy' : ventana === '48h' ? 'Comprar en 48h' : 'Comprar en 7 días';

  const rows: SugerenciaCompraRow[] = useMemo(
    () => (Array.isArray(sugerencias) ? sugerencias : []),
    [sugerencias]
  );

  const nombresValidos = useMemo(() => new Set(rows.map((r) => r.nombre).filter(Boolean)), [rows]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setHydrated(true);
        return;
      }
      const parsed = JSON.parse(raw) as StoredCompras;
      if (parsed.proveedorSeleccionado) {
        setProveedorSeleccionado(parsed.proveedorSeleccionado);
      }
      if (parsed.pedido && typeof parsed.pedido === 'object') {
        const limpio: Record<string, number> = {};
        for (const [nombre, qty] of Object.entries(parsed.pedido)) {
          if (nombresValidos.has(nombre) && qty > 0) {
            limpio[nombre] = qty;
          }
        }
        setPedido(limpio);
      }
    } catch {
      /* ignore corrupt storage */
    }
    setHydrated(true);
  }, [nombresValidos]);

  useEffect(() => {
    if (!hydrated) return;
    const payload: StoredCompras = { pedido, proveedorSeleccionado };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [pedido, proveedorSeleccionado, hydrated]);

  const comprarVentana = useUrgenciasCompraRows(rows, { umbralDias, busqueda });
  const proveedoresPrioritarios = useProveedoresUrgenciaAgrupados(comprarVentana);
  const proveedoresCards = useProveedoresCardResumen(rows);

  const inversionVentana = comprarVentana.reduce(
    (acc, s) => acc + Number(s.costo_estimado || 0),
    0
  );

  const inversionSoloA = useMemo(
    () =>
      filtrarPorAbc(comprarVentana, 'A').reduce(
        (acc, s) => acc + Number(s.costo_estimado || 0),
        0
      ),
    [comprarVentana]
  );

  const listaProveedorRaw = useMemo(() => {
    if (!proveedorSeleccionado) return [];
    const q = busqueda.toLowerCase().trim();
    return rows
      .filter((s) => (s.proveedor || 'Sin proveedor') === proveedorSeleccionado)
      .filter((s) => filtroPrioridad === 'todos' || s.prioridad === filtroPrioridad)
      .filter(
        (s) =>
          !q ||
          (s.nombre || '').toLowerCase().includes(q) ||
          (s.proveedor || '').toLowerCase().includes(q)
      )
      .sort((a, b) => (a.dias_stock ?? 999) - (b.dias_stock ?? 999));
  }, [rows, proveedorSeleccionado, filtroPrioridad, busqueda]);

  const listaProveedor = useMemo(
    () => filtrarPorAbc(listaProveedorRaw, filtroAbc),
    [listaProveedorRaw, filtroAbc]
  );

  const filasAccion = useMemo(() => {
    if (proveedorSeleccionado) return listaProveedor;
    return filtrarPorAbc(comprarVentana, filtroAbc);
  }, [proveedorSeleccionado, listaProveedor, comprarVentana, filtroAbc]);

  const itemsSeleccionados = useMemo(
    () => Object.entries(pedido).filter(([, qty]) => qty > 0),
    [pedido]
  );

  const costoPedidoEditado = useMemo(() => {
    return itemsSeleccionados.reduce((acc, [nombre, qty]) => {
      const item = rows.find((s) => s.nombre === nombre);
      const precio = Number(item?.precio_compra ?? 0);
      return acc + qty * precio;
    }, 0);
  }, [itemsSeleccionados, rows]);

  const unidadesPedido = useMemo(
    () => itemsSeleccionados.reduce((acc, [, qty]) => acc + qty, 0),
    [itemsSeleccionados]
  );

  const handleProveedorClick = (prov: string) => {
    setProveedorSeleccionado((prev) => (prev === prov ? null : prov));
  };

  const handleCheck = (nombre: string, sugerido: number, checked: boolean) => {
    setPedido((prev) => ({ ...prev, [nombre]: checked ? sugerido : 0 }));
  };

  const marcarFilas = (predicado: (item: SugerenciaCompraRow) => boolean, mensajeOk: string, mensajeVacio: string) => {
    const next = { ...pedido };
    let count = 0;
    for (const item of filasAccion) {
      if (predicado(item)) {
        next[item.nombre!] = Number(item.cantidad_sugerida || 0);
        count += 1;
      }
    }
    setPedido(next);
    toast.success(count > 0 ? `${count} ${mensajeOk}` : mensajeVacio);
  };

  const handleMarcarUrgentes = () => {
    marcarFilas(
      (item) => PRIORIDAD_URGENCIA.has(item.prioridad || ''),
      'ítems urgentes marcados',
      'No hay ítems urgentes visibles con los filtros actuales'
    );
  };

  const handleMarcarCurvaA = () => {
    marcarFilas(
      (item) => CURVA_A.has(normalizarAbc(item.clasificacion_abc)),
      'ítems curva A marcados',
      'No hay ítems curva A visibles con los filtros actuales'
    );
  };

  const handleMarcarAUrgentes = () => {
    marcarFilas(
      (item) =>
        CURVA_A.has(normalizarAbc(item.clasificacion_abc)) &&
        PRIORIDAD_URGENCIA.has(item.prioridad || ''),
      'ítems curva A urgentes marcados',
      'No hay ítems curva A urgentes/altos visibles'
    );
  };

  const handleLimpiarSeleccion = () => {
    setPedido({});
    toast.success('Selección limpiada');
  };

  const handleExportCSV = useCallback(() => {
    const lineas = itemsSeleccionados
      .map(([nombre, qty]) => {
        const item = rows.find((s) => s.nombre === nombre);
        if (!item) return null;
        const precio = Number(item.precio_compra ?? 0);
        return {
          producto: nombre,
          proveedor: item.proveedor || '',
          prioridad: item.prioridad || '',
          abc: item.clasificacion_abc || '',
          cantidad: String(qty),
          precio: String(precio),
          costo: String(qty * precio),
        };
      })
      .filter(Boolean) as Array<Record<string, string>>;

    if (lineas.length === 0) {
      toast.error('Seleccioná al menos un producto con cantidad > 0');
      return;
    }

    const headers = [
      'Producto',
      'Proveedor',
      'Prioridad',
      'ABC',
      'Cantidad',
      'Precio compra',
      'Costo estimado',
    ];
    const csvRows = lineas.map((l) => [
      l.producto,
      l.proveedor,
      l.prioridad,
      l.abc,
      l.cantidad,
      l.precio,
      l.costo,
    ]);
    const prov =
      proveedorSeleccionado?.replace(/[^\w-]+/g, '_') || 'pedido';
    exportToCSV(headers, csvRows, `pedido_${prov}_${new Date().toISOString().slice(0, 10)}.csv`);
    toast.success('Pedido exportado como CSV');
  }, [itemsSeleccionados, rows, proveedorSeleccionado]);

  const handleExportExcelCompleto = async () => {
    if (!proveedorSeleccionado || proveedorSeleccionado === 'Sin proveedor') {
      toast.error('Seleccioná un proveedor para exportar la sugerencia completa');
      return;
    }
    setExportingExcel(true);
    try {
      const blob = await apiService.exportOrdenCompraExcel(proveedorSeleccionado, filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sugerencia_${proveedorSeleccionado.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Excel de sugerencia completa descargado');
    } catch (e) {
      toast.error(`Error al exportar Excel: ${(e as Error).message}`);
    } finally {
      setExportingExcel(false);
    }
  };

  if (error) {
    return (
      <motion.div className="text-center py-8 text-destructive">
        Error al cargar compras: {error.message}
      </motion.div>
    );
  }

  return (
    <div className="space-y-6 pb-28">
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Compras</h1>
        <p className="text-muted-foreground">
          Qué pedir, a quién y cuánto — prioridad ABC con pedido editable
        </p>
      </motion.div>

      <FilterPanel />

      {isLoading ? (
        <motion.div className="grid gap-4">
          <motion.div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-[100px]" />
            ))}
          </motion.div>
          <Skeleton className="h-[320px]" />
        </motion.div>
      ) : (
        <>
          <motion.div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  {tituloVentana}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <motion.div className="text-2xl font-bold">{formatNumber(comprarVentana.length)}</motion.div>
                <p className="text-xs text-muted-foreground">Productos en la ventana activa</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <Truck className="h-4 w-4" />
                  Proveedores prioritarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                <motion.div className="text-2xl font-bold">
                  {formatNumber(proveedoresPrioritarios.length)}
                </motion.div>
                <p className="text-xs text-muted-foreground">Con urgencia en esta ventana</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <ClipboardList className="h-4 w-4" />
                  Inversión sugerida
                  <MetricTooltip text="Suma de costo_estimado de productos en la ventana activa." />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{formatCurrency(inversionVentana)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Solo curva A: <span className="font-semibold">{formatCurrency(inversionSoloA)}</span>
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <CheckSquare className="h-4 w-4" />
                  Ítems seleccionados
                </CardTitle>
              </CardHeader>
              <CardContent>
                <motion.div className="text-2xl font-bold">{formatNumber(itemsSeleccionados.length)}</motion.div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <ShoppingCart className="h-4 w-4" />
                  Costo pedido editado
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{formatCurrency(costoPedidoEditado)}</div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground mr-1">Ventana:</span>
            {(['hoy', '48h', '7d'] as VentanaDecision[]).map((v) => (
              <Button
                key={v}
                size="sm"
                variant={ventana === v ? 'default' : 'outline'}
                onClick={() => setVentana(v)}
              >
                {v === 'hoy' ? 'Hoy' : v === '48h' ? '48h' : '7 días'}
              </Button>
            ))}
            <div className="relative ml-auto w-full sm:w-72">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar producto o proveedor…"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="pl-9 h-9"
              />
            </div>
          </motion.div>

          <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
            <FiltroChips
              label="Prioridad"
              value={filtroPrioridad}
              options={PRIORIDADES_V1}
              onChange={setFiltroPrioridad}
            />
            <FiltroChips
              label="Curva ABC"
              value={filtroAbc}
              options={CLASIFICACIONES_ABC}
              onChange={setFiltroAbc}
            />
            <p className="text-xs text-muted-foreground">
              La curva ABC usa el mismo periodo que los filtros globales de arriba.
            </p>
          </div>

          {proveedoresCards.length > 0 && (
            <motion.div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {proveedoresCards.map((prov) => (
                <ProveedorCard
                  key={prov.proveedor}
                  prov={prov}
                  selected={prov.proveedor === proveedorSeleccionado}
                  onClick={() => handleProveedorClick(prov.proveedor)}
                />
              ))}
            </motion.div>
          )}

          {proveedorSeleccionado ? (
            <motion.div
              key={proveedorSeleccionado}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-lg">{proveedorSeleccionado}</span>
                <Button variant="ghost" size="sm" onClick={() => setProveedorSeleccionado(null)}>
                  Cambiar proveedor
                </Button>
              </div>

              {listaProveedor.length === 0 ? (
                <Card>
                  <CardContent className="py-12 flex flex-col items-center gap-3 text-muted-foreground">
                    <Package className="h-10 w-10" />
                    <p>No hay productos para este proveedor con los filtros actuales</p>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <ShoppingCart className="h-5 w-5" />
                      {listaProveedor.length} producto{listaProveedor.length !== 1 ? 's' : ''}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-10" />
                            <TableHead>Urgencia</TableHead>
                            <TableHead>Producto</TableHead>
                            <TableHead>ABC</TableHead>
                            <TableHead>Tendencia</TableHead>
                            <TableHead className="text-right">
                              ROI est.
                              <MetricTooltip text="Margen unitario estimado × cantidad sugerida." />
                            </TableHead>
                            <TableHead className="text-right">Stock</TableHead>
                            <TableHead className="text-right">
                              Días
                              <MetricTooltip text="Stock / venta diaria (30 días)." />
                            </TableHead>
                            <TableHead className="text-right">ROP</TableHead>
                            <TableHead className="text-right">Cant. sugerida</TableHead>
                            <TableHead className="text-right">Costo est.</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {listaProveedor.map((item, idx) => {
                            const nombre = item.nombre || `row-${idx}`;
                            const sugerido = Number(item.cantidad_sugerida || 0);
                            const qty = pedido[nombre] ?? 0;
                            const checked = qty > 0;
                            const precio = Number(item.precio_compra ?? 0);
                            return (
                              <TableRow
                                key={nombre}
                                className={cn(checked && 'bg-primary/5')}
                              >
                                <TableCell>
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={(e) =>
                                      handleCheck(nombre, sugerido, e.target.checked)
                                    }
                                    className="h-4 w-4 rounded border-gray-300 cursor-pointer"
                                  />
                                </TableCell>
                                <TableCell>
                                  <PrioridadBadge prioridad={item.prioridad} />
                                </TableCell>
                                <TableCell className="max-w-[220px]">
                                  <ProductLink
                                    nombre={nombre}
                                    className="truncate block max-w-[220px]"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Badge variant={abcBadgeVariant[normalizarAbc(item.clasificacion_abc)]}>
                                    {normalizarAbc(item.clasificacion_abc)}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <TendenciaCell tendencia={item.tendencia} />
                                </TableCell>
                                <TableCell className="text-right text-sm">
                                  {item.roi_estimado != null
                                    ? formatCurrency(Number(item.roi_estimado))
                                    : '—'}
                                </TableCell>
                                <TableCell className="text-right">
                                  {formatNumber(Number(item.cantidad_disponible ?? 0))}
                                </TableCell>
                                <TableCell className="text-right">
                                  <DiasStockCell dias={Number(item.dias_stock ?? 999)} />
                                </TableCell>
                                <TableCell className="text-right">
                                  {item.punto_reorden ?? '—'}
                                </TableCell>
                                <TableCell className="text-right">
                                  <input
                                    type="number"
                                    min={0}
                                    value={checked ? qty : sugerido}
                                    onChange={(e) => {
                                      const v = Math.max(0, parseInt(e.target.value, 10) || 0);
                                      setPedido((prev) => ({ ...prev, [nombre]: v }));
                                    }}
                                    onFocus={() => {
                                      if (!checked) {
                                        setPedido((prev) => ({
                                          ...prev,
                                          [nombre]: sugerido,
                                        }));
                                      }
                                    }}
                                    className="w-20 text-right border rounded px-2 py-0.5 text-sm bg-background ml-auto block"
                                  />
                                </TableCell>
                                <TableCell className="text-right font-medium">
                                  {formatCurrency(
                                    checked ? qty * precio : Number(item.costo_estimado ?? 0)
                                  )}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {listaProveedor.some((s) => !s.precio_compra) && (
                <div className="flex items-center gap-2 text-sm text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 px-4 py-2 rounded-md">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  Algunos productos no tienen precio de compra; el costo estimado puede estar incompleto.
                </div>
              )}
            </motion.div>
          ) : (
            <Card>
              <CardContent className="py-16 flex flex-col items-center gap-3 text-muted-foreground">
                <ShoppingCart className="h-12 w-12 opacity-30" />
                <p className="text-lg">Seleccioná un proveedor para armar el pedido</p>
                <p className="text-sm text-center max-w-md">
                  Las cards muestran urgencias por proveedor. La ventana (hoy / 48h / 7d) afecta los KPIs superiores.
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <div className="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:left-[var(--sidebar-width,0px)]">
        <motion.div className="max-w-[1600px] mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <motion.div className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{itemsSeleccionados.length}</span> ítems ·{' '}
            <span className="font-semibold text-foreground">{formatNumber(unidadesPedido)}</span> unidades ·{' '}
            <span className="font-semibold text-primary">{formatCurrency(costoPedidoEditado)}</span>
          </motion.div>
          <motion.div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={handleMarcarUrgentes}>
              <CheckSquare className="h-4 w-4 mr-1" />
              Marcar urgentes
            </Button>
            <Button variant="outline" size="sm" onClick={handleMarcarCurvaA}>
              Marcar curva A
            </Button>
            <Button variant="outline" size="sm" onClick={handleMarcarAUrgentes}>
              Marcar A urgentes
            </Button>
            <Button variant="outline" size="sm" onClick={handleLimpiarSeleccion}>
              <Eraser className="h-4 w-4 mr-1" />
              Limpiar selección
            </Button>
            <Button size="sm" onClick={handleExportCSV} disabled={itemsSeleccionados.length === 0}>
              <Download className="h-4 w-4 mr-1" />
              Exportar pedido CSV
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExportExcelCompleto}
              disabled={!proveedorSeleccionado || exportingExcel}
            >
              <Download className={cn('h-4 w-4 mr-1', exportingExcel && 'animate-pulse')} />
              Excel sugerencia completa
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}

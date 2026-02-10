import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Target, Truck, ClipboardList, Search, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Skeleton } from '../components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { useGenerarOrdenCompra, useResumenComprasProveedores, useSugerenciasCompra } from '../hooks/useApi';
import { formatCurrency, formatNumber, exportToCSV } from '../lib/utils';
import { MetricTooltip } from '../components/ui/metric-tooltip';

const prioridadesAccionHoy = new Set(['🔴 Urgente', '🟠 Alta']);
type VentanaDecision = 'hoy' | '48h' | '7d';

type OrdenCompra = {
  proveedor: string;
  fecha: string;
  total_productos: number;
  total_unidades: number;
  costo_total: number;
  items: Array<{
    nombre: string;
    cantidad_sugerida: number;
    costo_estimado: number;
    prioridad: string;
  }>;
};

export function CentroDecisiones() {
  const { data: sugerencias, isLoading, error } = useSugerenciasCompra();
  const { data: resumenProveedores } = useResumenComprasProveedores();
  const generarOrden = useGenerarOrdenCompra();
  const [ordenActual, setOrdenActual] = useState<OrdenCompra | null>(null);
  const [ventana, setVentana] = useState<VentanaDecision>('hoy');
  const [busqueda, setBusqueda] = useState('');

  const umbralDias = useMemo(() => {
    if (ventana === 'hoy') return 1;
    if (ventana === '48h') return 2;
    return 7;
  }, [ventana]);

  const tituloVentana = useMemo(() => {
    if (ventana === 'hoy') return 'Comprar Hoy';
    if (ventana === '48h') return 'Comprar en 48h';
    return 'Comprar en 7 dias';
  }, [ventana]);

  const comprarHoy = useMemo(() => {
    const rows = Array.isArray(sugerencias) ? sugerencias : [];
    const q = busqueda.toLowerCase().trim();
    return rows
      .filter((s: any) => prioridadesAccionHoy.has(s.prioridad) || (s.dias_stock ?? 999) <= umbralDias)
      .filter((s: any) => !q || (s.nombre || '').toLowerCase().includes(q) || (s.proveedor || '').toLowerCase().includes(q))
      .sort((a: any, b: any) => (a.dias_stock ?? 999) - (b.dias_stock ?? 999));
  }, [sugerencias, umbralDias, busqueda]);

  const proveedoresUrgentes = useMemo(() => {
    const map = new Map<string, { proveedor: string; productos: number; unidades: number; costo: number }>();
    for (const s of comprarHoy) {
      const proveedor = s.proveedor || 'Sin proveedor';
      const prev = map.get(proveedor) || {
        proveedor,
        productos: 0,
        unidades: 0,
        costo: 0,
      };
      prev.productos += 1;
      prev.unidades += Number(s.cantidad_sugerida || 0);
      prev.costo += Number(s.costo_estimado || 0);
      map.set(proveedor, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.costo - a.costo);
  }, [comprarHoy]);

  const inversionHoy = comprarHoy.reduce((acc, s: any) => acc + Number(s.costo_estimado || 0), 0);

  const handleExportarOrdenCSV = () => {
    if (!ordenActual) return;
    const headers = ['Item', 'Prioridad', 'Cantidad', 'Costo estimado'];
    const rows = (ordenActual.items || []).map((item) => [
      item.nombre,
      item.prioridad,
      String(item.cantidad_sugerida || 0),
      String(item.costo_estimado || 0),
    ]);
    const proveedorSafe = (ordenActual.proveedor || 'proveedor').replace(/[^\w-]+/g, '_');
    exportToCSV(headers, rows, `orden_compra_${proveedorSafe}_${new Date().toISOString().slice(0, 10)}.csv`);
    toast.success('Orden exportada como CSV');
  };

  const handleGenerarOrden = async (proveedor: string) => {
    if (proveedor === 'Sin proveedor') return;
    if (!window.confirm(`Generar orden de compra para ${proveedor}?`)) return;
    try {
      const data = await generarOrden.mutateAsync({
        proveedor,
        prioridadMinima: '🟠 Alta',
      });
      setOrdenActual(data as OrdenCompra);
      toast.success(`Orden generada para ${proveedor}`);
    } catch {
      toast.error('Error al generar la orden');
    }
  };

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar centro de decisiones: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Centro de Decisiones</h1>
        <p className="text-muted-foreground">
          Decide que comprar hoy, cuando comprar y a quien comprar en un solo lugar.
        </p>
      </motion.div>

      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
          </div>
          <Skeleton className="h-[350px]" />
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  {tituloVentana}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(comprarHoy.length)}</div>
                <p className="text-xs text-muted-foreground">Productos con urgencia real</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <Truck className="h-4 w-4" />
                  Proveedores Prioritarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(proveedoresUrgentes.length)}</div>
                <p className="text-xs text-muted-foreground">A contactar en esta ronda</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                  <ClipboardList className="h-4 w-4" />
                  Inversion Recomendada
                  <MetricTooltip text="Suma de costo_estimado (precio_compra x cantidad_sugerida) de todos los productos en la ventana de decision activa." />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{formatCurrency(inversionHoy)}</div>
                <p className="text-xs text-muted-foreground">Suma de items para la ventana activa</p>
              </CardContent>
            </Card>
          </div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                  {tituloVentana} (momento justo)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center gap-2 mb-4">
                  <Button
                    size="sm"
                    variant={ventana === 'hoy' ? 'default' : 'outline'}
                    onClick={() => setVentana('hoy')}
                  >
                    Hoy
                  </Button>
                  <Button
                    size="sm"
                    variant={ventana === '48h' ? 'default' : 'outline'}
                    onClick={() => setVentana('48h')}
                  >
                    48h
                  </Button>
                  <Button
                    size="sm"
                    variant={ventana === '7d' ? 'default' : 'outline'}
                    onClick={() => setVentana('7d')}
                  >
                    7 dias
                  </Button>
                  <div className="relative ml-auto w-full md:w-64">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Buscar producto o proveedor..."
                      value={busqueda}
                      onChange={(e) => setBusqueda(e.target.value)}
                      className="pl-9 h-9"
                    />
                  </div>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead>Proveedor</TableHead>
                      <TableHead>Prioridad</TableHead>
                      <TableHead className="text-right">Stock</TableHead>
                      <TableHead className="text-right">
                        Dias stock
                        <MetricTooltip text="Stock actual / venta diaria promedio (ultimos 30 dias). Indica cuantos dias dura el inventario actual al ritmo de venta actual." />
                      </TableHead>
                      <TableHead className="text-right">Sugerido</TableHead>
                      <TableHead className="text-right">Costo</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {comprarHoy.slice(0, 25).map((item: any, idx: number) => (
                      <TableRow key={`${item.nombre}-${idx}`}>
                        <TableCell className="font-medium max-w-[220px] truncate" title={item.nombre}>{item.nombre}</TableCell>
                        <TableCell>{item.proveedor || 'Sin proveedor'}</TableCell>
                        <TableCell>
                          <Badge variant={item.prioridad === '🔴 Urgente' ? 'destructive' : 'secondary'}>
                            {item.prioridad}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{formatNumber(item.cantidad_disponible || 0)}</TableCell>
                        <TableCell className="text-right">{Number(item.dias_stock || 0).toFixed(0)}</TableCell>
                        <TableCell className="text-right font-semibold">{formatNumber(item.cantidad_sugerida || 0)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(item.costo_estimado || 0)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle>A quien comprar primero</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {proveedoresUrgentes.map((prov) => (
                    <div key={prov.proveedor} className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 p-3 rounded-lg border">
                      <div className="space-y-1">
                        <div className="font-medium">{prov.proveedor}</div>
                        <div className="text-sm text-muted-foreground">
                          {formatNumber(prov.productos)} productos | {formatNumber(prov.unidades)} unidades | {formatCurrency(prov.costo)}
                        </div>
                      </div>
                      <Button
                        onClick={() => handleGenerarOrden(prov.proveedor)}
                        disabled={generarOrden.isPending || prov.proveedor === 'Sin proveedor'}
                      >
                        {generarOrden.isPending ? (
                          <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Generando...</>
                        ) : (
                          'Generar orden en 1 clic'
                        )}
                      </Button>
                    </div>
                  ))}
                </div>
                {resumenProveedores && Array.isArray(resumenProveedores) && resumenProveedores.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-4">
                    Proveedores detectados en total: {formatNumber(resumenProveedores.length)}
                  </p>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {ordenActual && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card>
                <CardHeader>
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <CardTitle>Orden sugerida: {ordenActual.proveedor}</CardTitle>
                    <Button variant="outline" onClick={handleExportarOrdenCSV}>
                      Exportar orden CSV
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="p-3 rounded border">
                      <div className="text-xs text-muted-foreground">Productos</div>
                      <div className="font-semibold">{formatNumber(ordenActual.total_productos || 0)}</div>
                    </div>
                    <div className="p-3 rounded border">
                      <div className="text-xs text-muted-foreground">Unidades</div>
                      <div className="font-semibold">{formatNumber(ordenActual.total_unidades || 0)}</div>
                    </div>
                    <div className="p-3 rounded border">
                      <div className="text-xs text-muted-foreground">Costo total</div>
                      <div className="font-semibold">{formatCurrency(ordenActual.costo_total || 0)}</div>
                    </div>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Item</TableHead>
                        <TableHead>Prioridad</TableHead>
                        <TableHead className="text-right">Cantidad</TableHead>
                        <TableHead className="text-right">Costo</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(ordenActual.items || []).map((item, idx) => (
                        <TableRow key={`${item.nombre}-${idx}`}>
                          <TableCell>{item.nombre}</TableCell>
                          <TableCell>{item.prioridad}</TableCell>
                          <TableCell className="text-right">{formatNumber(item.cantidad_sugerida || 0)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(item.costo_estimado || 0)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </>
      )}
    </div>
  );
}


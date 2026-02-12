import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ShoppingCart, AlertTriangle, Package, TrendingUp, TrendingDown, Minus, Search, Download } from 'lucide-react';
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
import { useSugerenciasCompra } from '../hooks/useApi';
import { cn, exportToCSV } from '../lib/utils';
import { MetricTooltip } from '../components/ui/metric-tooltip';
import { ProductLink } from '../components/ProductLink';

// Mapeo de prioridades del backend a estilos del frontend
const prioridadConfig: Record<string, { color: 'destructive' | 'secondary' | 'outline' | 'default'; icon: string; label: string }> = {
  '🔴 Urgente': { color: 'destructive', icon: '🔴', label: 'Urgente' },
  '🟠 Alta': { color: 'destructive', icon: '🟠', label: 'Alta' },
  '🟡 Media': { color: 'secondary', icon: '🟡', label: 'Media' },
  '🟢 Baja': { color: 'outline', icon: '🟢', label: 'Baja' },
};

const prioridadesAltas = ['🔴 Urgente', '🟠 Alta'];

function TendenciaIndicator({ tendencia }: { tendencia?: string }) {
  if (tendencia === 'creciente') return <div className="flex items-center gap-1"><TrendingUp className="h-4 w-4 text-green-600" /><span className="text-xs text-green-600">Crece</span></div>;
  if (tendencia === 'decreciente') return <div className="flex items-center gap-1"><TrendingDown className="h-4 w-4 text-red-600" /><span className="text-xs text-red-600">Baja</span></div>;
  return <div className="flex items-center gap-1"><Minus className="h-4 w-4 text-muted-foreground" /><span className="text-xs text-muted-foreground">Estable</span></div>;
}

function AbcBadge({ abc }: { abc?: string }) {
  const variant = abc === 'A' ? 'default' : abc === 'B' ? 'secondary' : 'outline';
  return <Badge variant={variant}>{abc || '-'}</Badge>;
}

export function Compras() {
  const { data, isLoading, error } = useSugerenciasCompra();
  const [busqueda, setBusqueda] = useState('');

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  const sugerencias: any[] = data && Array.isArray(data) ? data : [];

  const sugerenciasFiltradas = useMemo(() => {
    const q = busqueda.toLowerCase().trim();
    if (!q) return sugerencias;
    return sugerencias.filter((s: any) =>
      (s.nombre || '').toLowerCase().includes(q) ||
      (s.proveedor || '').toLowerCase().includes(q) ||
      (s.familia || '').toLowerCase().includes(q)
    );
  }, [sugerencias, busqueda]);

  const handleExportarCSV = () => {
    const headers = ['Prioridad', 'Producto', 'ABC', 'Tendencia', 'Familia', 'Proveedor', 'Stock', 'Venta/dia', 'Demanda proy. 7d', 'Dias stock', 'ROP', 'Sugerido', 'ROI Est.'];
    const rows = sugerencias.map((p: any) => [
      p.prioridad || '',
      p.nombre || '',
      p.clasificacion_abc || '',
      p.tendencia || '',
      p.familia || '',
      p.proveedor || '',
      String(p.cantidad_disponible || 0),
      String(p.venta_diaria || 0),
      String(p.demanda_proyectada_7d ?? ''),
      String(p.dias_stock?.toFixed(0) || 0),
      String(p.punto_reorden ?? ''),
      String(p.cantidad_sugerida || 0),
      String(p.roi_estimado || 0),
    ]);
    exportToCSV(headers, rows, `sugerencias_compra_${new Date().toISOString().slice(0, 10)}.csv`);
    toast.success('Sugerencias exportadas como CSV');
  };

  const inversionTotal = sugerencias.reduce((acc, s) => acc + (s.costo_estimado || 0), 0);
  const roiTotal = sugerencias.reduce((acc, s) => acc + (s.roi_estimado || 0), 0);
  const claseARiesgo = sugerencias.filter((s) => s.clasificacion_abc === 'A' && s.dias_stock <= 7).length;

  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Sugerencias de Compra</h1>
        <p className="text-muted-foreground">
          Productos que necesitan reposición basado en ventas, stock y análisis ABC
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
          </div>
          <Skeleton className="h-[400px]" />
        </div>
      ) : sugerencias.length > 0 ? (
        <>
          {/* Resumen financiero */}
          <div className="grid gap-4 md:grid-cols-3">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Inversión total requerida</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-primary">${inversionTotal.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">{sugerencias.length} productos a reponer</p>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    ROI estimado total
                    <MetricTooltip text="Retorno bruto estimado = (precio_venta - precio_compra) x cantidad_sugerida. Basado en el margen historico del producto." />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-emerald-600">${roiTotal.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">Retorno bruto potencial</p>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className={cn(claseARiesgo > 0 && 'border-red-500/50')}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    Productos clase A en riesgo
                    <MetricTooltip text="Pareto: A = top 80% de ventas (alta rotacion). Estos productos son criticos y no deben quedarse sin stock." />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{claseARiesgo}</div>
                  <p className="text-xs text-muted-foreground mt-1">Stock menor a 7 días</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Resumen por prioridad */}
          <div className="grid gap-4 md:grid-cols-4">
            {Object.entries(prioridadConfig).map(([key, config], index) => {
              const count = sugerencias.filter((s) => s.prioridad === key).length;
              return (
                <motion.div key={key} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>
                  <Card className={cn(prioridadesAltas.includes(key) && 'border-red-500/50')}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <span>{config.icon}</span> Prioridad {config.label}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{count}</div>
                      <p className="text-xs text-muted-foreground">productos a reponer</p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* Productos urgentes */}
          {sugerencias.filter((s) => prioridadesAltas.includes(s.prioridad)).length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card className="border-red-500/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <AlertTriangle className="h-5 w-5" /> Prioridad Alta / Urgente
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {sugerencias
                      .filter((s) => prioridadesAltas.includes(s.prioridad))
                      .slice(0, 6)
                      .map((producto: any, index: number) => (
                        <motion.div key={producto.nombre} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 * index }} className="p-4 rounded-lg border bg-red-500/5 border-red-500/20">
                          <div className="flex items-center justify-between">
                            <div className="font-medium truncate flex-1"><ProductLink nombre={producto.nombre} /></div>
                            <AbcBadge abc={producto.clasificacion_abc} />
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Stock: {producto.cantidad_disponible} | Venta diaria: {producto.venta_diaria}
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge variant="destructive">Comprar: {producto.cantidad_sugerida}</Badge>
                            <TendenciaIndicator tendencia={producto.tendencia} />
                          </div>
                        </motion.div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Top 10 por ROI */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
            <Card>
              <CardHeader>
                <CardTitle>Top 10 productos por ROI estimado</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead>ABC</TableHead>
                      <TableHead>Tendencia</TableHead>
                      <TableHead>Proveedor</TableHead>
                      <TableHead className="text-right">ROI Estimado</TableHead>
                      <TableHead className="text-right">Inversión</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sugerencias
                      .slice()
                      .sort((a, b) => (b.roi_estimado || 0) - (a.roi_estimado || 0))
                      .slice(0, 10)
                      .map((p: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="max-w-[200px]"><ProductLink nombre={p.nombre} className="truncate block" /></TableCell>
                          <TableCell><AbcBadge abc={p.clasificacion_abc} /></TableCell>
                          <TableCell><TendenciaIndicator tendencia={p.tendencia} /></TableCell>
                          <TableCell>{p.proveedor || '-'}</TableCell>
                          <TableCell className="text-right text-emerald-600 font-semibold">${Number(p.roi_estimado || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-right">${Number(p.costo_estimado || 0).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </motion.div>

          {/* Tabla completa */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card>
              <CardHeader>
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <ShoppingCart className="h-5 w-5" /> Todas las Sugerencias de Compra
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <div className="relative w-full md:w-64">
                      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Buscar producto, proveedor o familia..."
                        value={busqueda}
                        onChange={(e) => setBusqueda(e.target.value)}
                        className="pl-9 h-9"
                      />
                    </div>
                    <Button variant="outline" size="sm" onClick={handleExportarCSV}>
                      <Download className="h-4 w-4 mr-1" /> CSV
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Prioridad</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead>
                        ABC
                        <MetricTooltip text="Pareto: A = top 80% de ventas (alta rotacion), B = siguiente 15%, C = ultimo 5%. Los productos A son criticos y no deben quedarse sin stock." />
                      </TableHead>
                      <TableHead>
                        Tendencia
                        <MetricTooltip text="Compara la venta promedio de los ultimos 7 dias vs los 7 dias anteriores. Creciente: +10%, Decreciente: -10%, Estable: entre -10% y +10%." />
                      </TableHead>
                      <TableHead>Familia</TableHead>
                      <TableHead>Proveedor</TableHead>
                      <TableHead className="text-right">Stock</TableHead>
                      <TableHead className="text-right">Venta/dia</TableHead>
                      <TableHead className="text-right">
                        Dem. proy. 7d
                        <MetricTooltip text="Demanda proyectada (unidades) para los proximos 7 dias segun forecast. Cuando disponible, la sugerencia usa esta proyeccion en lugar del historico." />
                      </TableHead>
                      <TableHead className="text-right">
                        Dias stock
                        <MetricTooltip text="Stock actual / venta diaria promedio (ultimos 30 dias). Indica cuantos dias dura el inventario actual al ritmo de venta actual." />
                      </TableHead>
                      <TableHead className="text-right">
                        ROP
                        <MetricTooltip text="Punto de reorden: stock minimo al que debes llegar antes de pedir. ROP = venta_diaria x (lead_time + safety_stock)." />
                      </TableHead>
                      <TableHead className="text-right">Sugerido</TableHead>
                      <TableHead className="text-right">
                        ROI Est.
                        <MetricTooltip text="Retorno bruto estimado = (precio_venta - precio_compra) x cantidad_sugerida. Basado en el margen historico del producto." />
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sugerenciasFiltradas.map((producto: any, index: number) => {
                      const cfg = prioridadConfig[producto.prioridad] || { color: 'default' as const, icon: '', label: producto.prioridad };
                      return (
                        <TableRow key={index}>
                          <TableCell>
                            <Badge variant={cfg.color}>{cfg.icon} {cfg.label}</Badge>
                          </TableCell>
                          <TableCell className="max-w-[180px]"><ProductLink nombre={producto.nombre} className="truncate block" /></TableCell>
                          <TableCell><AbcBadge abc={producto.clasificacion_abc} /></TableCell>
                          <TableCell><TendenciaIndicator tendencia={producto.tendencia} /></TableCell>
                          <TableCell>{producto.familia || '-'}</TableCell>
                          <TableCell>{producto.proveedor || '-'}</TableCell>
                          <TableCell className="text-right">
                            <span className={cn(producto.cantidad_disponible === 0 && 'text-red-600 font-bold')}>
                              {producto.cantidad_disponible}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">{producto.venta_diaria}</TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {producto.demanda_proyectada_7d != null ? producto.demanda_proyectada_7d.toFixed(0) : '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className={cn(
                              producto.dias_stock <= 7 && 'text-red-600',
                              producto.dias_stock > 7 && producto.dias_stock <= 14 && 'text-yellow-600'
                            )}>
                              {producto.dias_stock?.toFixed(0) || 0}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">{producto.punto_reorden ?? '-'}</TableCell>
                          <TableCell className="text-right font-bold text-primary">{producto.cantidad_sugerida}</TableCell>
                          <TableCell className="text-right text-emerald-600">${Number(producto.roi_estimado || 0).toLocaleString()}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </motion.div>
        </>
      ) : (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground">
              <Package className="h-12 w-12" />
              <p>No hay sugerencias de compra en este momento</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

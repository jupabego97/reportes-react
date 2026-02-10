import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, TrendingUp, Package, Truck, Lightbulb, Search, Download } from 'lucide-react';
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
import { useInsights } from '../hooks/useApi';
import { cn, exportToCSV } from '../lib/utils';
import { MetricTooltip } from '../components/ui/metric-tooltip';

export function Insights() {
  const { data, isLoading, error } = useInsights();
  const [busqueda, setBusqueda] = useState('');

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar insights: {error.message}
      </div>
    );
  }

  const productosRiesgoRaw = data?.productos_en_riesgo || [];
  const oportunidadesRaw = data?.oportunidades || [];
  const sobreStockRaw = data?.sobre_stock || [];
  const proveedoresRiesgoRaw = data?.proveedores_en_riesgo || [];

  const q = busqueda.toLowerCase().trim();
  const filtrar = (items: any[]) => {
    if (!q) return items;
    return items.filter((p: any) =>
      (p.nombre || '').toLowerCase().includes(q) ||
      (p.proveedor || '').toLowerCase().includes(q) ||
      (p.familia || '').toLowerCase().includes(q)
    );
  };

  const productosRiesgo = useMemo(() => filtrar(productosRiesgoRaw), [productosRiesgoRaw, q]);
  const oportunidades = useMemo(() => filtrar(oportunidadesRaw), [oportunidadesRaw, q]);
  const sobreStock = useMemo(() => filtrar(sobreStockRaw), [sobreStockRaw, q]);
  const proveedoresRiesgo = useMemo(() => {
    if (!q) return proveedoresRiesgoRaw;
    return proveedoresRiesgoRaw.filter((p: any) => (p.proveedor || '').toLowerCase().includes(q));
  }, [proveedoresRiesgoRaw, q]);

  const handleExportarRiesgo = () => {
    const headers = ['Producto', 'Proveedor', 'Stock', 'Venta/dia', 'Dias stock', 'Comprar'];
    const rows = productosRiesgoRaw.map((p: any) => [
      p.nombre || '',
      p.proveedor || '',
      String(p.cantidad_disponible || 0),
      String(p.venta_diaria || 0),
      String(p.dias_stock?.toFixed(0) || 0),
      String(p.cantidad_sugerida || 0),
    ]);
    exportToCSV(headers, rows, `productos_riesgo_${new Date().toISOString().slice(0, 10)}.csv`);
    toast.success('Productos en riesgo exportados como CSV');
  };

  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Insights de Inventario</h1>
        <p className="text-muted-foreground">
          Alertas inteligentes cruzando análisis ABC, tendencias y niveles de stock
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {/* Busqueda rapida */}
      <div className="relative w-full md:w-80">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar producto, proveedor o familia..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Skeleton className="h-[100px]" />
            <Skeleton className="h-[100px]" />
            <Skeleton className="h-[100px]" />
            <Skeleton className="h-[100px]" />
          </div>
          <Skeleton className="h-[300px]" />
        </div>
      ) : (
        <>
          {/* Resumen ejecutivo */}
          <div className="grid gap-4 md:grid-cols-4">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card className={cn(productosRiesgo.length > 0 && 'border-red-500/50')}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" /> Productos en Riesgo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{productosRiesgo.length}</div>
                  <p className="text-xs text-muted-foreground">Clase A con stock menor a 7 días</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-emerald-500" /> Oportunidades
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{oportunidades.length}</div>
                  <p className="text-xs text-muted-foreground">Alto ROI y stock bajo</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Package className="h-4 w-4 text-yellow-500" /> Sobre-stock
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{sobreStock.length}</div>
                  <p className="text-xs text-muted-foreground">Clase C con 90+ días de stock</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Truck className="h-4 w-4 text-orange-500" /> Proveedores en Riesgo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{proveedoresRiesgo.length}</div>
                  <p className="text-xs text-muted-foreground">Con productos críticos</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Productos en riesgo */}
          {productosRiesgo.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
              <Card className="border-red-500/50">
                <CardHeader>
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <CardTitle className="flex items-center gap-2 text-red-600">
                      <AlertTriangle className="h-5 w-5" /> Productos Clase A en Riesgo - Accion Inmediata
                      <MetricTooltip text="Pareto: A = top 80% de ventas (alta rotacion). Estos productos son criticos y no deben quedarse sin stock." />
                    </CardTitle>
                    <Button variant="outline" size="sm" onClick={handleExportarRiesgo}>
                      <Download className="h-4 w-4 mr-1" /> CSV
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead>Proveedor</TableHead>
                        <TableHead className="text-right">Stock</TableHead>
                        <TableHead className="text-right">Venta/día</TableHead>
                        <TableHead className="text-right">
                          Dias stock
                          <MetricTooltip text="Stock actual / venta diaria promedio (ultimos 30 dias). Indica cuantos dias dura el inventario actual al ritmo de venta actual." />
                        </TableHead>
                        <TableHead className="text-right">Comprar</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {productosRiesgo.slice(0, 15).map((p: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium max-w-[200px] truncate" title={p.nombre}>{p.nombre}</TableCell>
                          <TableCell>{p.proveedor || '-'}</TableCell>
                          <TableCell className="text-right">
                            <span className={cn(p.cantidad_disponible === 0 && 'text-red-600 font-bold')}>
                              {p.cantidad_disponible}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">{p.venta_diaria}</TableCell>
                          <TableCell className="text-right">
                            <span className="text-red-600">{p.dias_stock?.toFixed(0) || 0}</span>
                          </TableCell>
                          <TableCell className="text-right font-bold text-primary">{p.cantidad_sugerida}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Oportunidades de inversión */}
          {oportunidades.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-emerald-600">
                    <TrendingUp className="h-5 w-5" /> Oportunidades de Inversión (Mayor ROI)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead>ABC</TableHead>
                        <TableHead>Proveedor</TableHead>
                        <TableHead className="text-right">Stock</TableHead>
                        <TableHead className="text-right">Inversión</TableHead>
                        <TableHead className="text-right">ROI Estimado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {oportunidades.slice(0, 15).map((p: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium max-w-[200px] truncate" title={p.nombre}>{p.nombre}</TableCell>
                          <TableCell><Badge variant="default">{p.clasificacion_abc || '-'}</Badge></TableCell>
                          <TableCell>{p.proveedor || '-'}</TableCell>
                          <TableCell className="text-right">{p.cantidad_disponible}</TableCell>
                          <TableCell className="text-right">${Number(p.costo_estimado || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-right text-emerald-600 font-semibold">${Number(p.roi_estimado || 0).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Sobre-stock */}
          {sobreStock.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
              <Card className="border-yellow-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-yellow-600">
                    <Package className="h-5 w-5" /> Sobre-stock (Clase C, +90 días)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead>Familia</TableHead>
                        <TableHead className="text-right">Stock</TableHead>
                        <TableHead className="text-right">Venta/día</TableHead>
                        <TableHead className="text-right">Días stock</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sobreStock.slice(0, 15).map((p: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium max-w-[200px] truncate" title={p.nombre}>{p.nombre}</TableCell>
                          <TableCell>{p.familia || '-'}</TableCell>
                          <TableCell className="text-right">{p.cantidad_disponible}</TableCell>
                          <TableCell className="text-right">{p.venta_diaria}</TableCell>
                          <TableCell className="text-right text-yellow-600">{p.dias_stock?.toFixed(0) || 0}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Proveedores en riesgo */}
          {proveedoresRiesgo.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-orange-600">
                    <Truck className="h-5 w-5" /> Proveedores con Productos Críticos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Proveedor</TableHead>
                        <TableHead className="text-right">Productos en riesgo</TableHead>
                        <TableHead className="text-right">Inversión estimada</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {proveedoresRiesgo.map((p: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium">{p.proveedor}</TableCell>
                          <TableCell className="text-right">
                            <Badge variant="destructive">{p.productos_en_riesgo}</Badge>
                          </TableCell>
                          <TableCell className="text-right">${Number(p.costo_estimado || 0).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Sin datos */}
          {productosRiesgo.length === 0 && oportunidades.length === 0 && sobreStock.length === 0 && proveedoresRiesgo.length === 0 && (
            <Card>
              <CardContent className="py-12">
                <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground">
                  <Lightbulb className="h-12 w-12" />
                  <p>No se encontraron insights relevantes para el período seleccionado</p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

import { motion } from 'framer-motion';
import { AlertTriangle, TrendingUp, Package, Truck, Lightbulb } from 'lucide-react';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
import { cn } from '../lib/utils';

export function Insights() {
  const { data, isLoading, error } = useInsights();

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar insights: {error.message}
      </div>
    );
  }

  const productosRiesgo = data?.productos_en_riesgo || [];
  const oportunidades = data?.oportunidades || [];
  const sobreStock = data?.sobre_stock || [];
  const proveedoresRiesgo = data?.proveedores_en_riesgo || [];

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
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <AlertTriangle className="h-5 w-5" /> Productos Clase A en Riesgo - Acción Inmediata
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead>Proveedor</TableHead>
                        <TableHead className="text-right">Stock</TableHead>
                        <TableHead className="text-right">Venta/día</TableHead>
                        <TableHead className="text-right">Días stock</TableHead>
                        <TableHead className="text-right">Comprar</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {productosRiesgo.slice(0, 15).map((p: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium max-w-[200px] truncate">{p.nombre}</TableCell>
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
                          <TableCell className="font-medium max-w-[200px] truncate">{p.nombre}</TableCell>
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
                          <TableCell className="font-medium max-w-[200px] truncate">{p.nombre}</TableCell>
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

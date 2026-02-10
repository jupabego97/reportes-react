import { motion } from 'framer-motion';
import { ShoppingCart, AlertTriangle, Package } from 'lucide-react';
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
import { useSugerenciasCompra } from '../hooks/useApi';
import { cn } from '../lib/utils';

// Mapeo de prioridades del backend a estilos del frontend
const prioridadConfig: Record<string, { color: 'destructive' | 'secondary' | 'outline' | 'default'; icon: string; label: string; key: string }> = {
  '🔴 Urgente': { color: 'destructive', icon: '🔴', label: 'Urgente', key: 'urgente' },
  '🟠 Alta': { color: 'destructive', icon: '🟠', label: 'Alta', key: 'alta' },
  '🟡 Media': { color: 'secondary', icon: '🟡', label: 'Media', key: 'media' },
  '🟢 Baja': { color: 'outline', icon: '🟢', label: 'Baja', key: 'baja' },
};

const prioridadesAltas = ['🔴 Urgente', '🟠 Alta'];

export function Compras() {
  const { data, isLoading, error } = useSugerenciasCompra();

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold tracking-tight">Sugerencias de Compra</h1>
        <p className="text-muted-foreground">
          Productos que necesitan reposición basado en ventas y stock
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
          </div>
          <Skeleton className="h-[400px]" />
        </div>
      ) : data && Array.isArray(data) && data.length > 0 ? (
        <>
          {/* Resumen por prioridad */}
          <div className="grid gap-4 md:grid-cols-4">
            {Object.entries(prioridadConfig).map(([key, config], index) => {
              const count = data.filter((s: any) => s.prioridad === key).length;
              return (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className={cn(
                    prioridadesAltas.includes(key) && 'border-red-500/50'
                  )}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <span>{config.icon}</span>
                        Prioridad {config.label}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">
                        {count}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        productos a reponer
                      </p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* Productos con prioridad alta/urgente */}
          {data.filter((s: any) => prioridadesAltas.includes(s.prioridad)).length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="border-red-500/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-600">
                    <AlertTriangle className="h-5 w-5" />
                    Prioridad Alta / Urgente - Acción Inmediata
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {data
                      .filter((s: any) => prioridadesAltas.includes(s.prioridad))
                      .slice(0, 6)
                      .map((producto: any, index: number) => (
                        <motion.div
                          key={producto.nombre}
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.1 * index }}
                          className="p-4 rounded-lg border bg-red-500/5 border-red-500/20"
                        >
                          <div className="font-medium truncate">{producto.nombre}</div>
                          <div className="text-sm text-muted-foreground mt-1">
                            Stock: {producto.cantidad_disponible} | Venta diaria: {producto.venta_diaria}
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge variant="destructive">
                              Comprar: {producto.cantidad_sugerida}
                            </Badge>
                          </div>
                        </motion.div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Tabla completa */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ShoppingCart className="h-5 w-5" />
                  Todas las Sugerencias de Compra
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Prioridad</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead>Familia</TableHead>
                      <TableHead>Proveedor</TableHead>
                      <TableHead className="text-right">Stock Actual</TableHead>
                      <TableHead className="text-right">Venta Diaria</TableHead>
                      <TableHead className="text-right">Días de Stock</TableHead>
                      <TableHead className="text-right">Cantidad Sugerida</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.map((producto: any, index: number) => {
                      const config = prioridadConfig[producto.prioridad] || { color: 'default' as const, icon: '', label: producto.prioridad };
                      return (
                        <TableRow key={index}>
                          <TableCell>
                            <Badge variant={config.color}>
                              {config.icon} {config.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-medium max-w-[200px] truncate">
                            {producto.nombre}
                          </TableCell>
                          <TableCell>{producto.familia || '-'}</TableCell>
                          <TableCell>{producto.proveedor || '-'}</TableCell>
                          <TableCell className="text-right">
                            <span className={cn(
                              producto.cantidad_disponible === 0 && 'text-red-600 font-bold'
                            )}>
                              {producto.cantidad_disponible}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">
                            {producto.venta_diaria}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className={cn(
                              producto.dias_stock <= 7 && 'text-red-600',
                              producto.dias_stock > 7 && producto.dias_stock <= 14 && 'text-yellow-600'
                            )}>
                              {producto.dias_stock?.toFixed(0) || 0}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-bold text-primary">
                            {producto.cantidad_sugerida}
                          </TableCell>
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

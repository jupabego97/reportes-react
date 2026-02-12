import { useState } from 'react';
import { motion } from 'framer-motion';
import { Receipt, AlertTriangle, Calendar, DollarSign, Search } from 'lucide-react';
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
import { useFacturasProveedor, useFacturasProveedorResumen } from '../hooks/useApi';
import { formatCurrency } from '../lib/utils';
import { cn } from '../lib/utils';

const estadoConfig: Record<string, { label: string; variant: 'destructive' | 'secondary' | 'outline' | 'default' }> = {
  vencida: { label: 'Vencida', variant: 'destructive' },
  vence_hoy: { label: 'Vence hoy', variant: 'destructive' },
  proxima: { label: 'Proxima (<=7d)', variant: 'secondary' },
  vigente: { label: 'Vigente', variant: 'outline' },
};

export function FacturasProveedor() {
  const [busqueda, setBusqueda] = useState('');
  const [estadoFiltro, setEstadoFiltro] = useState<string>('');
  const [diasPlazo, setDiasPlazo] = useState(30);

  const params = {
    proveedor: busqueda.trim() || undefined,
    dias_plazo: diasPlazo,
    estado: estadoFiltro || undefined,
  };

  const { data: facturas, isLoading: loadingFacturas } = useFacturasProveedor(params);
  const { data: resumen, isLoading: loadingResumen } = useFacturasProveedorResumen({
    proveedor: busqueda.trim() || undefined,
    dias_plazo: diasPlazo,
  });

  const lista = Array.isArray(facturas) ? facturas : [];
  const tieneVencidas = (resumen?.facturas_vencidas ?? 0) > 0;

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Receipt className="h-8 w-8 text-primary" />
          Facturas de Proveedor
        </h1>
        <p className="text-muted-foreground mt-1">
          Recordatorio de vencimientos (plazo de {diasPlazo} dias desde fecha de factura)
        </p>
      </motion.div>

      {/* Busqueda y filtros */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full md:w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por proveedor (ej: andres)"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {['', 'vencida', 'vence_hoy', 'proxima', 'vigente'].map((est) => (
            <Button
              key={est || 'todas'}
              size="sm"
              variant={estadoFiltro === est ? 'default' : 'outline'}
              onClick={() => setEstadoFiltro(est)}
            >
              {est === '' ? 'Todas' : estadoConfig[est]?.label ?? est}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Plazo:</span>
          <Input
            type="number"
            min={1}
            max={90}
            value={diasPlazo}
            onChange={(e) => setDiasPlazo(Math.max(1, Math.min(90, parseInt(e.target.value, 10) || 30)))}
            className="w-16"
          />
          <span className="text-sm text-muted-foreground">dias</span>
        </div>
      </div>

      {loadingResumen ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
      ) : (
        <>
          {/* Alerta de facturas vencidas */}
          {tieneVencidas && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="border-red-500/50 bg-red-500/5">
                <CardContent className="py-4">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-8 w-8 text-red-600" />
                    <div>
                      <p className="font-semibold text-red-700">
                        {resumen?.facturas_vencidas} factura(s) vencida(s) - Monto total: {formatCurrency(resumen?.monto_vencido ?? 0)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Revisa la tabla para ver el detalle por proveedor
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Cards resumen */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Receipt className="h-4 w-4" /> Total facturas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{resumen?.total_facturas ?? 0}</div>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <DollarSign className="h-4 w-4" /> Monto total
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(resumen?.monto_total ?? 0)}</div>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card className={cn(tieneVencidas && 'border-red-500/50')}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" /> Vencidas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">{resumen?.facturas_vencidas ?? 0}</div>
                  <p className="text-xs text-muted-foreground">{formatCurrency(resumen?.monto_vencido ?? 0)}</p>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    Vence hoy
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-orange-600">{resumen?.facturas_vence_hoy ?? 0}</div>
                  <p className="text-xs text-muted-foreground">{formatCurrency(resumen?.monto_vence_hoy ?? 0)}</p>
                </CardContent>
              </Card>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" /> Proximas (≤7 días)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-amber-600">{resumen?.facturas_proximas ?? 0}</div>
                  <p className="text-xs text-muted-foreground">{formatCurrency(resumen?.monto_proximo ?? 0)}</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </>
      )}

      {/* Tabla de facturas */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Card>
          <CardHeader>
            <CardTitle>Detalle de facturas</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingFacturas ? (
              <Skeleton className="h-[300px]" />
            ) : lista.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <Receipt className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No hay facturas de proveedor registradas o la tabla facturas_proveedor no existe</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Proveedor</TableHead>
                    <TableHead>Fecha factura</TableHead>
                    <TableHead>Fecha vencimiento</TableHead>
                    <TableHead className="text-right">Dias restantes</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lista.map((f: any, i: number) => {
                    const cfg = estadoConfig[f.estado] ?? { label: f.estado, variant: 'outline' as const };
                    return (
                      <TableRow
                        key={`${f.proveedor}-${f.fecha_factura}-${i}`}
                        className={cn(f.estado === 'vencida' && 'bg-red-500/5')}
                      >
                        <TableCell className="font-medium">{f.proveedor}</TableCell>
                        <TableCell>{f.fecha_factura}</TableCell>
                        <TableCell>{f.fecha_vencimiento}</TableCell>
                        <TableCell className="text-right">
                          <span
                            className={cn(
                              f.dias_restantes < 0 && 'text-red-600 font-bold',
                              f.dias_restantes === 0 && 'text-orange-600',
                              f.dias_restantes > 0 && f.dias_restantes <= 7 && 'text-amber-600'
                            )}
                          >
                            {f.dias_restantes < 0 ? `${f.dias_restantes}` : f.dias_restantes}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">{formatCurrency(f.monto ?? 0)}</TableCell>
                        <TableCell>
                          <Badge variant={cfg.variant}>{cfg.label}</Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

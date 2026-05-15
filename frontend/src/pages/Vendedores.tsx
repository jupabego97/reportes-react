import { useState } from 'react';
import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { Users, Trophy } from 'lucide-react';
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
import { Button } from '../components/ui/button';
import { useRankingVendedores, useVendedorDetalle } from '../hooks/useApi';
import { cn } from '../lib/utils';

const rankColors = ['🥇', '🥈', '🥉'];

type VendedorRow = {
  vendedor: string;
  ventas_totales: number;
  margen_total: number;
  productos_unicos: number;
  unidades: number;
  ticket_promedio: number;
  margen_porcentaje: number;
  rendimiento: string;
};

export function Vendedores() {
  const { data: ranking, isLoading, error } = useRankingVendedores();
  const [detalleNombre, setDetalleNombre] = useState<string | undefined>(undefined);
  const { data: detalle, isLoading: loadingDetalle } = useVendedorDetalle(detalleNombre);

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  const list: VendedorRow[] = Array.isArray(ranking) ? ranking : [];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Ranking de Vendedores</h1>
        <p className="text-muted-foreground">Desempeño según filtros (ventas totales, margen, ticket medio por linea)</p>
      </motion.div>

      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-[150px]" />
            <Skeleton className="h-[150px]" />
            <Skeleton className="h-[150px]" />
          </div>
          <Skeleton className="h-[400px]" />
        </div>
      ) : list.length === 0 ? (
        <p className="text-muted-foreground">No hay vendedores en el periodo seleccionado.</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            {list.slice(0, 3).map((vendedor, index) => (
              <motion.div
                key={vendedor.vendedor}
                initial={{ opacity: 0, y: 20, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    'relative overflow-hidden cursor-pointer hover:ring-1 hover:ring-primary/30',
                    index === 0 && 'ring-2 ring-yellow-400'
                  )}
                  onClick={() => setDetalleNombre(vendedor.vendedor)}
                >
                  {index === 0 && (
                    <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-yellow-400/20 to-transparent" />
                  )}
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2">
                      <span className="text-2xl">{rankColors[index]}</span>
                      <span className="truncate">{vendedor.vendedor || 'Sin nombre'}</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="text-3xl font-bold text-primary">
                        ${vendedor.ventas_totales?.toLocaleString() ?? 0}
                      </div>
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>{vendedor.unidades?.toLocaleString() ?? 0} unidades</span>
                        <span>Ticket linea ${vendedor.ticket_promedio?.toLocaleString() ?? 0}</span>
                      </div>
                      <Badge variant="outline">{vendedor.rendimiento}</Badge>
                      <p className="text-xs text-muted-foreground">
                        Margen {vendedor.margen_porcentaje?.toFixed(1) ?? 0}% · {vendedor.productos_unicos} SKU
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5" />
                  Comparativa de ventas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px]">
                  <ResponsiveBar
                    data={list.map((v) => ({
                      vendedor: v.vendedor || 'Sin nombre',
                      ventas: v.ventas_totales,
                      unidades: v.unidades,
                    }))}
                    keys={['ventas']}
                    indexBy="vendedor"
                    margin={{ top: 20, right: 20, bottom: 60, left: 80 }}
                    padding={0.3}
                    colors={['hsl(217, 91%, 60%)']}
                    borderRadius={4}
                    axisBottom={{
                      tickSize: 5,
                      tickPadding: 5,
                      tickRotation: -45,
                    }}
                    axisLeft={{
                      tickSize: 5,
                      tickPadding: 5,
                      format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                    }}
                    enableLabel={false}
                    tooltip={({ indexValue, value, data }) => (
                      <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                        <div className="font-medium">{indexValue}</div>
                        <div className="text-primary font-bold">${Number(value).toLocaleString()}</div>
                        <div className="text-xs text-muted-foreground">{data.unidades} unidades</div>
                      </div>
                    )}
                    theme={{
                      axis: {
                        ticks: {
                          text: {
                            fill: 'hsl(var(--muted-foreground))',
                          },
                        },
                      },
                      grid: {
                        line: {
                          stroke: 'hsl(var(--border))',
                        },
                      },
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Detalle por vendedor
                </CardTitle>
                {detalleNombre && (
                  <Button variant="ghost" size="sm" onClick={() => setDetalleNombre(undefined)}>
                    Cerrar panel
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pos.</TableHead>
                      <TableHead>Vendedor</TableHead>
                      <TableHead className="text-right">Unidades</TableHead>
                      <TableHead className="text-right">Ventas</TableHead>
                      <TableHead className="text-right">Margen %</TableHead>
                      <TableHead className="text-right">Ticket linea</TableHead>
                      <TableHead className="text-right">SKU unicos</TableHead>
                      <TableHead className="text-right">Rendimiento</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {list.map((v, index) => (
                      <TableRow
                        key={v.vendedor}
                        className={cn(detalleNombre === v.vendedor && 'bg-muted/60 cursor-pointer')}
                        onClick={() => setDetalleNombre(v.vendedor)}
                      >
                        <TableCell>
                          {index < 3 ? (
                            <span className="text-xl">{rankColors[index]}</span>
                          ) : (
                            <Badge variant="outline">{index + 1}</Badge>
                          )}
                        </TableCell>
                        <TableCell className="font-medium">{v.vendedor || 'Sin nombre'}</TableCell>
                        <TableCell className="text-right">{v.unidades?.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-medium">
                          ${v.ventas_totales?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">{v.margen_porcentaje?.toFixed(1)}%</TableCell>
                        <TableCell className="text-right">${v.ticket_promedio?.toLocaleString()}</TableCell>
                        <TableCell className="text-right">{v.productos_unicos}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant="secondary">{v.rendimiento}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {detalleNombre && (
                  <Card className="border-dashed">
                    <CardHeader>
                      <CardTitle className="text-base">Detalle: {detalleNombre}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {loadingDetalle ? (
                        <Skeleton className="h-24" />
                      ) : detalle ? (
                        <div className="text-sm space-y-2">
                          <p>
                            Ventas totales:{' '}
                            <strong>${Number(detalle.ventas_totales ?? 0).toLocaleString()}</strong>
                          </p>
                          <p>Delta vs promedio equipo: {Number(detalle.delta_vs_promedio ?? 0).toFixed(1)}%</p>
                          <p className="text-muted-foreground">
                            {detalle.top_productos?.length ?? 0} productos en top · ver graficos en pestaña Ventas
                            con filtro de vendedor.
                          </p>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </>
      )}
    </div>
  );
}

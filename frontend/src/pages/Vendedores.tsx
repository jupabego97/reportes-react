import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { Users, Trophy, TrendingUp, TrendingDown } from 'lucide-react';
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
import { useRankingVendedores } from '../hooks/useApi';
import { cn } from '../lib/utils';

const rankColors = ['🥇', '🥈', '🥉'];

export function Vendedores() {
  const { data, isLoading, error } = useRankingVendedores();

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
        <h1 className="text-3xl font-bold tracking-tight">Ranking de Vendedores</h1>
        <p className="text-muted-foreground">
          Desempeño y métricas por vendedor
        </p>
      </motion.div>

      {/* Filtros */}
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
      ) : data && data.ranking ? (
        <>
          {/* Top 3 vendedores */}
          <div className="grid gap-4 md:grid-cols-3">
            {data.ranking.slice(0, 3).map((vendedor: any, index: number) => (
              <motion.div
                key={vendedor.vendedor}
                initial={{ opacity: 0, y: 20, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className={cn(
                  'relative overflow-hidden',
                  index === 0 && 'ring-2 ring-yellow-400'
                )}>
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
                        ${vendedor.total_venta?.toLocaleString() || 0}
                      </div>
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>{vendedor.cantidad?.toLocaleString() || 0} ventas</span>
                        <span>Ticket: ${vendedor.ticket_promedio?.toLocaleString() || 0}</span>
                      </div>
                      {vendedor.variacion !== undefined && (
                        <div className={cn(
                          'flex items-center gap-1 text-sm',
                          vendedor.variacion >= 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {vendedor.variacion >= 0 ? (
                            <TrendingUp className="h-4 w-4" />
                          ) : (
                            <TrendingDown className="h-4 w-4" />
                          )}
                          {vendedor.variacion >= 0 ? '+' : ''}{vendedor.variacion?.toFixed(1)}% vs periodo anterior
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Gráfico comparativo */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5" />
                  Comparativa de Ventas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px]">
                  <ResponsiveBar
                    data={data.ranking.map((v: any) => ({
                      vendedor: v.vendedor || 'Sin nombre',
                      ventas: v.total_venta,
                      cantidad: v.cantidad,
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
                        <div className="text-primary font-bold">
                          ${Number(value).toLocaleString()}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {data.cantidad} transacciones
                        </div>
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

          {/* Tabla detallada */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Detalle por Vendedor
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pos.</TableHead>
                      <TableHead>Vendedor</TableHead>
                      <TableHead className="text-right">Transacciones</TableHead>
                      <TableHead className="text-right">Total Ventas</TableHead>
                      <TableHead className="text-right">Ticket Promedio</TableHead>
                      <TableHead className="text-right">Productos Únicos</TableHead>
                      <TableHead className="text-right">Variación</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.ranking.map((vendedor: any, index: number) => (
                      <TableRow key={vendedor.vendedor}>
                        <TableCell>
                          {index < 3 ? (
                            <span className="text-xl">{rankColors[index]}</span>
                          ) : (
                            <Badge variant="outline">{index + 1}</Badge>
                          )}
                        </TableCell>
                        <TableCell className="font-medium">
                          {vendedor.vendedor || 'Sin nombre'}
                        </TableCell>
                        <TableCell className="text-right">
                          {vendedor.cantidad?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          ${vendedor.total_venta?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          ${vendedor.ticket_promedio?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          {vendedor.productos_unicos}
                        </TableCell>
                        <TableCell className="text-right">
                          {vendedor.variacion !== undefined ? (
                            <span className={cn(
                              'flex items-center justify-end gap-1',
                              vendedor.variacion >= 0 ? 'text-green-600' : 'text-red-600'
                            )}>
                              {vendedor.variacion >= 0 ? '+' : ''}{vendedor.variacion?.toFixed(1)}%
                            </span>
                          ) : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </motion.div>
        </>
      ) : null}
    </div>
  );
}

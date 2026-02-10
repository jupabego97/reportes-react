import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsivePie } from '@nivo/pie';
import { Package } from 'lucide-react';
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
import { useABC } from '../hooks/useApi';

const categoryColors = {
  A: 'hsl(142, 71%, 45%)',  // green
  B: 'hsl(47, 96%, 53%)',   // yellow
  C: 'hsl(350, 89%, 60%)',  // red
};

export function AnalisisABC() {
  const { data, isLoading, error } = useABC();

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
        <h1 className="text-3xl font-bold tracking-tight">Análisis ABC (Pareto)</h1>
        <p className="text-muted-foreground">
          Clasificación de productos por contribución a las ventas
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[400px]" />
          <Skeleton className="h-[400px]" />
        </div>
      ) : data ? (
        <>
          {/* Resumen por categoría */}
          <div className="grid gap-4 md:grid-cols-3">
            {['A', 'B', 'C'].map((categoria, index) => {
              const catData = data.resumen?.find((r: any) => r.categoria === categoria);
              return (
                <motion.div
                  key={categoria}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2">
                        <Badge
                          style={{ backgroundColor: categoryColors[categoria as keyof typeof categoryColors] }}
                          className="text-white"
                        >
                          Categoría {categoria}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Productos:</span>
                          <span className="font-bold">{catData?.productos || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">% Ventas:</span>
                          <span className="font-bold">{catData?.porcentaje_ventas?.toFixed(1) || 0}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Total:</span>
                          <span className="font-bold">${catData?.total_ventas?.toLocaleString() || 0}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* Gráficos */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Distribución por categoría */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Distribución de Ventas por Categoría</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    {data.resumen && data.resumen.length > 0 ? (
                      <ResponsivePie
                        data={data.resumen.map((r: any) => ({
                          id: `Categoría ${r.categoria}`,
                          label: `Cat. ${r.categoria}`,
                          value: r.total_ventas,
                          color: categoryColors[r.categoria as keyof typeof categoryColors],
                        }))}
                        margin={{ top: 20, right: 80, bottom: 20, left: 80 }}
                        innerRadius={0.5}
                        padAngle={0.7}
                        cornerRadius={3}
                        colors={{ datum: 'data.color' }}
                        borderWidth={1}
                        borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
                        arcLinkLabelsTextColor="hsl(var(--foreground))"
                        arcLinkLabelsThickness={2}
                        arcLinkLabelsColor={{ from: 'color' }}
                        arcLabelsTextColor="#ffffff"
                        tooltip={({ datum }) => (
                          <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                            <div className="font-medium">{datum.id}</div>
                            <div className="text-primary font-bold">
                              ${Number(datum.value).toLocaleString()}
                            </div>
                          </div>
                        )}
                      />
                    ) : (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        Sin datos
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Curva de Pareto */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Curva de Pareto (Top 20 Productos)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    {data.productos && data.productos.length > 0 ? (
                      <ResponsiveBar
                        data={data.productos.slice(0, 20).map((p: any, i: number) => ({
                          producto: p.nombre?.substring(0, 15) || `Prod ${i + 1}`,
                          ventas: p.total_venta,
                          acumulado: p.porcentaje_acumulado,
                          color: categoryColors[p.categoria as keyof typeof categoryColors],
                        }))}
                        keys={['ventas']}
                        indexBy="producto"
                        margin={{ top: 20, right: 20, bottom: 80, left: 60 }}
                        padding={0.3}
                        colors={({ data }) => String(data.color)}
                        borderRadius={2}
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
                              Acumulado: {Number(data.acumulado ?? 0).toFixed(1)}%
                            </div>
                          </div>
                        )}
                        theme={{
                          axis: {
                            ticks: {
                              text: {
                                fill: 'hsl(var(--muted-foreground))',
                                fontSize: 10,
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
                    ) : (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        Sin datos
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Tabla de productos */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5" />
                  Detalle de Productos por Categoría
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead>Categoría</TableHead>
                      <TableHead className="text-right">Cantidad</TableHead>
                      <TableHead className="text-right">Total Ventas</TableHead>
                      <TableHead className="text-right">% del Total</TableHead>
                      <TableHead className="text-right">% Acumulado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.productos?.slice(0, 20).map((producto: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{producto.nombre}</TableCell>
                        <TableCell>
                          <Badge
                            style={{ backgroundColor: categoryColors[producto.categoria as keyof typeof categoryColors] }}
                            className="text-white"
                          >
                            {producto.categoria}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {producto.cantidad?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          ${producto.total_venta?.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          {producto.porcentaje?.toFixed(2)}%
                        </TableCell>
                        <TableCell className="text-right">
                          {producto.porcentaje_acumulado?.toFixed(2)}%
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

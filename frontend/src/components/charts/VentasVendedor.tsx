import { ResponsiveBar } from '@nivo/bar';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useVentasPorVendedor } from '../../hooks/useApi';

export function VentasVendedor() {
  const { data, isLoading, error } = useVentasPorVendedor();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ventas por Vendedor</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ventas por Vendedor</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
          Error al cargar datos
        </CardContent>
      </Card>
    );
  }

  const chartData = data.slice(0, 10).map((d: any) => ({
    vendedor: d.vendedor || 'Sin asignar',
    ventas: d.total_venta,
    cantidad: d.cantidad,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            👥 Ventas por Vendedor
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveBar
              data={chartData}
              keys={['ventas']}
              indexBy="vendedor"
              margin={{ top: 20, right: 20, bottom: 60, left: 80 }}
              padding={0.3}
              valueScale={{ type: 'linear' }}
              indexScale={{ type: 'band', round: true }}
              colors={['hsl(217, 91%, 60%)']}
              borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
              axisTop={null}
              axisRight={null}
              axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: -45,
                legend: '',
                legendPosition: 'middle',
                legendOffset: 50,
                truncateTickAt: 0,
              }}
              axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
                legend: 'Ventas ($)',
                legendPosition: 'middle',
                legendOffset: -70,
                format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
              }}
              enableGridY={true}
              enableLabel={false}
              labelSkipWidth={12}
              labelSkipHeight={12}
              labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
              role="application"
              ariaLabel="Ventas por vendedor"
              tooltip={({ indexValue, value }) => (
                <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                  <div className="font-medium">{indexValue}</div>
                  <div className="text-primary font-bold">
                    ${Number(value).toLocaleString()}
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
                  legend: {
                    text: {
                      fill: 'hsl(var(--muted-foreground))',
                    },
                  },
                },
                grid: {
                  line: {
                    stroke: 'hsl(var(--border))',
                    strokeWidth: 1,
                  },
                },
              }}
            />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

import { ResponsiveBar } from '@nivo/bar';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useVentasPorMetodo } from '../../hooks/useApi';

const COLORS = [
  'hsl(142, 71%, 45%)',  // green
  'hsl(217, 91%, 60%)',  // blue
  'hsl(262, 83%, 58%)',  // purple
  'hsl(25, 95%, 53%)',   // orange
  'hsl(350, 89%, 60%)',  // red
];

export function VentasMetodo() {
  const { data, isLoading, error } = useVentasPorMetodo();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ventas por Método de Pago</CardTitle>
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
          <CardTitle>Ventas por Método de Pago</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
          Error al cargar datos
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((d: any, index: number) => ({
    metodo: d.metodo || 'Otro',
    ventas: d.total_venta,
    color: COLORS[index % COLORS.length],
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            💳 Ventas por Método de Pago
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveBar
              data={chartData}
              keys={['ventas']}
              indexBy="metodo"
              margin={{ top: 20, right: 20, bottom: 50, left: 80 }}
              padding={0.4}
              layout="horizontal"
              valueScale={{ type: 'linear' }}
              indexScale={{ type: 'band', round: true }}
              colors={({ index }) => COLORS[index % COLORS.length]}
              borderRadius={4}
              borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
              axisTop={null}
              axisRight={null}
              axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
                legend: 'Ventas ($)',
                legendPosition: 'middle',
                legendOffset: 40,
                format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
              }}
              axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
              }}
              enableGridX={true}
              enableGridY={false}
              enableLabel={true}
              label={(d) => `$${(Number(d.value) / 1000).toFixed(0)}k`}
              labelSkipWidth={50}
              labelSkipHeight={12}
              labelTextColor="#ffffff"
              role="application"
              ariaLabel="Ventas por método de pago"
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

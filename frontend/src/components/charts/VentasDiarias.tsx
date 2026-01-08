import { ResponsiveLine } from '@nivo/line';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useVentasPorDia } from '../../hooks/useApi';

export function VentasDiarias() {
  const { data, isLoading, error } = useVentasPorDia();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ventas Diarias</CardTitle>
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
          <CardTitle>Ventas Diarias</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
          Error al cargar datos
        </CardContent>
      </Card>
    );
  }

  const chartData = [
    {
      id: 'Ventas',
      color: 'hsl(var(--primary))',
      data: data.map((d: any) => ({
        x: d.fecha,
        y: d.total_venta,
      })),
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📈 Ventas Diarias
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveLine
              data={chartData}
              margin={{ top: 20, right: 20, bottom: 50, left: 60 }}
              xScale={{ type: 'point' }}
              yScale={{ type: 'linear', min: 'auto', max: 'auto', stacked: false }}
              curve="monotoneX"
              axisTop={null}
              axisRight={null}
              axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: -45,
                legend: 'Fecha',
                legendOffset: 40,
                legendPosition: 'middle',
                truncateTickAt: 0,
              }}
              axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
                legend: 'Ventas ($)',
                legendOffset: -50,
                legendPosition: 'middle',
                format: (v) => `$${(v / 1000).toFixed(0)}k`,
              }}
              enableGridX={false}
              colors={['hsl(217, 91%, 60%)']}
              lineWidth={3}
              enablePoints={true}
              pointSize={8}
              pointColor={{ theme: 'background' }}
              pointBorderWidth={2}
              pointBorderColor={{ from: 'serieColor' }}
              pointLabelYOffset={-12}
              enableArea={true}
              areaOpacity={0.15}
              useMesh={true}
              tooltip={({ point }) => (
                <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                  <div className="font-medium">{point.data.xFormatted}</div>
                  <div className="text-primary font-bold">
                    ${Number(point.data.y).toLocaleString()}
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
                crosshair: {
                  line: {
                    stroke: 'hsl(var(--primary))',
                    strokeWidth: 1,
                    strokeOpacity: 0.5,
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

import { ResponsivePie } from '@nivo/pie';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useVentasPorFamilia } from '../../hooks/useApi';

const COLORS = [
  'hsl(217, 91%, 60%)',  // blue
  'hsl(142, 71%, 45%)',  // green
  'hsl(262, 83%, 58%)',  // purple
  'hsl(25, 95%, 53%)',   // orange
  'hsl(350, 89%, 60%)',  // red
  'hsl(47, 96%, 53%)',   // yellow
  'hsl(199, 89%, 48%)',  // cyan
  'hsl(339, 90%, 51%)',  // pink
];

export function VentasFamilia() {
  const { data, isLoading, error } = useVentasPorFamilia();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ventas por Familia</CardTitle>
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
          <CardTitle>Ventas por Familia</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
          Error al cargar datos
        </CardContent>
      </Card>
    );
  }

  const chartData = data.slice(0, 8).map((d: any, index: number) => ({
    id: d.familia || 'Sin familia',
    label: d.familia || 'Sin familia',
    value: d.total_venta,
    color: COLORS[index % COLORS.length],
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🏷️ Ventas por Familia
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsivePie
              data={chartData}
              margin={{ top: 20, right: 80, bottom: 20, left: 80 }}
              innerRadius={0.5}
              padAngle={0.7}
              cornerRadius={3}
              activeOuterRadiusOffset={8}
              colors={{ datum: 'data.color' }}
              borderWidth={1}
              borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
              arcLinkLabelsSkipAngle={10}
              arcLinkLabelsTextColor="hsl(var(--foreground))"
              arcLinkLabelsThickness={2}
              arcLinkLabelsColor={{ from: 'color' }}
              arcLabelsSkipAngle={10}
              arcLabelsTextColor={{ from: 'color', modifiers: [['darker', 2]] }}
              tooltip={({ datum }) => (
                <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: datum.color }}
                    />
                    <span className="font-medium">{datum.label}</span>
                  </div>
                  <div className="text-primary font-bold mt-1">
                    ${Number(datum.value).toLocaleString()}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {((datum.arc.endAngle - datum.arc.startAngle) / (2 * Math.PI) * 100).toFixed(1)}%
                  </div>
                </div>
              )}
              theme={{
                labels: {
                  text: {
                    fill: 'hsl(var(--foreground))',
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

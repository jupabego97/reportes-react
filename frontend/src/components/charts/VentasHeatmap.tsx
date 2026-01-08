import { ResponsiveHeatMap } from '@nivo/heatmap';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useVentasPorDia } from '../../hooks/useApi';

export function VentasHeatmap() {
  const { data, isLoading, error } = useVentasPorDia();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Mapa de Calor Semanal</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[200px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Mapa de Calor Semanal</CardTitle>
        </CardHeader>
        <CardContent className="h-[200px] flex items-center justify-center text-muted-foreground">
          Sin datos disponibles
        </CardContent>
      </Card>
    );
  }

  // Agrupar datos por día de la semana y semana del mes
  const diasSemana = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  
  // Crear estructura de datos para el heatmap
  const weeklyData: { [key: string]: { [key: string]: number } } = {};
  
  data.forEach((d: any) => {
    const date = new Date(d.fecha);
    const dayOfWeek = diasSemana[date.getDay()];
    const weekNum = `Sem ${Math.ceil(date.getDate() / 7)}`;
    
    if (!weeklyData[weekNum]) {
      weeklyData[weekNum] = {};
    }
    
    weeklyData[weekNum][dayOfWeek] = (weeklyData[weekNum][dayOfWeek] || 0) + d.total_venta;
  });

  const heatmapData = Object.entries(weeklyData).map(([week, days]) => ({
    id: week,
    data: diasSemana.map((dia) => ({
      x: dia,
      y: days[dia] || 0,
    })),
  }));

  if (heatmapData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Mapa de Calor Semanal</CardTitle>
        </CardHeader>
        <CardContent className="h-[200px] flex items-center justify-center text-muted-foreground">
          Sin datos suficientes
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🗓️ Mapa de Calor Semanal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveHeatMap
              data={heatmapData}
              margin={{ top: 20, right: 20, bottom: 40, left: 60 }}
              valueFormat={(v) => `$${(Number(v) / 1000).toFixed(0)}k`}
              axisTop={null}
              axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
              }}
              axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: 0,
              }}
              colors={{
                type: 'sequential',
                scheme: 'blues',
              }}
              emptyColor="#f0f0f0"
              borderRadius={4}
              borderWidth={2}
              borderColor={{ from: 'color', modifiers: [['darker', 0.4]] }}
              labelTextColor={{ from: 'color', modifiers: [['darker', 2]] }}
              tooltip={({ cell }) => (
                <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                  <div className="font-medium">{cell.serieId} - {cell.data.x}</div>
                  <div className="text-primary font-bold">
                    ${Number(cell.data.y).toLocaleString()}
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
              }}
            />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}


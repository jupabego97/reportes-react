import { ResponsiveBar } from '@nivo/bar';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';

interface TopProductosCantidadProps {
  data: { nombre: string; cantidad: number }[];
  isLoading: boolean;
}

export function TopProductosCantidad({ data, isLoading }: TopProductosCantidadProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  const chartData = data.slice(0, 10).map((d) => ({
    nombre: d.nombre.length > 20 ? d.nombre.substring(0, 20) + '...' : d.nombre,
    cantidad: d.cantidad,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>📦 Top 10 Productos por Cantidad</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveBar
            data={chartData}
            keys={['cantidad']}
            indexBy="nombre"
            margin={{ top: 10, right: 20, bottom: 80, left: 60 }}
            padding={0.3}
            valueScale={{ type: 'linear' }}
            colors={['#8b5cf6']}
            axisBottom={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: -45,
              legend: 'Producto',
              legendPosition: 'middle',
              legendOffset: 70,
            }}
            axisLeft={{
              tickSize: 5,
              tickPadding: 5,
              legend: 'Cantidad',
              legendPosition: 'middle',
              legendOffset: -50,
            }}
            labelSkipWidth={12}
            labelSkipHeight={12}
            tooltip={({ indexValue, value }) => (
              <div className="rounded bg-background border shadow-lg p-2 text-sm">
                <strong>{indexValue}</strong>
                <br />
                {value?.toLocaleString('es-CO')} unidades
              </div>
            )}
          />
        </div>
      </CardContent>
    </Card>
  );
}


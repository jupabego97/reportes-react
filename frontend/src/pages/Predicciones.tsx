import { motion } from 'framer-motion';
import { ResponsiveLine } from '@nivo/line';
import { ResponsiveBar } from '@nivo/bar';
import { TrendingUp, Calendar, Target, AlertCircle, BarChart3 } from 'lucide-react';
import { FilterPanel } from '../components/filters/FilterPanel';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { usePredicciones } from '../hooks/useApi';
import { Alert, AlertDescription } from '../components/ui/alert';

export function Predicciones() {
  const { data, isLoading, error } = usePredicciones();

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  // Formatear fechas para el gráfico
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) {
        // Si es formato YYYY-MM-DD, parsearlo manualmente
        const [year, month, day] = dateStr.split('-');
        const parsedDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return parsedDate.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
      }
      return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  // Preparar datos para el gráfico
  const historicoData = data?.historico?.map((h: any) => ({
    x: formatDate(h.fecha),
    y: h.ventas,
    fecha: h.fecha,
  })) || [];

  const mediaMovilData = data?.historico
    ?.filter((h: any) => h.media_movil_7d !== null && h.media_movil_7d !== undefined)
    .map((h: any) => ({
      x: formatDate(h.fecha),
      y: h.media_movil_7d,
      fecha: h.fecha,
    })) || [];

  const prediccionesData = data?.predicciones?.map((p: any) => ({
    x: formatDate(p.fecha),
    y: p.ventas,
    fecha: p.fecha,
  })) || [];

  // Banda de confianza (upper/lower para gráfico)
  const confianzaData = data?.predicciones?.map((p: any, idx: number) => {
    const upper = data.predicciones_upper?.[idx] ?? p.ventas * 1.2;
    const lower = data.predicciones_lower?.[idx] ?? Math.max(0, p.ventas * 0.8);
    return {
      x: formatDate(p.fecha),
      y: upper,
      y0: lower,
      fecha: p.fecha,
    };
  }) || [];

  // Datos para el gráfico de estacionalidad
  const estacionalidadData = data?.ventas_por_dia_semana?.map((v: any) => ({
    dia: v.dia,
    promedio: v.promedio,
  })) || [];

  // Ordenar días de la semana
  const ordenDias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  const estacionalidadOrdenada = ordenDias.map(dia => 
    estacionalidadData.find((d: any) => d.dia === dia) || { dia, promedio: 0 }
  );

  const tieneDatosSuficientes = data?.historico && data.historico.length >= 7;
  const tendenciaTexto = data?.tendencia_diaria 
    ? data.tendencia_diaria > 0 
      ? `+$${data.tendencia_diaria.toFixed(2)}/día` 
      : `$${data.tendencia_diaria.toFixed(2)}/día`
    : 'N/A';

  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold tracking-tight">🔮 Predicciones de Ventas</h1>
        <p className="text-muted-foreground">
          Proyecciones basadas en tendencias históricas y análisis de estacionalidad
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {isLoading ? (
        <div className="grid gap-6">
          <Skeleton className="h-[400px]" />
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
            <Skeleton className="h-[120px]" />
          </div>
          <Skeleton className="h-[300px]" />
        </div>
      ) : data ? (
        <>
          {!tieneDatosSuficientes && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Se necesitan al menos 7 días de datos para generar predicciones precisas.
              </AlertDescription>
            </Alert>
          )}

          {/* Métricas de predicción */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Venta Diaria Promedio (7d)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-primary">
                    ${data.venta_diaria_promedio?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </div>
                  {data.tendencia_diaria !== undefined && (
                    <p className={`text-xs mt-1 ${
                      data.tendencia_diaria > 0 ? 'text-green-600' : 
                      data.tendencia_diaria < 0 ? 'text-red-600' : 'text-muted-foreground'
                    }`}>
                      Tendencia: {tendenciaTexto}
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Predicción Próxima Semana
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-primary">
                    ${data.prediccion_semanal?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Proyección 7 días
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Predicción Próximo Mes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-primary">
                    ${data.prediccion_mensual?.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Proyección 30 días
                  </p>
                </CardContent>
              </Card>
            </motion.div>
            {(data.mape != null || data.wape != null) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <BarChart3 className="h-4 w-4" />
                      Calidad del modelo
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex gap-4 text-sm">
                      {data.mape != null && (
                        <div>
                          <span className="text-muted-foreground">MAPE: </span>
                          <span className="font-semibold">{data.mape}%</span>
                        </div>
                      )}
                      {data.wape != null && (
                        <div>
                          <span className="text-muted-foreground">WAPE: </span>
                          <span className="font-semibold">{data.wape}%</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Error in-sample (ajuste histórico)
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </div>

          {/* Gráfico de tendencia con predicción */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>📊 Tendencia y Proyección</CardTitle>
                <CardDescription>
                  Ventas históricas, media móvil de 7 días y predicciones con banda de confianza basada en desviación histórica
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[450px]">
                  {tieneDatosSuficientes && historicoData.length > 0 ? (
                    <ResponsiveLine
                      data={[
                        {
                          id: 'Ventas Reales',
                          color: 'hsl(217, 91%, 60%)',
                          data: historicoData,
                        },
                        {
                          id: 'Media Móvil 7d',
                          color: 'hsl(25, 95%, 53%)',
                          data: mediaMovilData,
                        },
                        {
                          id: 'Predicción',
                          color: 'hsl(142, 71%, 45%)',
                          data: prediccionesData,
                        },
                      ]}
                      margin={{ top: 20, right: 120, bottom: 60, left: 80 }}
                      xScale={{ type: 'point' }}
                      yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                      curve="monotoneX"
                      layers={[
                        'grid',
                        'axes',
                        (layerProps: any) => {
                          if (confianzaData.length === 0) return null;
                          const { xScale, yScale } = layerProps;
                          const points = confianzaData
                            .map((d: { x: string; y: number; y0: number }) => {
                              const x = xScale(d.x);
                              const yUpper = yScale(d.y);
                              const yLower = yScale(d.y0);
                              return { x: Number(x), yUpper: Number(yUpper), yLower: Number(yLower) };
                            })
                            .filter((p: { x: number; yUpper: number; yLower: number }) => !Number.isNaN(p.x) && !Number.isNaN(p.yUpper));
                          if (points.length < 2) return null;
                          const d = points
                            .map((p: { x: number; yUpper: number }, i: number) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.yUpper}`)
                            .join(' ') +
                            ' ' +
                            points
                              .slice()
                              .reverse()
                              .map((p: { x: number; yLower: number }, i: number) => `${i === 0 ? 'L' : 'L'} ${p.x} ${p.yLower}`)
                              .join(' ') +
                            ' Z';
                          return (
                            <path
                              d={d}
                              fill="hsl(142, 71%, 45%)"
                              fillOpacity={0.2}
                              strokeWidth={0}
                            />
                          );
                        },
                        'lines',
                        'points',
                        'mesh',
                        'legends',
                      ]}
                      axisBottom={{
                        tickSize: 5,
                        tickPadding: 5,
                        tickRotation: -45,
                        legend: 'Fecha',
                        legendOffset: 50,
                        legendPosition: 'middle',
                      }}
                      axisLeft={{
                        tickSize: 5,
                        tickPadding: 5,
                        format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                        legend: 'Ventas ($)',
                        legendOffset: -60,
                        legendPosition: 'middle',
                      }}
                      enableGridX={false}
                      colors={{ datum: 'color' }}
                      lineWidth={2}
                      enablePoints={true}
                      pointSize={6}
                      pointColor={{ theme: 'background' }}
                      pointBorderWidth={2}
                      pointBorderColor={{ from: 'serieColor' }}
                      enableArea={false}
                      useMesh={true}
                      legends={[
                        {
                          anchor: 'bottom-right',
                          direction: 'column',
                          justify: false,
                          translateX: 100,
                          translateY: 0,
                          itemsSpacing: 0,
                          itemDirection: 'left-to-right',
                          itemWidth: 80,
                          itemHeight: 20,
                          itemOpacity: 0.75,
                          symbolSize: 12,
                          symbolShape: 'circle',
                          symbolBorderColor: 'rgba(0, 0, 0, .5)',
                        },
                      ]}
                      tooltip={({ point }) => (
                        <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                          <div className="font-medium">{point.seriesId}</div>
                          <div className="text-xs text-muted-foreground">{String(point.data.x)}</div>
                          <div className="text-primary font-bold">
                            ${Number(point.data.y).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                        legends: {
                          text: {
                            fill: 'hsl(var(--muted-foreground))',
                          },
                        },
                      }}
                    />
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      Sin datos suficientes para predicción (se requieren al menos 7 días)
                    </div>
                  )}
                </div>
                {tieneDatosSuficientes && prediccionesData.length > 0 && confianzaData.length > 0 && (
                  <div className="mt-4 text-sm text-muted-foreground flex items-center gap-4">
                    <p>
                      <span className="inline-block w-3 h-3 rounded-sm bg-green-500/30 mr-2 align-middle"></span>
                      Banda de confianza: rango probable según desviación estándar histórica de residuos.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Gráfico de estacionalidad por día de la semana */}
          {estacionalidadOrdenada.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>📅 Patrón por Día de la Semana</CardTitle>
                  <CardDescription>
                    Ventas promedio por día de la semana para identificar patrones de estacionalidad
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[350px]">
                    <ResponsiveBar
                      data={estacionalidadOrdenada}
                      keys={['promedio']}
                      indexBy="dia"
                      margin={{ top: 20, right: 50, bottom: 50, left: 80 }}
                      padding={0.3}
                      valueScale={{ type: 'linear' }}
                      indexScale={{ type: 'band', round: true }}
                      colors={{ scheme: 'nivo' }}
                      axisTop={null}
                      axisRight={null}
                      axisBottom={{
                        tickSize: 5,
                        tickPadding: 5,
                        tickRotation: 0,
                        legend: 'Día de la Semana',
                        legendPosition: 'middle',
                        legendOffset: 40,
                      }}
                      axisLeft={{
                        tickSize: 5,
                        tickPadding: 5,
                        format: (v) => `$${(Number(v) / 1000).toFixed(0)}k`,
                        legend: 'Ventas Promedio ($)',
                        legendPosition: 'middle',
                        legendOffset: -60,
                      }}
                      labelSkipWidth={12}
                      labelSkipHeight={12}
                      labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
                      tooltip={({ value }) => (
                        <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-lg border">
                          <div className="text-primary font-bold">
                            ${Number(value).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
          )}
        </>
      ) : null}
    </div>
  );
}

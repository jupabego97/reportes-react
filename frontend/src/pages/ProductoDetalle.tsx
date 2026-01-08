import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
    ArrowLeft,
    Package,
    TrendingUp,
    TrendingDown,
    DollarSign,
    BarChart3,
    AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
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
import { api } from '../services/api';
import { cn } from '../lib/utils';
import { ResponsiveLine } from '@nivo/line';

// Types
interface ProductoDetalle {
    nombre: string;
    familia: string | null;
    stock_actual: number;
    precio_venta: number;
    precio_compra_promedio: number | null;
    venta_diaria: number;
    dias_cobertura: number | null;
    total_vendido_30d: number;
    total_ingresos_30d: number;
    margen_porcentaje: number | null;
    tendencia: number;
    tendencia_label: string;
    historial_ventas: {
        fecha_venta: string;
        cantidad: number;
        total_venta: number;
        precio_promedio: number;
        costo_promedio: number | null;
        vendedores: string | null;
    }[];
}

// Format currency
const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
};

export function ProductoDetalle() {
    const { nombre } = useParams<{ nombre: string }>();
    const navigate = useNavigate();

    const { data: producto, isLoading, error } = useQuery({
        queryKey: ['producto-detalle', nombre],
        queryFn: () => api.get<ProductoDetalle>(`/api/inventario/producto/${encodeURIComponent(nombre || '')}`),
        enabled: !!nombre,
    });

    if (!nombre) {
        return (
            <div className="text-center py-12">
                <p className="text-muted-foreground">Producto no especificado</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
                <p className="text-destructive">Error al cargar el producto</p>
                <Button onClick={() => navigate(-1)} className="mt-4">Volver</Button>
            </div>
        );
    }

    // Prepare chart data
    const chartData = producto?.historial_ventas ? [
        {
            id: 'Ventas',
            data: producto.historial_ventas
                .slice()
                .reverse()
                .map(v => ({
                    x: v.fecha_venta,
                    y: v.cantidad,
                })),
        },
    ] : [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-4"
            >
                <Button
                    variant="outline"
                    size="icon"
                    onClick={() => navigate(-1)}
                >
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold tracking-tight line-clamp-1">
                        {producto?.nombre || nombre}
                    </h1>
                    <div className="flex items-center gap-2 mt-1">
                        {producto?.familia && (
                            <Badge variant="secondary">{producto.familia}</Badge>
                        )}
                        {producto && (
                            <Badge
                                variant={producto.tendencia > 5 ? 'default' : producto.tendencia < -5 ? 'destructive' : 'outline'}
                            >
                                {producto.tendencia_label}
                            </Badge>
                        )}
                    </div>
                </div>
            </motion.div>

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-[120px]" />)}
                </div>
            ) : producto && (
                <>
                    {/* KPIs */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
                    >
                        {/* Stock */}
                        <Card className={cn(
                            producto.dias_cobertura !== null && producto.dias_cobertura <= 7 && 'border-red-500/50'
                        )}>
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium">Stock Actual</CardTitle>
                                <Package className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{producto.stock_actual} unidades</div>
                                <p className="text-xs text-muted-foreground">
                                    {producto.dias_cobertura !== null
                                        ? `${producto.dias_cobertura} días de cobertura`
                                        : 'Sin ventas recientes'}
                                </p>
                            </CardContent>
                        </Card>

                        {/* Ventas mensuales */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium">Ventas (30d)</CardTitle>
                                <BarChart3 className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{producto.total_vendido_30d} uds</div>
                                <p className="text-xs text-muted-foreground">
                                    {formatCurrency(producto.total_ingresos_30d)} en ingresos
                                </p>
                            </CardContent>
                        </Card>

                        {/* Venta diaria */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium">Velocidad de Venta</CardTitle>
                                {producto.tendencia > 0 ? (
                                    <TrendingUp className="h-4 w-4 text-green-500" />
                                ) : (
                                    <TrendingDown className="h-4 w-4 text-red-500" />
                                )}
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{producto.venta_diaria}/día</div>
                                <p className={cn(
                                    "text-xs",
                                    producto.tendencia > 0 ? "text-green-600" : "text-red-600"
                                )}>
                                    {producto.tendencia > 0 ? '+' : ''}{producto.tendencia}% vs semana anterior
                                </p>
                            </CardContent>
                        </Card>

                        {/* Margen */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm font-medium">Margen</CardTitle>
                                <DollarSign className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className={cn(
                                    "text-2xl font-bold",
                                    producto.margen_porcentaje !== null && producto.margen_porcentaje < 10 && "text-red-600",
                                    producto.margen_porcentaje !== null && producto.margen_porcentaje >= 20 && "text-green-600"
                                )}>
                                    {producto.margen_porcentaje !== null ? `${producto.margen_porcentaje}%` : 'N/A'}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Precio: {formatCurrency(producto.precio_venta)}
                                    {producto.precio_compra_promedio && (
                                        <> | Costo: {formatCurrency(producto.precio_compra_promedio)}</>
                                    )}
                                </p>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Gráfico de ventas */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle>Historial de Ventas</CardTitle>
                                <CardDescription>Unidades vendidas por día</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {chartData.length > 0 && chartData[0].data.length > 0 ? (
                                    <div className="h-[300px]">
                                        <ResponsiveLine
                                            data={chartData}
                                            margin={{ top: 20, right: 20, bottom: 50, left: 50 }}
                                            xScale={{ type: 'point' }}
                                            yScale={{ type: 'linear', min: 0, max: 'auto' }}
                                            curve="monotoneX"
                                            axisBottom={{
                                                tickSize: 5,
                                                tickPadding: 5,
                                                tickRotation: -45,
                                                format: (v) => v.slice(5), // MM-DD
                                            }}
                                            axisLeft={{
                                                tickSize: 5,
                                                tickPadding: 5,
                                                legend: 'Cantidad',
                                                legendOffset: -40,
                                                legendPosition: 'middle',
                                            }}
                                            colors={['hsl(var(--primary))']}
                                            pointSize={8}
                                            pointColor={{ theme: 'background' }}
                                            pointBorderWidth={2}
                                            pointBorderColor={{ from: 'serieColor' }}
                                            enableArea={true}
                                            areaOpacity={0.1}
                                            useMesh={true}
                                        />
                                    </div>
                                ) : (
                                    <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                                        No hay datos de ventas para mostrar
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Tabla de historial */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle>Detalle de Ventas</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Fecha</TableHead>
                                            <TableHead className="text-right">Cantidad</TableHead>
                                            <TableHead className="text-right">Total</TableHead>
                                            <TableHead className="text-right">Precio</TableHead>
                                            <TableHead className="text-right">Costo</TableHead>
                                            <TableHead>Vendedor</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {producto.historial_ventas.slice(0, 20).map((venta, idx) => (
                                            <TableRow key={idx}>
                                                <TableCell>{venta.fecha_venta}</TableCell>
                                                <TableCell className="text-right font-mono">{venta.cantidad}</TableCell>
                                                <TableCell className="text-right font-mono">
                                                    {formatCurrency(venta.total_venta)}
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    {formatCurrency(venta.precio_promedio)}
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    {venta.costo_promedio ? formatCurrency(venta.costo_promedio) : '-'}
                                                </TableCell>
                                                <TableCell className="max-w-[150px] truncate">
                                                    {venta.vendedores || '-'}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>
                    </motion.div>
                </>
            )}
        </div>
    );
}

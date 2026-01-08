import { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
    Package,
    AlertTriangle,
    BarChart3,
    DollarSign,
    Box,
    Search
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Input } from '../components/ui/input';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../components/ui/table';
import { Select } from '../components/ui/select';
import { api } from '../services/api';
import { cn } from '../lib/utils';

// Types
interface ProductoInventario {
    nombre: string;
    familia: string | null;
    proveedor: string | null;
    stock_actual: number;
    stock_minimo: number;
    stock_maximo: number;
    precio_venta: number;
    precio_compra: number | null;
    venta_diaria: number;
    dias_cobertura: number | null;
    rotacion: number | null;
    estado_stock: string;
    valor_inventario: number;
    margen_porcentaje: number | null;
    cantidad_vendida_30d: number;
}

interface ResumenInventario {
    total_productos: number;
    total_unidades: number;
    valor_total: number;
    productos_criticos: number;
    productos_bajos: number;
    productos_normales: number;
    productos_exceso: number;
    rotacion_promedio: number;
    valor_criticos: number;
    valor_exceso: number;
}

interface AlertaInventario {
    tipo: string;
    icono: string;
    titulo: string;
    detalle: string;
    datos: ProductoInventario[];
}

// API hooks
const useInventario = (estado?: string) => {
    return useQuery({
        queryKey: ['inventario', estado],
        queryFn: () => api.get<{ data: ProductoInventario[]; total: number }>(
            '/api/inventario',
            { estado, limite: 200 }
        ),
    });
};

const useResumenInventario = () => {
    return useQuery({
        queryKey: ['inventario-resumen'],
        queryFn: () => api.get<ResumenInventario>('/api/inventario/resumen'),
    });
};

const useAlertasInventario = () => {
    return useQuery({
        queryKey: ['inventario-alertas'],
        queryFn: () => api.get<AlertaInventario[]>('/api/inventario/alertas'),
    });
};

// Format currency
const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
};

export function Inventario() {
    const [filtroEstado, setFiltroEstado] = useState<string>('todos');
    const [busqueda, setBusqueda] = useState('');

    const { data: inventarioData, isLoading: loadingInventario } = useInventario(
        filtroEstado !== 'todos' ? filtroEstado : undefined
    );
    const { data: resumen, isLoading: loadingResumen } = useResumenInventario();
    const { data: alertas, isLoading: loadingAlertas } = useAlertasInventario();

    // Filter by search
    const productosFiltrados = inventarioData?.data?.filter(p =>
        p.nombre.toLowerCase().includes(busqueda.toLowerCase()) ||
        p.familia?.toLowerCase().includes(busqueda.toLowerCase()) ||
        p.proveedor?.toLowerCase().includes(busqueda.toLowerCase())
    ) || [];

    const estadoColors: Record<string, string> = {
        '🔴 Crítico': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        '🟠 Bajo': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
        '🟢 Normal': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        '🔵 Exceso': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 className="text-3xl font-bold tracking-tight">📦 Gestión de Inventario</h1>
                <p className="text-muted-foreground">
                    Stock en tiempo real, alertas y análisis de rotación
                </p>
            </motion.div>

            {/* KPIs */}
            {loadingResumen ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-[120px]" />)}
                </div>
            ) : resumen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
                >
                    {/* Valor Total */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Valor del Inventario</CardTitle>
                            <DollarSign className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{formatCurrency(resumen.valor_total)}</div>
                            <p className="text-xs text-muted-foreground">
                                {resumen.total_unidades.toLocaleString()} unidades en stock
                            </p>
                        </CardContent>
                    </Card>

                    {/* Productos Críticos */}
                    <Card className={cn(resumen.productos_criticos > 0 && 'border-red-500/50')}>
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Stock Crítico</CardTitle>
                            <AlertTriangle className="h-4 w-4 text-red-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-red-600">
                                {resumen.productos_criticos}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Valor en riesgo: {formatCurrency(resumen.valor_criticos)}
                            </p>
                        </CardContent>
                    </Card>

                    {/* Productos con Exceso */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Stock en Exceso</CardTitle>
                            <Box className="h-4 w-4 text-blue-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-blue-600">
                                {resumen.productos_exceso}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Capital inmovilizado: {formatCurrency(resumen.valor_exceso)}
                            </p>
                        </CardContent>
                    </Card>

                    {/* Rotación Promedio */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Rotación Promedio</CardTitle>
                            <BarChart3 className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{resumen.rotacion_promedio}x</div>
                            <p className="text-xs text-muted-foreground">
                                veces al año
                            </p>
                        </CardContent>
                    </Card>
                </motion.div>
            )}

            {/* Alertas */}
            {!loadingAlertas && alertas && alertas.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="space-y-4"
                >
                    {alertas.slice(0, 2).map((alerta, idx) => (
                        <Card
                            key={idx}
                            className={cn(
                                alerta.tipo === 'error' && 'border-red-500/50 bg-red-50/50 dark:bg-red-950/20',
                                alerta.tipo === 'warning' && 'border-orange-500/50 bg-orange-50/50 dark:bg-orange-950/20',
                            )}
                        >
                            <CardHeader className="pb-2">
                                <CardTitle className="flex items-center gap-2 text-lg">
                                    <span>{alerta.icono}</span>
                                    {alerta.titulo}
                                </CardTitle>
                                <CardDescription>{alerta.detalle}</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="flex flex-wrap gap-2">
                                    {alerta.datos.slice(0, 6).map((producto, i) => (
                                        <Badge key={i} variant="outline" className="text-sm">
                                            {producto.nombre}
                                            <span className="ml-1 text-muted-foreground">
                                                ({producto.stock_actual} uds)
                                            </span>
                                        </Badge>
                                    ))}
                                    {alerta.datos.length > 6 && (
                                        <Badge variant="secondary">
                                            +{alerta.datos.length - 6} más
                                        </Badge>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </motion.div>
            )}

            {/* Filtros y búsqueda */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="flex flex-col md:flex-row gap-4"
            >
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Buscar producto, familia o proveedor..."
                        value={busqueda}
                        onChange={(e) => setBusqueda(e.target.value)}
                        className="pl-10"
                    />
                </div>
                <Select
                    value={filtroEstado}
                    onChange={(e) => setFiltroEstado(e.target.value)}
                    className="w-[200px]"
                    options={[
                        { value: 'todos', label: 'Todos los estados' },
                        { value: 'critico', label: '🔴 Crítico' },
                        { value: 'bajo', label: '🟠 Bajo' },
                        { value: 'normal', label: '🟢 Normal' },
                        { value: 'exceso', label: '🔵 Exceso' },
                    ]}
                />
            </motion.div>

            {/* Tabla de inventario */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
            >
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Package className="h-5 w-5" />
                            Inventario Completo
                            <Badge variant="secondary" className="ml-2">
                                {productosFiltrados.length} productos
                            </Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {loadingInventario ? (
                            <Skeleton className="h-[400px]" />
                        ) : (
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Estado</TableHead>
                                            <TableHead>Producto</TableHead>
                                            <TableHead>Familia</TableHead>
                                            <TableHead className="text-right">Stock</TableHead>
                                            <TableHead className="text-right">Venta/día</TableHead>
                                            <TableHead className="text-right">Días Cobertura</TableHead>
                                            <TableHead className="text-right">Rotación</TableHead>
                                            <TableHead className="text-right">Valor</TableHead>
                                            <TableHead className="text-right">Margen</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {productosFiltrados.slice(0, 50).map((producto, idx) => (
                                            <TableRow key={idx} className="hover:bg-muted/50">
                                                <TableCell>
                                                    <span className={cn(
                                                        'px-2 py-1 rounded-full text-xs font-medium',
                                                        estadoColors[producto.estado_stock]
                                                    )}>
                                                        {producto.estado_stock}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="font-medium max-w-[200px] truncate">
                                                    {producto.nombre}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {producto.familia || '-'}
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    <span className={cn(
                                                        producto.stock_actual <= 5 && 'text-red-600 font-bold'
                                                    )}>
                                                        {producto.stock_actual}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    {producto.venta_diaria.toFixed(1)}
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    <span className={cn(
                                                        producto.dias_cobertura !== null && producto.dias_cobertura <= 3 && 'text-red-600',
                                                        producto.dias_cobertura !== null && producto.dias_cobertura > 3 && producto.dias_cobertura <= 7 && 'text-orange-600'
                                                    )}>
                                                        {producto.dias_cobertura?.toFixed(0) || '∞'}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    {producto.rotacion?.toFixed(1) || '-'}x
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    {formatCurrency(producto.valor_inventario)}
                                                </TableCell>
                                                <TableCell className="text-right font-mono">
                                                    <span className={cn(
                                                        producto.margen_porcentaje !== null && producto.margen_porcentaje < 10 && 'text-red-600',
                                                        producto.margen_porcentaje !== null && producto.margen_porcentaje >= 20 && 'text-green-600'
                                                    )}>
                                                        {producto.margen_porcentaje?.toFixed(1) || '-'}%
                                                    </span>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                                {productosFiltrados.length > 50 && (
                                    <div className="text-center py-4 text-muted-foreground">
                                        Mostrando 50 de {productosFiltrados.length} productos
                                    </div>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </motion.div>
        </div>
    );
}

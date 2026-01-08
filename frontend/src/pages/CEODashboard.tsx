import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
    DollarSign,
    ShoppingCart,
    TrendingUp,
    TrendingDown,
    Package,
    Lightbulb,
    BarChart3,
    Users,
    RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';
import { api } from '../services/api';
import { cn } from '../lib/utils';

// Types
interface KPIsEjecutivo {
    ventas_hoy: number;
    transacciones_hoy: number;
    delta_vs_ayer: number;
    ventas_mes: number;
    transacciones_mes: number;
    productos_vendidos: number;
    ticket_promedio: number;
    margen_total: number;
}

interface Insight {
    tipo: string;
    icono: string;
    titulo: string;
    descripcion: string;
}

// API hooks
const useKPIs = () => {
    return useQuery({
        queryKey: ['kpis-ejecutivo'],
        queryFn: () => api.get<KPIsEjecutivo>('/api/insights/kpis'),
        refetchInterval: 60000, // Refresh every minute
    });
};

const useInsights = () => {
    return useQuery({
        queryKey: ['insights'],
        queryFn: () => api.get<Insight[]>('/api/insights'),
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

export function CEODashboard() {
    const { data: kpis, isLoading: loadingKPIs, refetch: refetchKPIs } = useKPIs();
    const { data: insights, isLoading: loadingInsights } = useInsights();

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">🏢 Dashboard Ejecutivo</h1>
                    <p className="text-muted-foreground">
                        Vista consolidada del negocio en tiempo real
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="icon"
                    onClick={() => refetchKPIs()}
                >
                    <RefreshCw className="h-4 w-4" />
                </Button>
            </motion.div>

            {/* Main KPIs */}
            {loadingKPIs ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-[140px]" />)}
                </div>
            ) : kpis && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
                >
                    {/* Ventas Hoy */}
                    <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Ventas Hoy</CardTitle>
                            <DollarSign className="h-5 w-5 text-blue-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold">{formatCurrency(kpis.ventas_hoy)}</div>
                            <div className="flex items-center gap-2 mt-1">
                                {kpis.delta_vs_ayer >= 0 ? (
                                    <TrendingUp className="h-4 w-4 text-green-500" />
                                ) : (
                                    <TrendingDown className="h-4 w-4 text-red-500" />
                                )}
                                <span className={cn(
                                    "text-sm",
                                    kpis.delta_vs_ayer >= 0 ? "text-green-600" : "text-red-600"
                                )}>
                                    {kpis.delta_vs_ayer >= 0 ? '+' : ''}{kpis.delta_vs_ayer}% vs ayer
                                </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                                {kpis.transacciones_hoy} transacciones
                            </p>
                        </CardContent>
                    </Card>

                    {/* Ventas del Mes */}
                    <Card className="bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-500/20">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Ventas del Mes</CardTitle>
                            <BarChart3 className="h-5 w-5 text-green-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold">{formatCurrency(kpis.ventas_mes)}</div>
                            <p className="text-xs text-muted-foreground mt-2">
                                {kpis.transacciones_mes} transacciones en 30 días
                            </p>
                        </CardContent>
                    </Card>

                    {/* Margen Total */}
                    <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Margen Total</CardTitle>
                            <TrendingUp className="h-5 w-5 text-purple-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold">{formatCurrency(kpis.margen_total)}</div>
                            <p className="text-xs text-muted-foreground mt-2">
                                Ganancia bruta del período
                            </p>
                        </CardContent>
                    </Card>

                    {/* Ticket Promedio */}
                    <Card className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border-orange-500/20">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Ticket Promedio</CardTitle>
                            <ShoppingCart className="h-5 w-5 text-orange-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold">{formatCurrency(kpis.ticket_promedio)}</div>
                            <p className="text-xs text-muted-foreground mt-2">
                                {kpis.productos_vendidos} productos únicos vendidos
                            </p>
                        </CardContent>
                    </Card>
                </motion.div>
            )}

            {/* Insights Automáticos */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Lightbulb className="h-5 w-5 text-yellow-500" />
                            Insights del Negocio
                        </CardTitle>
                        <CardDescription>
                            Recomendaciones generadas automáticamente basadas en tus datos
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loadingInsights ? (
                            <div className="space-y-4">
                                {[1, 2, 3].map(i => <Skeleton key={i} className="h-[80px]" />)}
                            </div>
                        ) : insights && insights.length > 0 ? (
                            <div className="grid gap-4 md:grid-cols-2">
                                {insights.map((insight, idx) => (
                                    <motion.div
                                        key={idx}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: idx * 0.1 }}
                                        className={cn(
                                            "p-4 rounded-lg border",
                                            insight.tipo === 'positive' && "bg-green-50/50 border-green-500/20 dark:bg-green-950/20",
                                            insight.tipo === 'warning' && "bg-orange-50/50 border-orange-500/20 dark:bg-orange-950/20",
                                            insight.tipo === 'negative' && "bg-red-50/50 border-red-500/20 dark:bg-red-950/20"
                                        )}
                                    >
                                        <div className="flex items-start gap-3">
                                            <span className="text-2xl">{insight.icono}</span>
                                            <div>
                                                <h4 className="font-semibold">{insight.titulo}</h4>
                                                <p className="text-sm text-muted-foreground mt-1">
                                                    {insight.descripcion}
                                                </p>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">
                                <Lightbulb className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                <p>No hay insights disponibles en este momento</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </motion.div>

            {/* Quick Actions */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="grid gap-4 md:grid-cols-3"
            >
                <Card className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => window.location.href = '/inventario'}>
                    <CardContent className="flex items-center gap-4 pt-6">
                        <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
                            <Package className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold">Gestión de Inventario</h3>
                            <p className="text-sm text-muted-foreground">Ver stock y alertas</p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => window.location.href = '/compras'}>
                    <CardContent className="flex items-center gap-4 pt-6">
                        <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
                            <ShoppingCart className="h-6 w-6 text-green-600 dark:text-green-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold">Sugerencias de Compra</h3>
                            <p className="text-sm text-muted-foreground">Qué comprar y cuándo</p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => window.location.href = '/vendedores'}>
                    <CardContent className="flex items-center gap-4 pt-6">
                        <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
                            <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold">Desempeño de Equipo</h3>
                            <p className="text-sm text-muted-foreground">Ranking de vendedores</p>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>
        </div>
    );
}

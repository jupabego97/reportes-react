import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, Package, Percent, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useMetricas } from '../../hooks/useApi';
import { cn } from '../../lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: number;
  description?: string;
  delay?: number;
}

function MetricCard({ title, value, icon, trend, description, delay = 0 }: MetricCardProps) {
  const isPositive = trend && trend > 0;
  const isNegative = trend && trend < 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, delay }}
    >
      <Card className="hover:shadow-lg transition-shadow duration-300">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            {icon}
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{value}</div>
          {(trend !== undefined || description) && (
            <div className="flex items-center gap-1 mt-1">
              {trend !== undefined && (
                <span
                  className={cn(
                    'flex items-center text-xs font-medium',
                    isPositive && 'text-green-600',
                    isNegative && 'text-red-600',
                    !isPositive && !isNegative && 'text-muted-foreground'
                  )}
                >
                  {isPositive && <TrendingUp className="h-3 w-3 mr-0.5" />}
                  {isNegative && <TrendingDown className="h-3 w-3 mr-0.5" />}
                  {trend > 0 ? '+' : ''}{trend.toFixed(1)}%
                </span>
              )}
              {description && (
                <span className="text-xs text-muted-foreground">
                  {description}
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function MetricCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-4 w-20" />
      </CardContent>
    </Card>
  );
}

export function MetricCards() {
  const { data, isLoading, error } = useMetricas();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Error al cargar métricas
      </div>
    );
  }

  // Parsear delta a número
  const parseDelta = (delta: string | undefined): number | undefined => {
    if (!delta) return undefined;
    const num = parseFloat(delta.replace('%', '').replace('+', ''));
    return isNaN(num) ? undefined : num;
  };

  const metrics = [
    {
      title: 'Total Ventas',
      value: `$${data.total_ventas?.toLocaleString() || 0}`,
      icon: <DollarSign className="h-4 w-4" />,
      trend: parseDelta(data.delta_ventas),
      description: 'vs periodo anterior',
    },
    {
      title: 'Transacciones',
      value: data.total_registros?.toLocaleString() || 0,
      icon: <ShoppingCart className="h-4 w-4" />,
      trend: parseDelta(data.delta_registros),
      description: 'registros',
    },
    {
      title: 'Precio Promedio',
      value: `$${data.precio_promedio?.toLocaleString() || 0}`,
      icon: <DollarSign className="h-4 w-4" />,
      trend: parseDelta(data.delta_precio),
    },
    {
      title: 'Margen Promedio',
      value: `$${data.margen_promedio?.toFixed(2) || 0}`,
      icon: <Percent className="h-4 w-4" />,
    },
    {
      title: 'Margen Total',
      value: `$${data.margen_total?.toLocaleString() || 0}`,
      icon: <TrendingUp className="h-4 w-4" />,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {metrics.map((metric, index) => (
        <MetricCard
          key={metric.title}
          {...metric}
          delay={index * 0.05}
        />
      ))}
    </div>
  );
}

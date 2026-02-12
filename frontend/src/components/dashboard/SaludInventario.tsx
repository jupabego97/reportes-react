import { motion } from 'framer-motion';
import { Package, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { ProductLink } from '../ProductLink';
import { useSaludInventario } from '../../hooks/useApi';
import { cn } from '../../lib/utils';

export function SaludInventario() {
  const { data, isLoading, error } = useSaludInventario();

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Salud del inventario
          </CardTitle>
          <Skeleton className="h-8 w-8 rounded-lg" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-24 mb-3" />
          <Skeleton className="h-4 w-full mb-1" />
          <Skeleton className="h-4 w-3/4 mb-1" />
          <Skeleton className="h-4 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return null;
  }

  const { salud_porcentaje, top_criticos, total_productos } = data;
  const isHealthy = salud_porcentaje >= 70;
  const isWarning = salud_porcentaje >= 40 && salud_porcentaje < 70;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card className="hover:shadow-lg transition-shadow duration-300">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Salud del inventario
          </CardTitle>
          <div
            className={cn(
              'h-8 w-8 rounded-lg flex items-center justify-center',
              isHealthy && 'bg-green-500/10 text-green-600',
              isWarning && 'bg-amber-500/10 text-amber-600',
              !isHealthy && !isWarning && 'bg-red-500/10 text-red-600'
            )}
          >
            {isHealthy ? <Package className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          </div>
        </CardHeader>
        <CardContent>
          <div
            className={cn(
              'text-2xl font-bold',
              isHealthy && 'text-green-600',
              isWarning && 'text-amber-600',
              !isHealthy && !isWarning && 'text-red-600'
            )}
          >
            {salud_porcentaje}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {total_productos} productos con stock normal
          </p>
          {top_criticos.length > 0 && (
            <div className="mt-3 pt-3 border-t">
              <p className="text-xs font-medium text-muted-foreground mb-2">Productos más críticos</p>
              <ul className="space-y-1.5">
                {top_criticos.map((p) => (
                  <li key={p.nombre} className="flex items-center justify-between text-sm">
                    <ProductLink nombre={p.nombre} className="text-sm" />
                    {p.dias_cobertura != null && (
                      <span className="text-muted-foreground text-xs">
                        {p.dias_cobertura.toFixed(0)} días
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

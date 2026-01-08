import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, AlertCircle, Info, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { useAlertas } from '../../hooks/useApi';
import { cn } from '../../lib/utils';
import { toast } from 'sonner';

interface AlertItem {
  tipo: 'error' | 'warning' | 'info';
  titulo: string;
  mensaje: string;
  detalles?: string[];
}

const alertStyles = {
  error: {
    icon: AlertTriangle,
    className: 'border-red-500/50 bg-red-500/10',
    iconClassName: 'text-red-500',
    badgeVariant: 'destructive' as const,
  },
  warning: {
    icon: AlertCircle,
    className: 'border-yellow-500/50 bg-yellow-500/10',
    iconClassName: 'text-yellow-500',
    badgeVariant: 'secondary' as const,
  },
  info: {
    icon: Info,
    className: 'border-blue-500/50 bg-blue-500/10',
    iconClassName: 'text-blue-500',
    badgeVariant: 'outline' as const,
  },
};

function AlertCard({ alert, index }: { alert: AlertItem; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const style = alertStyles[alert.tipo];
  const Icon = style.icon;

  if (isDismissed) return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ delay: index * 0.1 }}
    >
      <Alert className={cn('relative', style.className)}>
        <Icon className={cn('h-4 w-4', style.iconClassName)} />
        <div className="flex-1">
          <AlertTitle className="flex items-center gap-2">
            {alert.titulo}
            <Badge variant={style.badgeVariant} className="ml-2">
              {alert.tipo}
            </Badge>
          </AlertTitle>
          <AlertDescription className="mt-1">
            {alert.mensaje}
          </AlertDescription>
          
          {alert.detalles && alert.detalles.length > 0 && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 p-0 h-auto text-xs"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="h-3 w-3 mr-1" />
                    Ocultar detalles
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    Ver {alert.detalles.length} detalles
                  </>
                )}
              </Button>
              
              <AnimatePresence>
                {isExpanded && (
                  <motion.ul
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 space-y-1 text-sm"
                  >
                    {alert.detalles.slice(0, 5).map((detalle, i) => (
                      <li key={i} className="text-muted-foreground">
                        • {detalle}
                      </li>
                    ))}
                    {alert.detalles.length > 5 && (
                      <li className="text-muted-foreground italic">
                        ... y {alert.detalles.length - 5} más
                      </li>
                    )}
                  </motion.ul>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
        
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 h-6 w-6 opacity-50 hover:opacity-100"
          onClick={() => {
            setIsDismissed(true);
            toast.info('Alerta descartada');
          }}
        >
          <X className="h-4 w-4" />
        </Button>
      </Alert>
    </motion.div>
  );
}

export function AlertSystem() {
  const { data: alertas, isLoading, error } = useAlertas();
  const [showAll, setShowAll] = useState(false);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Alertas del Sistema</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return null;
  }

  const alerts: AlertItem[] = alertas || [];
  const displayedAlerts = showAll ? alerts : alerts.slice(0, 3);

  if (alerts.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Card>
          <CardContent className="py-6">
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <Info className="h-5 w-5" />
              <span>No hay alertas activas</span>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            🚨 Alertas
            <Badge variant="destructive">{alerts.length}</Badge>
          </CardTitle>
          {alerts.length > 3 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? 'Ver menos' : `Ver todas (${alerts.length})`}
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <AnimatePresence mode="popLayout">
            {displayedAlerts.map((alert, index) => (
              <AlertCard key={`${alert.tipo}-${index}`} alert={alert} index={index} />
            ))}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}

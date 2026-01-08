import { motion } from 'framer-motion';
import { FilterPanel } from '../components/filters/FilterPanel';
import { MetricCards } from '../components/dashboard/MetricCards';
import { AlertSystem } from '../components/dashboard/AlertSystem';
import { VentasDiarias } from '../components/charts/VentasDiarias';
import { VentasVendedor } from '../components/charts/VentasVendedor';
import { VentasFamilia } from '../components/charts/VentasFamilia';
import { VentasMetodo } from '../components/charts/VentasMetodo';
import { VentasHeatmap } from '../components/charts/VentasHeatmap';

export function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard de Ventas</h1>
          <p className="text-muted-foreground">
            Resumen de los últimos 30 días
          </p>
        </div>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {/* Métricas */}
      <MetricCards />

      {/* Alertas */}
      <AlertSystem />

      {/* Gráficos principales */}
      <div className="grid gap-6 lg:grid-cols-2">
        <VentasDiarias />
        <VentasVendedor />
      </div>

      {/* Gráficos secundarios */}
      <div className="grid gap-6 lg:grid-cols-2">
        <VentasFamilia />
        <VentasMetodo />
      </div>

      {/* Heatmap */}
      <VentasHeatmap />
    </div>
  );
}

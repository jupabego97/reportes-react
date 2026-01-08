import { motion } from 'framer-motion';
import { FilterPanel } from '../components/filters/FilterPanel';
import { DataTable } from '../components/data/DataTable';

export function Datos() {
  return (
    <div className="space-y-6">
      {/* Título */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold tracking-tight">Datos Detallados</h1>
        <p className="text-muted-foreground">
          Explora todos los registros de ventas
        </p>
      </motion.div>

      {/* Filtros */}
      <FilterPanel />

      {/* Tabla de datos */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <DataTable />
      </motion.div>
    </div>
  );
}

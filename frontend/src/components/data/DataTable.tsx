import { useState, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpDown, ArrowUp, ArrowDown, Download, FileSpreadsheet, FileText } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Pagination } from '../ui/pagination';
import { useVentas, useExportExcel, useExportCSV, useExportPDF } from '../../hooks/useApi';
import { cn } from '../../lib/utils';
import { ProductLink } from '../ProductLink';

type SortDirection = 'asc' | 'desc' | null;

interface Column {
  key: string;
  label: string;
  sortable?: boolean;
  format?: (value: any) => string;
  render?: (value: any, row: any) => ReactNode;
  className?: string;
}

const columns: Column[] = [
  { key: 'fecha_venta', label: 'Fecha', sortable: true },
  {
    key: 'nombre',
    label: 'Producto',
    sortable: true,
    render: (v) => (v ? <ProductLink nombre={v} /> : '-'),
  },
  { key: 'vendedor', label: 'Vendedor', sortable: true },
  { key: 'familia', label: 'Familia', sortable: true },
  { 
    key: 'cantidad', 
    label: 'Cantidad', 
    sortable: true,
    className: 'text-right',
    format: (v) => v?.toLocaleString() || '0'
  },
  { 
    key: 'precio', 
    label: 'Precio', 
    sortable: true,
    className: 'text-right',
    format: (v) => `$${v?.toLocaleString() || '0'}`
  },
  { 
    key: 'total_venta', 
    label: 'Total', 
    sortable: true,
    className: 'text-right',
    format: (v) => `$${v?.toLocaleString() || '0'}`
  },
  { 
    key: 'margen_porcentaje', 
    label: 'Margen %', 
    sortable: true,
    className: 'text-right',
    format: (v) => v !== null ? `${v?.toFixed(1)}%` : '-'
  },
  { key: 'metodo', label: 'Método', sortable: true },
];

export function DataTable() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const { data, isLoading, error } = useVentas(page, pageSize);
  const exportExcel = useExportExcel();
  const exportCSV = useExportCSV();
  const exportPDF = useExportPDF();

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortColumn(null);
        setSortDirection(null);
      }
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (column: string) => {
    if (sortColumn !== column) {
      return <ArrowUpDown className="h-4 w-4 opacity-50" />;
    }
    if (sortDirection === 'asc') {
      return <ArrowUp className="h-4 w-4" />;
    }
    return <ArrowDown className="h-4 w-4" />;
  };

  // Sort data locally (for demo - in production this would be server-side)
  const sortedData = data?.data ? [...data.data].sort((a, b) => {
    if (!sortColumn || !sortDirection) return 0;
    
    const aVal = (a as any)[sortColumn];
    const bVal = (b as any)[sortColumn];
    
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;
    
    const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortDirection === 'asc' ? comparison : -comparison;
  }) : [];

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error al cargar datos: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header con acciones */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {data && (
            <>
              Mostrando {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, data.total_registros)} de {data.total_registros.toLocaleString()} registros
            </>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportCSV.mutate()}
            disabled={exportCSV.isPending}
          >
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportExcel.mutate()}
            disabled={exportExcel.isPending}
          >
            <FileSpreadsheet className="h-4 w-4 mr-2" />
            Excel
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportPDF.mutate()}
            disabled={exportPDF.isPending}
          >
            <FileText className="h-4 w-4 mr-2" />
            PDF
          </Button>
        </div>
      </div>

      {/* Tabla */}
      <div className="rounded-md border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  className={cn(
                    column.sortable && 'cursor-pointer select-none hover:bg-muted/50',
                    column.className
                  )}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  <div className="flex items-center gap-1">
                    {column.label}
                    {column.sortable && getSortIcon(column.key)}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              // Skeleton loading
              Array.from({ length: pageSize }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((column) => (
                    <TableCell key={column.key}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : sortedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center py-8">
                  No se encontraron registros
                </TableCell>
              </TableRow>
            ) : (
              sortedData.map((row, index) => (
                <motion.tr
                  key={index}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.02 }}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  {columns.map((column) => (
                    <TableCell key={column.key} className={column.className}>
                      {column.render
                        ? column.render((row as any)[column.key], row)
                        : column.format
                        ? column.format((row as any)[column.key])
                        : (row as any)[column.key] || '-'}
                    </TableCell>
                  ))}
                </motion.tr>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Paginación */}
      {data && data.total_pages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={data.total_pages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}


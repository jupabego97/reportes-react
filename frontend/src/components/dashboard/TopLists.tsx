import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Skeleton } from '../ui/skeleton';
import { formatCurrency, formatNumber } from '../../lib/utils';
import type { TopProducto, TopVendedor } from '../../types';

interface TopListsProps {
  topProductos: TopProducto[];
  topVendedores: TopVendedor[];
  isLoading: boolean;
}

export function TopLists({ topProductos, topVendedores, isLoading }: TopListsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[...Array(2)].map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-48" />
            </CardHeader>
            <CardContent>
              {[...Array(5)].map((_, j) => (
                <Skeleton key={j} className="mb-2 h-8 w-full" />
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🏆 Top 5 Productos Más Vendidos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Producto</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {topProductos.map((producto, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">{producto.nombre}</TableCell>
                  <TableCell className="text-right">{formatNumber(producto.cantidad)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(producto.total_venta)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">👥 Top 5 Vendedores</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vendedor</TableHead>
                <TableHead className="text-right">Ventas</TableHead>
                <TableHead className="text-right">Unidades</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {topVendedores.map((vendedor, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">{vendedor.vendedor}</TableCell>
                  <TableCell className="text-right">{formatCurrency(vendedor.total_venta)}</TableCell>
                  <TableCell className="text-right">{formatNumber(vendedor.cantidad)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}


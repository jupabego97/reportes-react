import type { ReactNode } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ChevronRight, Home, Bell } from 'lucide-react';
import { ThemeToggle } from '../ui/theme-toggle';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';

const routeNames: Record<string, string> = {
  '': 'Dashboard',
  'margenes': 'Analisis de Margenes',
  'predicciones': 'Predicciones',
  'abc': 'Analisis ABC',
  'vendedores': 'Ranking de Vendedores',
  'proveedores': 'Analisis de Proveedores',
  'compras': 'Sugerencias de Compra',
  'insights': 'Insights de Inventario',
  'datos': 'Datos Detallados',
};

interface HeaderProps {
  children?: ReactNode;
}

export function Header({ children }: HeaderProps) {
  const location = useLocation();
  const pathSegments = location.pathname.split('/').filter(Boolean);

  const breadcrumbs = [
    { name: 'Inicio', href: '/' },
    ...pathSegments.map((segment, index) => ({
      name: routeNames[segment] || segment,
      href: '/' + pathSegments.slice(0, index + 1).join('/'),
    })),
  ];

  return (
    <header className="sticky top-0 z-40 flex h-14 md:h-16 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-3 md:px-6">
      {/* Left side: Mobile menu + Breadcrumbs */}
      <div className="flex items-center gap-2">
        {children}

        <nav className="hidden sm:flex items-center space-x-1 text-sm text-muted-foreground">
          {breadcrumbs.map((crumb, index) => (
            <div key={crumb.href} className="flex items-center">
              {index > 0 && <ChevronRight className="h-4 w-4 mx-1" />}
              {index === 0 ? (
                <Link
                  to={crumb.href}
                  className="flex items-center hover:text-foreground transition-colors"
                >
                  <Home className="h-4 w-4" />
                </Link>
              ) : index === breadcrumbs.length - 1 ? (
                <span className="font-medium text-foreground">{crumb.name}</span>
              ) : (
                <Link
                  to={crumb.href}
                  className="hover:text-foreground transition-colors"
                >
                  {crumb.name}
                </Link>
              )}
            </div>
          ))}
        </nav>

        <span className="sm:hidden text-sm font-medium text-foreground truncate max-w-[150px]">
          {breadcrumbs.length > 1 ? breadcrumbs[breadcrumbs.length - 1].name : 'Dashboard'}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 md:gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative h-9 w-9">
              <Bell className="h-4 w-4 md:h-5 md:w-5" />
              <Badge className="absolute -top-1 -right-1 h-4 w-4 md:h-5 md:w-5 p-0 flex items-center justify-center text-[10px] md:text-xs">
                3
              </Badge>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72 md:w-80">
            <DropdownMenuLabel>Notificaciones</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
              <span className="font-medium text-red-600">Margen Negativo</span>
              <span className="text-xs text-muted-foreground">
                3 productos con margen negativo detectados
              </span>
            </DropdownMenuItem>
            <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
              <span className="font-medium text-yellow-600">Stock Bajo</span>
              <span className="text-xs text-muted-foreground">
                5 productos necesitan reposicion
              </span>
            </DropdownMenuItem>
            <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
              <span className="font-medium text-blue-600">Meta Alcanzada</span>
              <span className="text-xs text-muted-foreground">
                Vendedor Juan supero su meta mensual
              </span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <ThemeToggle />
      </div>
    </header>
  );
}

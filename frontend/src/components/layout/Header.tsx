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
  'margenes': 'Análisis de Márgenes',
  'predicciones': 'Predicciones',
  'abc': 'Análisis ABC',
  'vendedores': 'Ranking de Vendedores',
  'proveedores': 'Análisis de Proveedores',
  'compras': 'Sugerencias de Compra',
  'datos': 'Datos Detallados',
};

export function Header() {
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
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6">
      {/* Breadcrumbs */}
      <nav className="flex items-center space-x-1 text-sm text-muted-foreground">
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

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <Badge className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs">
                3
              </Badge>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Notificaciones</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
              <span className="font-medium text-red-600">⚠️ Margen Negativo</span>
              <span className="text-xs text-muted-foreground">
                3 productos con margen negativo detectados
              </span>
            </DropdownMenuItem>
            <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
              <span className="font-medium text-yellow-600">📉 Stock Bajo</span>
              <span className="text-xs text-muted-foreground">
                5 productos necesitan reposición
              </span>
            </DropdownMenuItem>
            <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
              <span className="font-medium text-blue-600">📊 Meta Alcanzada</span>
              <span className="text-xs text-muted-foreground">
                Vendedor Juan superó su meta mensual
              </span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Theme Toggle */}
        <ThemeToggle />
      </div>
    </header>
  );
}

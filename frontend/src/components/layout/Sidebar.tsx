import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  TrendingUp,
  LineChart,
  BarChart3,
  Users,
  Table,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User,
  Truck,
  PackageSearch,
  Menu,
  X,
  Receipt,
  CalendarCheck,
  Warehouse,
  Lightbulb,
  MessageSquareText,
  PieChart,
  ListChecks,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuthStore } from '../../stores/useAuthStore';
import { apiService } from '../../services/api';
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '../ui/tooltip';

type NavItem = { name: string; href: string; icon: LucideIcon };

const destacadoNav: NavItem[] = [
  { name: 'Decisiones', href: '/decisiones', icon: ListChecks },
  { name: 'Vista CEO', href: '/ceo', icon: PieChart },
];

const operacionNav: NavItem[] = [
  { name: 'Hoy', href: '/', icon: CalendarCheck },
  { name: 'Compras', href: '/compras', icon: PackageSearch },
  { name: 'Inventario', href: '/inventario', icon: Warehouse },
  { name: 'Proveedores', href: '/proveedores', icon: Truck },
];

const analisisNav: NavItem[] = [
  { name: 'Ventas', href: '/ventas', icon: LayoutDashboard },
  { name: 'Márgenes', href: '/margenes', icon: TrendingUp },
  { name: 'Predicciones', href: '/predicciones', icon: LineChart },
  { name: 'Análisis ABC', href: '/abc', icon: BarChart3 },
  { name: 'Vendedores', href: '/vendedores', icon: Users },
  { name: 'Facturas proveedor', href: '/facturas', icon: Receipt },
  { name: 'Insights', href: '/insights', icon: Lightbulb },
  { name: 'Datos', href: '/datos', icon: Table },
  { name: 'Analista', href: '/analista', icon: MessageSquareText },
];

const roleColors: Record<string, string> = {
  admin: 'bg-red-500',
  vendedor: 'bg-blue-500',
  viewer: 'bg-gray-500',
};

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

function NavItems({
  items,
  collapsed,
  onNavClick,
  destacado = false,
}: {
  items: NavItem[];
  collapsed: boolean;
  onNavClick: () => void;
  destacado?: boolean;
}) {
  return (
    <>
      {items.map((item) => (
        <Tooltip key={item.href} delayDuration={collapsed ? 0 : 1000}>
          <TooltipTrigger asChild>
            <NavLink
              to={item.href}
              end={item.href === '/'}
              onClick={onNavClick}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : destacado
                      ? 'border border-primary/40 bg-primary/10 text-foreground hover:bg-primary/15'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  collapsed && 'justify-center px-2'
                )
              }
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              <AnimatePresence mode="wait">
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="overflow-hidden whitespace-nowrap"
                  >
                    {item.name}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          </TooltipTrigger>
          {collapsed && (
            <TooltipContent side="right">{item.name}</TooltipContent>
          )}
        </Tooltip>
      ))}
    </>
  );
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await apiService.logout();
    } catch {
      /* ignorar si el backend no responde */
    }
    logout();
    navigate('/login');
  };

  const handleNavClick = () => {
    if (onMobileClose) {
      onMobileClose();
    }
  };

  const SidebarContent = () => (
    <>
      <div className="flex h-16 items-center justify-between border-b px-4">
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.h1
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xl font-bold text-primary"
            >
              Operaciones
            </motion.h1>
          )}
        </AnimatePresence>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className="h-8 w-8 hidden md:flex"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
        {onMobileClose && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onMobileClose}
            className="h-8 w-8 md:hidden"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4 overflow-y-auto">
        {!collapsed && (
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Destacado
          </p>
        )}
        <NavItems items={destacadoNav} collapsed={collapsed} onNavClick={handleNavClick} destacado />

        <div className={cn('my-3 border-t', collapsed && 'mx-1')} />

        {!collapsed && (
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Operación
          </p>
        )}
        <NavItems items={operacionNav} collapsed={collapsed} onNavClick={handleNavClick} />

        <div className={cn('my-3 border-t', collapsed && 'mx-1')} />

        {!collapsed && (
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Análisis
          </p>
        )}
        <NavItems items={analisisNav} collapsed={collapsed} onNavClick={handleNavClick} />
      </nav>

      <div className="border-t p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                'w-full justify-start gap-2',
                collapsed && 'justify-center px-2'
              )}
            >
              <div
                className={cn(
                  'h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0',
                  roleColors[user?.role || 'viewer']
                )}
              >
                <User className="h-4 w-4 text-white" />
              </div>
              <AnimatePresence mode="wait">
                {!collapsed && user && (
                  <motion.div
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="flex flex-col items-start overflow-hidden"
                  >
                    <span className="text-sm font-medium truncate">
                      {user.full_name || user.username}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {user.role}
                    </Badge>
                  </motion.div>
                )}
              </AnimatePresence>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align={collapsed ? 'center' : 'end'} className="w-56">
            <DropdownMenuLabel>Mi Cuenta</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled>
              <User className="mr-2 h-4 w-4" />
              <span>{user?.username}</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Cerrar sesion</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </>
  );

  return (
    <>
      <motion.div
        initial={false}
        animate={{ width: collapsed ? 64 : 256 }}
        transition={{ duration: 0.2 }}
        className="hidden md:flex h-full flex-col bg-card border-r"
      >
        <SidebarContent />
      </motion.div>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={onMobileClose}
              className="fixed inset-0 z-40 bg-black md:hidden"
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 w-[280px] flex flex-col bg-card border-r md:hidden"
            >
              <SidebarContent />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={onClick}
      className="md:hidden"
    >
      <Menu className="h-5 w-5" />
    </Button>
  );
}

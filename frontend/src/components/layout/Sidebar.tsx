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
  Settings,
  Truck,
  PackageSearch,
  Lightbulb,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuthStore } from '../../stores/useAuthStore';
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

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Márgenes', href: '/margenes', icon: TrendingUp },
  { name: 'Predicciones', href: '/predicciones', icon: LineChart },
  { name: 'Análisis ABC', href: '/abc', icon: BarChart3 },
  { name: 'Vendedores', href: '/vendedores', icon: Users },
  { name: 'Proveedores', href: '/proveedores', icon: Truck },
  { name: 'Compras', href: '/compras', icon: PackageSearch },
  { name: 'Insights', href: '/insights', icon: Lightbulb },
  { name: 'Datos', href: '/datos', icon: Table },
];

const roleColors = {
  admin: 'bg-red-500',
  vendedor: 'bg-blue-500',
  viewer: 'bg-gray-500',
};

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <motion.div
      initial={false}
      animate={{ width: collapsed ? 64 : 256 }}
      transition={{ duration: 0.2 }}
      className="flex h-full flex-col bg-card border-r"
    >
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.h1
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xl font-bold text-primary"
            >
              📊 Ventas
            </motion.h1>
          )}
        </AnimatePresence>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className="h-8 w-8"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => (
          <Tooltip key={item.name} delayDuration={collapsed ? 0 : 1000}>
            <TooltipTrigger asChild>
              <NavLink
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
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
              <TooltipContent side="right">
                {item.name}
              </TooltipContent>
            )}
          </Tooltip>
        ))}
      </nav>

      {/* User section */}
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
              <div className={cn('h-8 w-8 rounded-full flex items-center justify-center', roleColors[user?.role || 'viewer'])}>
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
            <DropdownMenuItem disabled>
              <Settings className="mr-2 h-4 w-4" />
              <span>Configuración</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Cerrar sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.div>
  );
}

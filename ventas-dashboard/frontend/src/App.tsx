import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { Layout } from './components/layout/Layout';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Margenes } from './pages/Margenes';
import { Predicciones } from './pages/Predicciones';
import { AnalisisABC } from './pages/AnalisisABC';
import { Vendedores } from './pages/Vendedores';
import { Proveedores } from './pages/Proveedores';
import { Compras } from './pages/Compras';
import { Insights } from './pages/Insights';
import { Datos } from './pages/Datos';
import { initializeTheme } from './stores/useThemeStore';
import { TooltipProvider } from './components/ui/tooltip';

// Crear QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 segundos
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Página de no autorizado
function Unauthorized() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-destructive mb-4">403</h1>
        <p className="text-muted-foreground mb-4">No tienes permiso para acceder a esta página</p>
        <a href="/" className="text-primary hover:underline">Volver al inicio</a>
      </div>
    </div>
  );
}

function App() {
  // Inicializar tema al cargar
  useEffect(() => {
    initializeTheme();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            {/* Rutas públicas */}
            <Route path="/login" element={<Login />} />
            <Route path="/unauthorized" element={<Unauthorized />} />

            {/* Rutas protegidas */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="margenes" element={<Margenes />} />
              <Route path="predicciones" element={<Predicciones />} />
              <Route path="abc" element={<AnalisisABC />} />
              <Route path="vendedores" element={<Vendedores />} />
              <Route path="proveedores" element={<Proveedores />} />
              <Route path="compras" element={<Compras />} />
              <Route path="insights" element={<Insights />} />
              <Route path="datos" element={<Datos />} />
            </Route>

            {/* Redirección por defecto */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { Layout } from './components/layout/Layout';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Login } from './pages/Login';
import { Hoy } from './pages/Hoy';
import { Dashboard } from './pages/Dashboard';
import { Margenes } from './pages/Margenes';
import { Predicciones } from './pages/Predicciones';
import { AnalisisABC } from './pages/AnalisisABC';
import { Vendedores } from './pages/Vendedores';
import { Proveedores } from './pages/Proveedores';
import { Compras } from './pages/Compras';
import { Inventario } from './pages/Inventario';
import { Datos } from './pages/Datos';
import { FacturasProveedor } from './pages/FacturasProveedor';
import { ProductoDetalle } from './pages/ProductoDetalle';
import { Analista } from './pages/Analista';
import { Insights } from './pages/Insights';
import { CEODashboard } from './pages/CEODashboard';
import { Decisiones } from './pages/Decisiones';
import { initializeTheme } from './stores/useThemeStore';
import { TooltipProvider } from './components/ui/tooltip';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

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
  useEffect(() => {
    initializeTheme();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/unauthorized" element={<Unauthorized />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Hoy />} />
              <Route path="ventas" element={<Dashboard />} />
              <Route path="compras" element={<Compras />} />
              <Route path="decisiones" element={<Decisiones />} />
              <Route path="inventario" element={<Inventario />} />
              <Route path="proveedores" element={<Proveedores />} />
              <Route path="facturas" element={<FacturasProveedor />} />
              <Route path="margenes" element={<Margenes />} />
              <Route path="predicciones" element={<Predicciones />} />
              <Route path="abc" element={<AnalisisABC />} />
              <Route path="vendedores" element={<Vendedores />} />
              <Route path="insights" element={<Insights />} />
              <Route path="ceo" element={<CEODashboard />} />
              <Route path="datos" element={<Datos />} />
              <Route path="analista" element={<Analista />} />
              <Route path="producto/:nombre" element={<ProductoDetalle />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

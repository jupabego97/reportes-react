import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, X, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { MultiSelect } from '../ui/multi-select';
import { Slider } from '../ui/slider';
import { useFiltersStore } from '../../stores/useFiltersStore';
import { useFiltrosOpciones } from '../../hooks/useApi';
import { cn } from '../../lib/utils';

export function FilterPanel() {
  const [isExpanded, setIsExpanded] = useState(false);
  const { data: opciones, isLoading } = useFiltrosOpciones();
  
  const {
    fechaInicio,
    fechaFin,
    productos,
    vendedores,
    familias,
    metodos,
    proveedores,
    precioMin,
    precioMax,
    setFechaInicio,
    setFechaFin,
    setProductos,
    setVendedores,
    setFamilias,
    setMetodos,
    setProveedores,
    setPrecioMin,
    setPrecioMax,
    resetFilters,
  } = useFiltersStore();

  const [priceRange, setPriceRange] = useState<[number, number]>([0, 1000]);

  useEffect(() => {
    if (opciones) {
      setPriceRange([opciones.precio_min || 0, opciones.precio_max || 1000]);
    }
  }, [opciones]);

  const activeFiltersCount = [
    fechaInicio,
    fechaFin,
    productos.length > 0,
    vendedores.length > 0,
    familias.length > 0,
    metodos.length > 0,
    proveedores.length > 0,
    precioMin !== null,
    precioMax !== null,
  ].filter(Boolean).length;

  const handlePriceChange = (values: number[]) => {
    if (values.length >= 2) {
      setPrecioMin(values[0]);
      setPrecioMax(values[1]);
    }
  };

  const productosOptions = (opciones?.productos || []).map((p) => ({ value: p, label: p }));
  const vendedoresOptions = (opciones?.vendedores || []).map((v) => ({ value: v, label: v }));
  const familiasOptions = (opciones?.familias || []).map((f) => ({ value: f, label: f }));
  const metodosOptions = (opciones?.metodos || []).map((m) => ({ value: m, label: m }));
  const proveedoresOptions = (opciones?.proveedores || []).map((p) => ({ value: p, label: p }));

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            <CardTitle className="text-lg">Filtros</CardTitle>
            {activeFiltersCount > 0 && (
              <Badge variant="secondary">{activeFiltersCount} activos</Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {activeFiltersCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
                className="text-muted-foreground"
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                Limpiar
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="h-4 w-4 mr-1" />
                  Menos
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4 mr-1" />
                  Más
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Fila principal - siempre visible */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Fecha Inicio</label>
            <Input
              type="date"
              value={fechaInicio || ''}
              onChange={(e) => setFechaInicio(e.target.value || null)}
              max={fechaFin || undefined}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Fecha Fin</label>
            <Input
              type="date"
              value={fechaFin || ''}
              onChange={(e) => setFechaFin(e.target.value || null)}
              min={fechaInicio || undefined}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Vendedores</label>
            <MultiSelect
              options={vendedoresOptions}
              selected={vendedores}
              onChange={setVendedores}
              placeholder="Todos los vendedores"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Familias</label>
            <MultiSelect
              options={familiasOptions}
              selected={familias}
              onChange={setFamilias}
              placeholder="Todas las familias"
            />
          </div>
        </div>

        {/* Filtros expandidos */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-4 overflow-hidden"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Productos</label>
                  <MultiSelect
                    options={productosOptions}
                    selected={productos}
                    onChange={setProductos}
                    placeholder="Todos los productos"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Métodos de Pago</label>
                  <MultiSelect
                    options={metodosOptions}
                    selected={metodos}
                    onChange={setMetodos}
                    placeholder="Todos los métodos"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Proveedores</label>
                  <MultiSelect
                    options={proveedoresOptions}
                    selected={proveedores}
                    onChange={setProveedores}
                    placeholder="Todos los proveedores"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Rango de Precio: ${precioMin?.toLocaleString() || priceRange[0]} - ${precioMax?.toLocaleString() || priceRange[1]}
                  </label>
                  <Slider
                    defaultValue={[precioMin || priceRange[0], precioMax || priceRange[1]]}
                    min={priceRange[0]}
                    max={priceRange[1]}
                    step={100}
                    onValueChange={handlePriceChange}
                    className="mt-2"
                  />
                </div>
              </div>

              {/* Tags de filtros activos */}
              {activeFiltersCount > 0 && (
                <div className="flex flex-wrap gap-2 pt-4 border-t">
                  {fechaInicio && (
                    <Badge variant="secondary" className="gap-1">
                      Desde: {fechaInicio}
                      <X
                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => setFechaInicio(null)}
                      />
                    </Badge>
                  )}
                  {fechaFin && (
                    <Badge variant="secondary" className="gap-1">
                      Hasta: {fechaFin}
                      <X
                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => setFechaFin(null)}
                      />
                    </Badge>
                  )}
                  {vendedores.map((v) => (
                    <Badge key={v} variant="secondary" className="gap-1">
                      {v}
                      <X
                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => setVendedores(vendedores.filter((x) => x !== v))}
                      />
                    </Badge>
                  ))}
                  {familias.map((f) => (
                    <Badge key={f} variant="secondary" className="gap-1">
                      {f}
                      <X
                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => setFamilias(familias.filter((x) => x !== f))}
                      />
                    </Badge>
                  ))}
                  {productos.map((p) => (
                    <Badge key={p} variant="secondary" className="gap-1">
                      {p}
                      <X
                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => setProductos(productos.filter((x) => x !== p))}
                      />
                    </Badge>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}


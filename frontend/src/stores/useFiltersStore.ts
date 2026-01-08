import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FiltersState {
  // Fechas
  fechaInicio: string | null;
  fechaFin: string | null;
  
  // Multi-selects
  productos: string[];
  vendedores: string[];
  familias: string[];
  metodos: string[];
  proveedores: string[];
  
  // Rangos
  precioMin: number | null;
  precioMax: number | null;
  cantidadMin: number | null;
  cantidadMax: number | null;
  
  // Actions
  setFechaInicio: (fecha: string | null) => void;
  setFechaFin: (fecha: string | null) => void;
  setProductos: (productos: string[]) => void;
  setVendedores: (vendedores: string[]) => void;
  setFamilias: (familias: string[]) => void;
  setMetodos: (metodos: string[]) => void;
  setProveedores: (proveedores: string[]) => void;
  setPrecioMin: (precio: number | null) => void;
  setPrecioMax: (precio: number | null) => void;
  setCantidadMin: (cantidad: number | null) => void;
  setCantidadMax: (cantidad: number | null) => void;
  resetFilters: () => void;
  setFiltersFromUrl: (params: URLSearchParams) => void;
  getUrlParams: () => URLSearchParams;
}

const initialState = {
  fechaInicio: null,
  fechaFin: null,
  productos: [],
  vendedores: [],
  familias: [],
  metodos: [],
  proveedores: [],
  precioMin: null,
  precioMax: null,
  cantidadMin: null,
  cantidadMax: null,
};

export const useFiltersStore = create<FiltersState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      setFechaInicio: (fechaInicio) => set({ fechaInicio }),
      setFechaFin: (fechaFin) => set({ fechaFin }),
      setProductos: (productos) => set({ productos }),
      setVendedores: (vendedores) => set({ vendedores }),
      setFamilias: (familias) => set({ familias }),
      setMetodos: (metodos) => set({ metodos }),
      setProveedores: (proveedores) => set({ proveedores }),
      setPrecioMin: (precioMin) => set({ precioMin }),
      setPrecioMax: (precioMax) => set({ precioMax }),
      setCantidadMin: (cantidadMin) => set({ cantidadMin }),
      setCantidadMax: (cantidadMax) => set({ cantidadMax }),
      
      resetFilters: () => set(initialState),
      
      setFiltersFromUrl: (params) => {
        const newState: Partial<FiltersState> = {};
        
        const fechaInicio = params.get('fecha_inicio');
        if (fechaInicio) newState.fechaInicio = fechaInicio;
        
        const fechaFin = params.get('fecha_fin');
        if (fechaFin) newState.fechaFin = fechaFin;
        
        const productos = params.getAll('productos');
        if (productos.length > 0) newState.productos = productos;
        
        const vendedores = params.getAll('vendedores');
        if (vendedores.length > 0) newState.vendedores = vendedores;
        
        const familias = params.getAll('familias');
        if (familias.length > 0) newState.familias = familias;
        
        const metodos = params.getAll('metodos');
        if (metodos.length > 0) newState.metodos = metodos;
        
        const proveedores = params.getAll('proveedores');
        if (proveedores.length > 0) newState.proveedores = proveedores;
        
        const precioMin = params.get('precio_min');
        if (precioMin) newState.precioMin = parseFloat(precioMin);
        
        const precioMax = params.get('precio_max');
        if (precioMax) newState.precioMax = parseFloat(precioMax);
        
        set(newState);
      },
      
      getUrlParams: () => {
        const state = get();
        const params = new URLSearchParams();
        
        if (state.fechaInicio) params.set('fecha_inicio', state.fechaInicio);
        if (state.fechaFin) params.set('fecha_fin', state.fechaFin);
        
        state.productos.forEach((p) => params.append('productos', p));
        state.vendedores.forEach((v) => params.append('vendedores', v));
        state.familias.forEach((f) => params.append('familias', f));
        state.metodos.forEach((m) => params.append('metodos', m));
        state.proveedores.forEach((p) => params.append('proveedores', p));
        
        if (state.precioMin !== null) params.set('precio_min', state.precioMin.toString());
        if (state.precioMax !== null) params.set('precio_max', state.precioMax.toString());
        
        return params;
      },
    }),
    {
      name: 'filters-storage',
      partialize: (state) => ({
        fechaInicio: state.fechaInicio,
        fechaFin: state.fechaFin,
        productos: state.productos,
        vendedores: state.vendedores,
        familias: state.familias,
        metodos: state.metodos,
        proveedores: state.proveedores,
        precioMin: state.precioMin,
        precioMax: state.precioMax,
      }),
    }
  )
);

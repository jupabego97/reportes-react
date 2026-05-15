import { useMemo } from 'react';

/** Prioridades que disparan acción inmediata de compra */
export const PRIORIDAD_URGENCIA = new Set(['🔴 Urgente', '🟠 Alta']);

export type SugerenciaCompraRow = {
  prioridad?: string;
  dias_stock?: number;
  nombre?: string;
  proveedor?: string;
  costo_estimado?: number;
  cantidad_sugerida?: number;
};

/**
 * Filas urgentes según prioridad emoji o días de stock ≤ umbralDias.
 * Opcionalmente filtra por búsqueda en nombre/proveedor.
 */
export function useUrgenciasCompraRows(
  sugerencias: SugerenciaCompraRow[] | undefined,
  options?: { umbralDias?: number; busqueda?: string }
) {
  const umbralDias = options?.umbralDias ?? 2;
  const q = (options?.busqueda ?? '').toLowerCase().trim();

  return useMemo(() => {
    const rows = Array.isArray(sugerencias) ? sugerencias : [];
    return rows
      .filter(
        (s) =>
          PRIORIDAD_URGENCIA.has(s.prioridad || '') || (s.dias_stock ?? 999) <= umbralDias
      )
      .filter(
        (s) =>
          !q ||
          (s.nombre || '').toLowerCase().includes(q) ||
          (s.proveedor || '').toLowerCase().includes(q)
      )
      .sort((a, b) => (a.dias_stock ?? 999) - (b.dias_stock ?? 999));
  }, [sugerencias, umbralDias, q]);
}

export function useProveedoresUrgenciaAgrupados(comprarUrgente: SugerenciaCompraRow[]) {
  return useMemo(() => {
    const map = new Map<
      string,
      { proveedor: string; productos: number; unidades: number; costo: number }
    >();
    for (const s of comprarUrgente) {
      const proveedor = s.proveedor || 'Sin proveedor';
      const prev = map.get(proveedor) || {
        proveedor,
        productos: 0,
        unidades: 0,
        costo: 0,
      };
      prev.productos += 1;
      prev.unidades += Number(s.cantidad_sugerida || 0);
      prev.costo += Number(s.costo_estimado || 0);
      map.set(proveedor, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.costo - a.costo);
  }, [comprarUrgente]);
}

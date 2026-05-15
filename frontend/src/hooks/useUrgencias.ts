import { useMemo } from 'react';
import type { VariantProps } from 'class-variance-authority';
import { badgeVariants } from '../components/ui/badge';

/** Prioridades que disparan acción inmediata de compra */
export const PRIORIDAD_URGENCIA = new Set(['🔴 Urgente', '🟠 Alta']);

export const PRIORIDADES_V1 = ['🔴 Urgente', '🟠 Alta', '🟡 Media', '🟢 Baja'] as const;

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>['variant']>;

export const URGENCIA_CONFIG: Record<
  string,
  { label: string; badgeVariant: BadgeVariant }
> = {
  '🔴 Urgente': { label: 'Urgente', badgeVariant: 'destructive' },
  '🟠 Alta': { label: 'Alta', badgeVariant: 'warning' },
  '🟡 Media': { label: 'Media', badgeVariant: 'secondary' },
  '🟢 Baja': { label: 'Baja', badgeVariant: 'outline' },
};

export function useUrgenciaConfig(prioridad?: string) {
  return useMemo(() => {
    const cfg = URGENCIA_CONFIG[prioridad || ''];
    return cfg ?? { label: prioridad || '—', badgeVariant: 'outline' as BadgeVariant };
  }, [prioridad]);
}

export type SugerenciaCompraRow = {
  prioridad?: string;
  dias_stock?: number;
  nombre?: string;
  proveedor?: string;
  costo_estimado?: number;
  cantidad_sugerida?: number;
  cantidad_disponible?: number;
  precio_compra?: number;
  clasificacion_abc?: string;
  punto_reorden?: number;
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

export type ProveedorCardResumen = {
  proveedor: string;
  urgente: number;
  alta: number;
  media: number;
  baja: number;
  productos: number;
  costo: number;
};

/** Resumen por proveedor con conteos de prioridad (v1 emoji) para las cards. */
export function useProveedoresCardResumen(sugerencias: SugerenciaCompraRow[] | undefined) {
  return useMemo(() => {
    const map = new Map<string, ProveedorCardResumen>();
    for (const s of Array.isArray(sugerencias) ? sugerencias : []) {
      const proveedor = s.proveedor || 'Sin proveedor';
      const prev = map.get(proveedor) || {
        proveedor,
        urgente: 0,
        alta: 0,
        media: 0,
        baja: 0,
        productos: 0,
        costo: 0,
      };
      prev.productos += 1;
      prev.costo += Number(s.costo_estimado || 0);
      if (s.prioridad === '🔴 Urgente') prev.urgente += 1;
      else if (s.prioridad === '🟠 Alta') prev.alta += 1;
      else if (s.prioridad === '🟡 Media') prev.media += 1;
      else if (s.prioridad === '🟢 Baja') prev.baja += 1;
      map.set(proveedor, prev);
    }
    return Array.from(map.values()).sort(
      (a, b) => b.urgente * 1000 + b.alta * 100 + b.costo - (a.urgente * 1000 + a.alta * 100 + a.costo)
    );
  }, [sugerencias]);
}

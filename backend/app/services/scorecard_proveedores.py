"""
Scorecard de proveedores (Fase 3).

Mide el desempeño real de cada proveedor con las OC recibidas:
- OTIF: % de órdenes a tiempo Y completas (binaria por orden)
- Fill rate: % de unidades recibidas vs pedidas
- Lead time real vs prometido (y su variabilidad, que infla el stock
  de seguridad: un proveedor errático cuesta capital de trabajo)

Un proveedor que se deteriora se detecta aquí y se alerta en Decisiones.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class ScorecardProveedoresService:
    """Desempeño medido de proveedores a partir de las OC."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_scorecard(self, dias: int = 90) -> List[Dict[str, Any]]:
        """Scorecard por proveedor sobre las OC recibidas en la ventana.

        Una OC cuenta como "a tiempo" si fecha_recepcion <= fecha_promesa,
        y "completa" si todas sus líneas recibieron lo pedido.
        """
        query = """
            WITH oc AS (
                SELECT
                    o.proveedor_id,
                    o.id,
                    o.fecha_envio,
                    o.fecha_promesa,
                    o.fecha_recepcion,
                    (o.fecha_recepcion::date <= o.fecha_promesa) as a_tiempo,
                    BOOL_AND(l.cantidad_recibida >= l.cantidad_pedida) as completa,
                    SUM(l.cantidad_pedida) as pedidas,
                    SUM(l.cantidad_recibida) as recibidas,
                    EXTRACT(EPOCH FROM (o.fecha_recepcion - o.fecha_envio)) / 86400.0
                        as lead_time_real
                FROM ordenes_compra o
                JOIN ordenes_compra_lineas l ON l.orden_id = o.id
                WHERE o.estado IN ('recibida', 'recibida_parcial')
                  AND o.fecha_recepcion IS NOT NULL
                  AND o.fecha_promesa IS NOT NULL
                  AND o.fecha_recepcion >= CURRENT_DATE - CAST(:dias AS INTEGER)
                GROUP BY o.proveedor_id, o.id
            )
            SELECT
                p.id as proveedor_id,
                p.nombre as proveedor,
                p.lead_time_dias as lead_time_prometido,
                COUNT(oc.id) as ordenes,
                SUM(CASE WHEN oc.a_tiempo AND oc.completa THEN 1 ELSE 0 END) as otif_ok,
                SUM(oc.pedidas) as unidades_pedidas,
                SUM(oc.recibidas) as unidades_recibidas,
                AVG(oc.lead_time_real) as lead_time_real_promedio,
                STDDEV_SAMP(oc.lead_time_real) as lead_time_real_sigma
            FROM oc
            JOIN proveedores p ON p.id = oc.proveedor_id
            GROUP BY p.id, p.nombre, p.lead_time_dias
            ORDER BY COUNT(oc.id) DESC
        """
        result = await self.db.execute(text(query), {"dias": dias})
        scorecard = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            ordenes = int(fila["ordenes"] or 0)
            otif_ok = int(fila["otif_ok"] or 0)
            fila["otif_pct"] = semantica.otif_pct(otif_ok, ordenes)
            fila["fill_rate_pct"] = semantica.fill_rate_pct(
                float(fila["unidades_recibidas"] or 0),
                float(fila["unidades_pedidas"] or 0),
            )
            for k in ("unidades_pedidas", "unidades_recibidas",
                      "lead_time_real_promedio", "lead_time_real_sigma"):
                fila[k] = round(float(fila[k]), 2) if fila[k] is not None else None
            if fila["otif_pct"] is not None:
                fila["otif_pct"] = round(fila["otif_pct"], 1)
            if fila["fill_rate_pct"] is not None:
                fila["fill_rate_pct"] = round(fila["fill_rate_pct"], 1)
            fila["cumple_objetivo"] = (
                fila["otif_pct"] is not None
                and fila["otif_pct"] >= semantica.OTIF_OBJETIVO_PCT
            )
            scorecard.append(fila)
        return scorecard

    async def get_deteriorados(self) -> List[Dict[str, Any]]:
        """Proveedores cuyo OTIF reciente (30d) cayó vs su histórico (90d).

        Insumo del detector de decisiones: deterioro > OTIF_CAIDA_ALERTA_PTS
        con al menos 3 órdenes recientes para no alertar por ruido.
        """
        reciente = {s["proveedor_id"]: s for s in await self.get_scorecard(dias=30)}
        historico = {s["proveedor_id"]: s for s in await self.get_scorecard(dias=90)}

        deteriorados = []
        for pid, r in reciente.items():
            h = historico.get(pid)
            if not h or r["otif_pct"] is None or h["otif_pct"] is None:
                continue
            if int(r["ordenes"] or 0) < 3:
                continue
            caida = h["otif_pct"] - r["otif_pct"]
            if caida > semantica.OTIF_CAIDA_ALERTA_PTS:
                deteriorados.append(
                    {
                        "proveedor_id": pid,
                        "proveedor": r["proveedor"],
                        "otif_reciente": r["otif_pct"],
                        "otif_historico": h["otif_pct"],
                        "caida_pts": round(caida, 1),
                        "ordenes_recientes": int(r["ordenes"] or 0),
                    }
                )
        deteriorados.sort(key=lambda d: d["caida_pts"], reverse=True)
        return deteriorados

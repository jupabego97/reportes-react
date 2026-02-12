"""
Servicio de facturas de proveedor - Vencimientos y recordatorios.
Calcula fecha_vencimiento = fecha + dias_plazo (default 30).
"""
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class FacturasProveedorService:
    """Servicio para gestionar facturas de proveedor y vencimientos."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_facturas(
        self,
        proveedor: Optional[str] = None,
        dias_plazo: int = 30,
        estado: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene facturas con estado de vencimiento.
        Agrupa por proveedor + fecha (una factura por dia por proveedor).
        estado: None (todas), 'vencida', 'proxima', 'vigente', 'vence_hoy'
        """
        # Query para obtener facturas unicas por (proveedor, fecha)
        query = """
            SELECT 
                proveedor,
                fecha,
                MAX(total_fact) as monto,
                COUNT(*) as lineas
            FROM facturas_proveedor
            WHERE 1=1
        """
        params: Dict[str, Any] = {}
        if proveedor:
            query += " AND LOWER(TRIM(proveedor)) LIKE LOWER(:proveedor)"
            params["proveedor"] = f"%{proveedor.strip()}%"

        query += " GROUP BY proveedor, fecha ORDER BY fecha DESC, proveedor"
        try:
            result = await self.db.execute(text(query), params)
        except Exception:
            # Si la tabla no existe o tiene otro esquema, devolver lista vacia
            return []

        rows = result.fetchall()
        hoy = date.today()
        facturas = []

        for row in rows:
            row_dict = row._asdict()
            fecha_fact = row_dict["fecha"]
            if hasattr(fecha_fact, "date"):
                fecha_fact = fecha_fact.date()
            elif isinstance(fecha_fact, str):
                fecha_fact = date.fromisoformat(fecha_fact[:10])

            fecha_venc = fecha_fact + timedelta(days=dias_plazo)
            dias_restantes = (fecha_venc - hoy).days

            if dias_restantes < 0:
                est = "vencida"
            elif dias_restantes == 0:
                est = "vence_hoy"
            elif dias_restantes <= 7:
                est = "proxima"
            else:
                est = "vigente"

            if estado and estado in ("vencida", "vence_hoy", "proxima", "vigente") and est != estado:
                continue

            facturas.append({
                "proveedor": row_dict["proveedor"],
                "fecha_factura": str(fecha_fact),
                "fecha_vencimiento": str(fecha_venc),
                "dias_restantes": dias_restantes,
                "monto": float(row_dict["monto"] or 0),
                "lineas": int(row_dict["lineas"] or 0),
                "estado": est,
            })

        return facturas

    async def get_resumen(
        self,
        proveedor: Optional[str] = None,
        dias_plazo: int = 30,
    ) -> Dict[str, Any]:
        """Resumen por proveedor: total facturas, monto, vencidas, proximas."""
        facturas = await self.get_facturas(proveedor=proveedor, dias_plazo=dias_plazo)

        total_facturas = len(facturas)
        monto_total = sum(f["monto"] for f in facturas)
        vencidas = [f for f in facturas if f["estado"] == "vencida"]
        vence_hoy = [f for f in facturas if f["estado"] == "vence_hoy"]
        proximas = [f for f in facturas if f["estado"] == "proxima"]
        vigentes = [f for f in facturas if f["estado"] == "vigente"]

        monto_vencido = sum(f["monto"] for f in vencidas)
        monto_vence_hoy = sum(f["monto"] for f in vence_hoy)
        monto_proximo = sum(f["monto"] for f in proximas)

        # Resumen por proveedor
        por_proveedor: Dict[str, Dict[str, Any]] = {}
        for f in facturas:
            p = f["proveedor"]
            if p not in por_proveedor:
                por_proveedor[p] = {
                    "proveedor": p,
                    "total_facturas": 0,
                    "monto_total": 0,
                    "facturas_vencidas": 0,
                    "monto_vencido": 0,
                    "facturas_proximas": 0,
                    "monto_proximo": 0,
                }
            por_proveedor[p]["total_facturas"] += 1
            por_proveedor[p]["monto_total"] += f["monto"]
            if f["estado"] == "vencida":
                por_proveedor[p]["facturas_vencidas"] += 1
                por_proveedor[p]["monto_vencido"] += f["monto"]
            elif f["estado"] in ("proxima", "vence_hoy"):
                por_proveedor[p]["facturas_proximas"] += 1
                por_proveedor[p]["monto_proximo"] += f["monto"] if f["estado"] == "proxima" else 0
                if f["estado"] == "vence_hoy":
                    por_proveedor[p]["monto_proximo"] += f["monto"]

        return {
            "total_facturas": total_facturas,
            "monto_total": round(monto_total, 2),
            "facturas_vencidas": len(vencidas),
            "monto_vencido": round(monto_vencido, 2),
            "facturas_vence_hoy": len(vence_hoy),
            "monto_vence_hoy": round(monto_vence_hoy, 2),
            "facturas_proximas": len(proximas),
            "monto_proximo": round(monto_proximo, 2),
            "por_proveedor": list(por_proveedor.values()),
        }

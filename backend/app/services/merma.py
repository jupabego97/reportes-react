"""
Servicio de merma por causa (Fase 3).

La merma no es un número global: cada causa tiene dueño y tratamiento.
- vencimiento → comprador (compró de más) o gerente (no rotó FEFO)
- dano → gerente de tienda (manipulación/almacenaje)
- robo_externo → gerente de tienda (seguridad de piso)
- robo_interno → finanzas/auditoría
- error_administrativo → finanzas (proceso, no pérdida física real)

Registrar merma descuenta inventario (movimiento 'merma' en el libro
perpetuo) y alimenta el reporte valorizado que dispara alertas.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class MermaService:
    """Registro y análisis de merma clasificada por causa."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar(
        self,
        nombre_producto: str,
        causa: str,
        cantidad: float,
        nota: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra una merma y descuenta el inventario perpetuo."""
        if causa not in semantica.CAUSAS_MERMA:
            raise ValueError(
                f"Causa inválida: {causa}. Válidas: {', '.join(sorted(semantica.CAUSAS_MERMA))}"
            )
        if cantidad <= 0:
            raise ValueError("La cantidad de merma debe ser positiva")

        result = await self.db.execute(
            text("SELECT id, costo_unitario FROM productos WHERE nombre = :n"),
            {"n": semantica.normalizar_nombre(nombre_producto)},
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"Producto no encontrado en el maestro: {nombre_producto}")
        producto_id = int(row[0])
        costo = float(row[1]) if row[1] is not None else None
        valor = round(cantidad * costo, 2) if costo is not None else None

        tienda = await self.db.execute(
            text("SELECT id FROM tiendas WHERE activa ORDER BY id LIMIT 1")
        )
        tienda_id = int(tienda.fetchone()[0])

        await self.db.execute(
            text(
                """
                INSERT INTO mermas
                    (producto_id, tienda_id, causa, cantidad, costo_unitario, valor, nota, usuario)
                VALUES (:producto, :tienda, :causa, :cantidad, :costo, :valor, :nota, :usuario)
                """
            ),
            {
                "producto": producto_id,
                "tienda": tienda_id,
                "causa": causa,
                "cantidad": cantidad,
                "costo": costo,
                "valor": valor,
                "nota": nota,
                "usuario": usuario,
            },
        )
        # El libro perpetuo registra la salida (cantidad negativa)
        await self.db.execute(
            text(
                """
                INSERT INTO movimientos_inventario
                    (producto_id, tienda_id, tipo, cantidad, costo_unitario, referencia, usuario)
                VALUES (:producto, :tienda, 'merma', :cantidad, :costo, :referencia, :usuario)
                """
            ),
            {
                "producto": producto_id,
                "tienda": tienda_id,
                "cantidad": -cantidad,
                "costo": costo,
                "referencia": f"merma:{causa}",
                "usuario": usuario,
            },
        )
        await self.db.commit()
        return {
            "producto_id": producto_id,
            "causa": causa,
            "cantidad": cantidad,
            "valor": valor,
        }

    async def get_reporte(self, dias: int = 30) -> Dict[str, Any]:
        """Merma valorizada del período: total, % sobre venta y por causa.

        El % sobre venta es la métrica comparable (objetivo < 1%); el
        desglose por causa dice a quién le toca actuar.
        """
        result = await self.db.execute(
            text(
                """
                SELECT causa,
                       COUNT(*) as eventos,
                       SUM(cantidad) as unidades,
                       SUM(valor) as valor
                FROM mermas
                WHERE fecha >= CURRENT_DATE - CAST(:dias AS INTEGER)
                GROUP BY causa
                ORDER BY SUM(valor) DESC NULLS LAST
                """
            ),
            {"dias": dias},
        )
        por_causa = []
        total_valor = 0.0
        for r in result.fetchall():
            valor = float(r[3]) if r[3] is not None else 0.0
            total_valor += valor
            por_causa.append(
                {
                    "causa": r[0],
                    "eventos": int(r[1]),
                    "unidades": float(r[2] or 0),
                    "valor": round(valor, 2),
                }
            )

        venta = await self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(venta_neta), 0)
                FROM ventas_diarias_historicas
                WHERE fecha >= CURRENT_DATE - CAST(:dias AS INTEGER)
                """
            ),
            {"dias": dias},
        )
        venta_periodo = float(venta.scalar() or 0)
        merma_pct = semantica.merma_pct_sobre_venta(total_valor, venta_periodo)

        # Top productos con más merma (dónde concentrar la acción)
        result = await self.db.execute(
            text(
                """
                SELECT p.nombre, m.causa, SUM(m.cantidad) as unidades, SUM(m.valor) as valor
                FROM mermas m
                JOIN productos p ON p.id = m.producto_id
                WHERE m.fecha >= CURRENT_DATE - CAST(:dias AS INTEGER)
                GROUP BY p.nombre, m.causa
                ORDER BY SUM(m.valor) DESC NULLS LAST
                LIMIT 15
                """
            ),
            {"dias": dias},
        )
        top_productos = [
            {
                "nombre": r[0],
                "causa": r[1],
                "unidades": float(r[2] or 0),
                "valor": round(float(r[3]), 2) if r[3] is not None else None,
            }
            for r in result.fetchall()
        ]

        return {
            "dias": dias,
            "merma_total_valor": round(total_valor, 2),
            "venta_periodo": round(venta_periodo, 2),
            "merma_pct_sobre_venta": round(merma_pct, 3) if merma_pct is not None else None,
            "objetivo_pct": semantica.MERMA_PCT_ALERTA,
            "por_causa": por_causa,
            "top_productos": top_productos,
        }

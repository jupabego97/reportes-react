"""
Servicio de autonomía Nivel 1 (Fase 5).

Auto-ejecuta acciones de bajo riesgo según políticas:
- Aprobar OC en borrador bajo umbral de costo
- Resolver decisiones Nivel 1 con nota auto:nivel1

Nunca auto-ejecuta códigos prohibidos (P1 críticos, quiebres, etc.).
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class AutonomiaService:
    """Políticas y auto-ejecución Nivel 1."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_politicas(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT id, codigo, descripcion, auto_max_impacto, habilitado, updated_at
                FROM politicas_autonomia
                ORDER BY codigo
                """
            )
        )
        filas = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            fila["auto_max_impacto"] = (
                float(fila["auto_max_impacto"]) if fila["auto_max_impacto"] is not None else 0.0
            )
            fila["updated_at"] = str(fila["updated_at"]) if fila["updated_at"] else None
            filas.append(fila)
        return filas

    async def actualizar_politica(
        self,
        codigo: str,
        auto_max_impacto: Optional[float] = None,
        habilitado: Optional[bool] = None,
    ) -> Dict[str, Any]:
        sets = ["updated_at = NOW()"]
        params: Dict[str, Any] = {"codigo": codigo}
        if auto_max_impacto is not None:
            sets.append("auto_max_impacto = :max")
            params["max"] = auto_max_impacto
        if habilitado is not None:
            sets.append("habilitado = :hab")
            params["hab"] = habilitado
        result = await self.db.execute(
            text(
                f"""
                UPDATE politicas_autonomia SET {', '.join(sets)}
                WHERE codigo = :codigo
                RETURNING id, codigo, descripcion, auto_max_impacto, habilitado
                """
            ),
            params,
        )
        row = result.fetchone()
        await self.db.commit()
        if not row:
            raise ValueError(f"Política no encontrada: {codigo}")
        return {
            "id": row[0],
            "codigo": row[1],
            "descripcion": row[2],
            "auto_max_impacto": float(row[3] or 0),
            "habilitado": bool(row[4]),
        }

    async def _politica(self, codigo: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT codigo, auto_max_impacto, habilitado
                FROM politicas_autonomia WHERE codigo = :c
                """
            ),
            {"c": codigo},
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "codigo": row[0],
            "auto_max_impacto": float(row[1] or 0),
            "habilitado": bool(row[2]),
        }

    async def ejecutar_nivel1(self) -> Dict[str, Any]:
        """Auto-aprueba OC y resuelve decisiones bajo umbral."""
        oc_aprobadas = await self._auto_aprobar_oc()
        decisiones_resueltas = await self._auto_resolver_decisiones()
        return {
            "oc_aprobadas": oc_aprobadas,
            "decisiones_resueltas": decisiones_resueltas,
        }

    async def _auto_aprobar_oc(self) -> int:
        pol = await self._politica("oc_borrador")
        if not pol or not pol["habilitado"]:
            return 0
        umbral = pol["auto_max_impacto"]
        result = await self.db.execute(
            text(
                """
                SELECT id, total_costo FROM ordenes_compra
                WHERE estado = 'borrador'
                  AND COALESCE(total_costo, 0) <= :umbral
                """
            ),
            {"umbral": umbral},
        )
        filas = result.fetchall()
        count = 0
        for f in filas:
            nivel = semantica.nivel_autonomia(
                "oc_borrador",
                float(f[1] or 0),
                auto_max_impacto=umbral,
                habilitado=True,
            )
            if nivel != 1:
                continue
            await self.db.execute(
                text(
                    """
                    UPDATE ordenes_compra
                    SET estado = 'aprobada', usuario_aprobo = 'auto:nivel1',
                        fecha_aprobacion = NOW()
                    WHERE id = :id AND estado = 'borrador'
                    """
                ),
                {"id": int(f[0])},
            )
            count += 1
        if count:
            await self.db.commit()
        return count

    async def _auto_resolver_decisiones(self) -> int:
        result = await self.db.execute(
            text(
                """
                SELECT id, codigo_alerta, impacto_dinero, prioridad
                FROM decisiones WHERE estado = 'pendiente'
                """
            )
        )
        pendientes = result.fetchall()
        count = 0
        for d in pendientes:
            codigo = d[1]
            impacto = float(d[2]) if d[2] is not None else 0.0
            if codigo in semantica.AUTONOMIA_PROHIBIDOS:
                continue
            pol = await self._politica(codigo)
            if not pol:
                continue
            nivel = semantica.nivel_autonomia(
                codigo,
                impacto,
                auto_max_impacto=pol["auto_max_impacto"],
                habilitado=pol["habilitado"],
            )
            if nivel != 1:
                continue

            from app.services.decisiones import DecisionesService

            try:
                await DecisionesService(self.db).resolver(
                    decision_id=int(d[0]),
                    estado="resuelta",
                    usuario="auto:nivel1",
                    nota="auto:nivel1 — ejecutado bajo umbral de política",
                )
                count += 1
            except ValueError:
                continue
        return count

"""
Motor de decisiones (Fase 1) — la bandeja que reemplaza a los dashboards.

Formato obligatorio de toda alerta (regla del Retail Intelligence OS):
    QUÉ pasa + POR QUÉ (causa probable) + QUÉ HACER (acción concreta)
    + CUÁNTO vale (impacto en dinero) + DUEÑO + SLA.

Alertas sin acción no existen. Cada decisión registra su resolución para
el circuito de aprendizaje (¿se aceptó? ¿sirvió?).
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica

# SLA por prioridad (horas hasta vencer)
SLA_HORAS = {"P1": 4, "P2": 24, "P3": 168, "P4": 720}

ESTADOS_VALIDOS = {"pendiente", "aprobada", "rechazada", "resuelta", "expirada"}


class DecisionesService:
    """Evalúa detectores, deduplica y administra la bandeja de decisiones."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------ persistencia

    async def _emitir(
        self,
        codigo_alerta: str,
        prioridad: str,
        titulo: str,
        que_pasa: str,
        por_que: str,
        que_hacer: str,
        dueno: str,
        clave_dedup: str,
        impacto_dinero: Optional[float] = None,
        datos: Optional[Any] = None,
    ) -> bool:
        """Inserta la decisión si no existe otra pendiente con la misma clave."""
        existe = await self.db.execute(
            text(
                """
                SELECT 1 FROM decisiones
                WHERE clave_dedup = :clave AND estado = 'pendiente'
                LIMIT 1
                """
            ),
            {"clave": clave_dedup},
        )
        if existe.fetchone():
            return False

        vence_en = datetime.now(timezone.utc) + timedelta(hours=SLA_HORAS.get(prioridad, 168))
        await self.db.execute(
            text(
                """
                INSERT INTO decisiones
                    (codigo_alerta, prioridad, titulo, que_pasa, por_que, que_hacer,
                     impacto_dinero, dueno, vence_en, datos, clave_dedup)
                VALUES
                    (:codigo, :prioridad, :titulo, :que_pasa, :por_que, :que_hacer,
                     :impacto, :dueno, :vence, CAST(:datos AS JSON), :clave)
                """
            ),
            {
                "codigo": codigo_alerta,
                "prioridad": prioridad,
                "titulo": titulo,
                "que_pasa": que_pasa,
                "por_que": por_que,
                "que_hacer": que_hacer,
                "impacto": round(impacto_dinero, 2) if impacto_dinero is not None else None,
                "dueno": dueno,
                "vence": vence_en,
                "datos": json.dumps(datos, default=str) if datos is not None else None,
                "clave": clave_dedup,
            },
        )
        return True

    # -------------------------------------------------------------- detectores

    async def _detectar_margen_negativo(self) -> int:
        """P1 · pricing — productos vendiéndose bajo su costo (últimos 7 días)."""
        query = """
            SELECT
                nombre,
                AVG(precio) as precio_promedio,
                AVG(precio_promedio_compra) as costo_promedio,
                SUM(cantidad) as unidades,
                SUM((precio - precio_promedio_compra) * cantidad) as perdida_total
            FROM reportes_ventas_30dias
            WHERE precio_promedio_compra IS NOT NULL
              AND precio < precio_promedio_compra
              AND fecha_venta >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY nombre
            ORDER BY perdida_total ASC
        """
        result = await self.db.execute(text(query))
        filas = [dict(r._asdict()) for r in result.fetchall()]
        if not filas:
            return 0

        perdida = abs(sum(float(f["perdida_total"] or 0) for f in filas))
        emitida = await self._emitir(
            codigo_alerta="margen_negativo",
            prioridad="P1",
            titulo=f"{len(filas)} productos vendiéndose bajo costo esta semana",
            que_pasa=(
                f"En los últimos 7 días, {len(filas)} productos se vendieron por debajo de su "
                f"costo promedio de compra, con una pérdida acumulada de ${perdida:,.0f}."
            ),
            por_que=(
                "Causas probables: costo desactualizado tras alza del proveedor, precio mal "
                "digitado, o promoción sin piso de margen. Verificar primero el costo (la causa "
                "más frecuente) antes de tocar el precio."
            ),
            que_hacer=(
                "Para cada producto del detalle: 1) validar el costo contra la última factura "
                "del proveedor; 2) si el costo es correcto, corregir el precio de venta hoy; "
                "3) si hay promoción activa, suspenderla hasta definir piso."
            ),
            dueno="pricing",
            impacto_dinero=perdida,
            clave_dedup=f"margen_negativo:{datetime.now(timezone.utc):%Y-%W}",
            datos=[
                {
                    "nombre": f["nombre"],
                    "precio_promedio": round(float(f["precio_promedio"] or 0), 2),
                    "costo_promedio": round(float(f["costo_promedio"] or 0), 2),
                    "unidades": int(f["unidades"] or 0),
                    "perdida": round(float(f["perdida_total"] or 0), 2),
                }
                for f in filas[:20]
            ],
        )
        return 1 if emitida else 0

    async def _detectar_quiebre_inminente(self) -> int:
        """P2 · comprador — productos con venta activa que quebrarán en <7 días.

        Impacto = margen perdido proyectado (velocidad × días descubiertos ×
        margen real), usando la definición canónica de la capa semántica.
        """
        query = """
            WITH ventas AS (
                SELECT
                    nombre,
                    SUM(cantidad) as unidades_30d,
                    AVG(precio) as precio_promedio,
                    AVG(precio_promedio_compra) as costo_promedio,
                    MAX(proveedor_moda) as proveedor
                FROM reportes_ventas_30dias
                WHERE fecha_venta >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY nombre
                HAVING SUM(cantidad) > 0
            )
            SELECT
                v.nombre,
                v.unidades_30d,
                v.precio_promedio,
                v.costo_promedio,
                v.proveedor,
                COALESCE(i.cantidad_disponible, 0) as stock_actual
            FROM ventas v
            LEFT JOIN items i ON UPPER(TRIM(i.nombre)) = UPPER(TRIM(v.nombre))
        """
        result = await self.db.execute(text(query))
        filas = [dict(r._asdict()) for r in result.fetchall()]

        en_riesgo = []
        margen_en_riesgo_total = 0.0
        for f in filas:
            vd = semantica.venta_diaria(float(f["unidades_30d"] or 0), 30)
            cobertura = semantica.dias_cobertura(float(f["stock_actual"] or 0), vd)
            if cobertura is None or cobertura > semantica.DIAS_STOCK_MINIMO:
                continue
            # Días que quedarían descubiertos si se repone con lead time default
            dias_descubiertos = max(semantica.LEAD_TIME_DEFAULT - cobertura, 0)
            costo = float(f["costo_promedio"]) if f["costo_promedio"] is not None else None
            mp = semantica.margen_perdido(
                vd, dias_descubiertos, float(f["precio_promedio"] or 0), costo
            )
            vp = semantica.venta_perdida(vd, dias_descubiertos, float(f["precio_promedio"] or 0))
            en_riesgo.append(
                {
                    "nombre": f["nombre"],
                    "proveedor": f["proveedor"],
                    "stock_actual": float(f["stock_actual"] or 0),
                    "dias_cobertura": round(cobertura, 1),
                    "venta_diaria": round(vd, 2),
                    "venta_perdida_proyectada": round(vp, 2),
                    "margen_perdido_proyectado": round(mp, 2) if mp is not None else None,
                }
            )
            margen_en_riesgo_total += mp if mp is not None else vp * 0.0

        if not en_riesgo:
            return 0

        en_riesgo.sort(key=lambda x: x["venta_perdida_proyectada"], reverse=True)
        venta_perdida_total = sum(x["venta_perdida_proyectada"] for x in en_riesgo)

        emitida = await self._emitir(
            codigo_alerta="quiebre_inminente",
            prioridad="P2",
            titulo=f"{len(en_riesgo)} productos con venta activa quebrarán en menos de 7 días",
            que_pasa=(
                f"{len(en_riesgo)} productos tienen cobertura por debajo de "
                f"{semantica.DIAS_STOCK_MINIMO} días a su velocidad de venta actual. "
                f"Si no se repone hoy, la venta perdida proyectada es ${venta_perdida_total:,.0f}."
            ),
            por_que=(
                "La cobertura cayó bajo el lead time de reposición (7 días por defecto): "
                "aunque se ordene hoy, habrá días descubiertos. Causas típicas: venta mayor "
                "a la esperada, pedido anterior corto, o retraso del proveedor."
            ),
            que_hacer=(
                "Generar hoy la orden de compra para los productos del detalle, empezando por "
                "los de mayor venta perdida proyectada. Si el proveedor no puede entregar a "
                "tiempo, evaluar proveedor alterno del comparativo de compras."
            ),
            dueno="comprador",
            impacto_dinero=margen_en_riesgo_total if margen_en_riesgo_total > 0 else venta_perdida_total,
            clave_dedup=f"quiebre_inminente:{datetime.now(timezone.utc):%Y-%m-%d}",
            datos=en_riesgo[:25],
        )
        return 1 if emitida else 0

    async def _detectar_inventario_muerto(self) -> int:
        """P3 · comprador — capital atrapado en stock sin venta en 30 días."""
        query = """
            SELECT
                UPPER(TRIM(i.nombre)) as nombre,
                COALESCE(i.cantidad_disponible, 0) as stock,
                p.costo_unitario
            FROM items i
            LEFT JOIN productos p ON p.nombre = UPPER(TRIM(i.nombre))
            WHERE COALESCE(i.cantidad_disponible, 0) > 0
              AND NOT EXISTS (
                  SELECT 1 FROM reportes_ventas_30dias v
                  WHERE UPPER(TRIM(v.nombre)) = UPPER(TRIM(i.nombre))
                    AND v.fecha_venta >= CURRENT_DATE - INTERVAL '30 days'
              )
        """
        result = await self.db.execute(text(query))
        filas = [dict(r._asdict()) for r in result.fetchall()]
        if not filas:
            return 0

        detalle = []
        capital_total = 0.0
        for f in filas:
            costo = float(f["costo_unitario"]) if f["costo_unitario"] is not None else None
            valor = semantica.valor_inventario_costo(float(f["stock"] or 0), costo)
            if valor:
                capital_total += valor
            detalle.append(
                {"nombre": f["nombre"], "stock": float(f["stock"] or 0), "valor_costo": valor}
            )

        detalle.sort(key=lambda x: x["valor_costo"] or 0, reverse=True)

        emitida = await self._emitir(
            codigo_alerta="inventario_muerto",
            prioridad="P3",
            titulo=f"{len(detalle)} productos sin una sola venta en 30 días",
            que_pasa=(
                f"Hay {len(detalle)} productos con stock y cero ventas en 30 días. "
                f"Capital atrapado (al costo): ${capital_total:,.0f}."
            ),
            por_que=(
                "Causas probables por orden de frecuencia: producto no exhibido o mal ubicado, "
                "precio fuera de mercado, producto obsoleto/de temporada pasada, o quiebre "
                "fantasma (el sistema dice que hay stock pero físicamente no está)."
            ),
            que_hacer=(
                "Para el top del detalle: 1) verificar exhibición física (conteo dirigido); "
                "2) si está exhibido, aplicar rebaja de salida escalonada; 3) si lleva más de "
                "90 días, negociar devolución al proveedor o liquidar. No recomprar ninguno."
            ),
            dueno="comprador",
            impacto_dinero=capital_total,
            clave_dedup=f"inventario_muerto:{datetime.now(timezone.utc):%Y-%W}",
            datos=detalle[:25],
        )
        return 1 if emitida else 0

    async def _detectar_quiebre_fantasma(self) -> int:
        """P2 · gerente_tienda — stock en sistema pero la venta se apagó.

        Proxy Fase 1: vendía de forma consistente en la primera quincena del
        período y lleva 7+ días en cero con stock disponible.
        """
        query = """
            WITH ventana AS (
                SELECT
                    nombre,
                    SUM(CASE WHEN fecha_venta < CURRENT_DATE - INTERVAL '7 days'
                             THEN cantidad ELSE 0 END) as unidades_previas,
                    SUM(CASE WHEN fecha_venta >= CURRENT_DATE - INTERVAL '7 days'
                             THEN cantidad ELSE 0 END) as unidades_ult_7d,
                    AVG(precio) as precio_promedio,
                    AVG(precio_promedio_compra) as costo_promedio
                FROM reportes_ventas_30dias
                WHERE fecha_venta >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY nombre
            )
            SELECT
                v.nombre,
                v.unidades_previas,
                v.precio_promedio,
                v.costo_promedio,
                COALESCE(i.cantidad_disponible, 0) as stock_actual
            FROM ventana v
            JOIN items i ON UPPER(TRIM(i.nombre)) = UPPER(TRIM(v.nombre))
            WHERE v.unidades_ult_7d = 0
              AND v.unidades_previas >= 5
              AND COALESCE(i.cantidad_disponible, 0) > 0
        """
        result = await self.db.execute(text(query))
        filas = [dict(r._asdict()) for r in result.fetchall()]
        if not filas:
            return 0

        detalle = []
        venta_en_riesgo = 0.0
        for f in filas:
            vd_previa = semantica.venta_diaria(float(f["unidades_previas"] or 0), 23)
            vp = semantica.venta_perdida(vd_previa, 7, float(f["precio_promedio"] or 0))
            venta_en_riesgo += vp
            detalle.append(
                {
                    "nombre": f["nombre"],
                    "stock_sistema": float(f["stock_actual"] or 0),
                    "venta_diaria_previa": round(vd_previa, 2),
                    "venta_perdida_7d": round(vp, 2),
                }
            )
        detalle.sort(key=lambda x: x["venta_perdida_7d"], reverse=True)

        emitida = await self._emitir(
            codigo_alerta="quiebre_fantasma",
            prioridad="P2",
            titulo=f"{len(detalle)} posibles quiebres fantasma: hay stock en sistema pero no venden",
            que_pasa=(
                f"{len(detalle)} productos que vendían de forma consistente llevan 7+ días sin "
                f"una sola venta, aunque el sistema muestra stock disponible. Venta en riesgo: "
                f"${venta_en_riesgo:,.0f} por semana."
            ),
            por_que=(
                "Cuando hay stock en sistema pero la venta se apaga de golpe, la causa más "
                "probable es que el producto NO está físicamente disponible: error de "
                "inventario, producto en bodega sin exhibir, dañado, o mal ubicado."
            ),
            que_hacer=(
                "Conteo dirigido HOY de los productos del detalle: verificar existencia física "
                "y exhibición. Registrar el conteo en el sistema para ajustar el libro y medir "
                "exactitud. Si el stock real es cero, generar orden de compra inmediata."
            ),
            dueno="gerente_tienda",
            impacto_dinero=venta_en_riesgo,
            clave_dedup=f"quiebre_fantasma:{datetime.now(timezone.utc):%Y-%W}",
            datos=detalle[:25],
        )
        return 1 if emitida else 0

    async def _detectar_facturas_por_vencer(self) -> int:
        """P2 · finanzas — facturas de proveedor que vencen en 7 días o menos."""
        query = """
            SELECT
                proveedor,
                fecha,
                MAX(total_fact) as monto
            FROM facturas_proveedor
            GROUP BY proveedor, fecha
        """
        try:
            result = await self.db.execute(text(query))
        except Exception:
            await self.db.rollback()
            return 0
        filas = [dict(r._asdict()) for r in result.fetchall()]

        hoy = datetime.now(timezone.utc).date()
        por_vencer = []
        total = 0.0
        for f in filas:
            fecha_fact = f["fecha"]
            if hasattr(fecha_fact, "date"):
                fecha_fact = fecha_fact.date()
            vence = fecha_fact + timedelta(days=semantica.DIAS_PLAZO_PAGO_DEFAULT)
            dias_restantes = (vence - hoy).days
            if 0 <= dias_restantes <= 7:
                monto = float(f["monto"] or 0)
                total += monto
                por_vencer.append(
                    {
                        "proveedor": f["proveedor"],
                        "fecha_factura": str(fecha_fact),
                        "vence": str(vence),
                        "dias_restantes": dias_restantes,
                        "monto": monto,
                    }
                )

        if not por_vencer:
            return 0
        por_vencer.sort(key=lambda x: x["dias_restantes"])

        emitida = await self._emitir(
            codigo_alerta="facturas_por_vencer",
            prioridad="P2",
            titulo=f"{len(por_vencer)} facturas de proveedor vencen en los próximos 7 días",
            que_pasa=(
                f"Compromisos de pago por ${total:,.0f} vencen esta semana "
                f"({len(por_vencer)} facturas)."
            ),
            por_que=(
                f"Vencimiento calculado con el plazo estándar de "
                f"{semantica.DIAS_PLAZO_PAGO_DEFAULT} días desde la fecha de factura."
            ),
            que_hacer=(
                "Programar los pagos en orden de vencimiento. Si la caja no alcanza, "
                "negociar extensión ANTES del vencimiento (pagar tarde sin avisar deteriora "
                "las condiciones futuras del proveedor)."
            ),
            dueno="finanzas",
            impacto_dinero=total,
            clave_dedup=f"facturas_por_vencer:{hoy:%Y-%W}",
            datos=por_vencer[:25],
        )
        return 1 if emitida else 0

    async def _detectar_exactitud_baja(self) -> int:
        """P4 · gerente_tienda — la exactitud de inventario impide automatizar."""
        try:
            from app.services.inventario_perpetuo import InventarioPerpetuoService

            exactitud = await InventarioPerpetuoService(self.db).get_exactitud(dias=30)
        except Exception:
            await self.db.rollback()
            return 0

        pct = exactitud.get("exactitud_pct")
        if pct is None or pct >= 95.0 or exactitud.get("conteos_totales", 0) < 10:
            return 0

        emitida = await self._emitir(
            codigo_alerta="exactitud_inventario_baja",
            prioridad="P4",
            titulo=f"Exactitud de inventario en {pct}%: bajo el mínimo para automatizar (95%)",
            que_pasa=(
                f"De {exactitud['conteos_totales']} conteos en 30 días, solo "
                f"{exactitud['conteos_exactos']} coincidieron con el sistema ({pct}%). "
                f"Discrepancia valorizada: ${exactitud['valor_discrepancia_absoluta']:,.0f}."
            ),
            por_que=(
                "Discrepancias sistemáticas indican procesos rotos: recepciones sin registrar, "
                "ventas sin descargar stock, merma no reportada, o robo. Mientras el libro no "
                "sea confiable, toda decisión automática de compra hereda el error."
            ),
            que_hacer=(
                "Aumentar frecuencia de conteos dirigidos (usar el plan priorizado por riesgo), "
                "auditar el proceso de recepción de mercancía esta semana, y clasificar la "
                "causa de cada discrepancia grande (proceso vs. merma vs. robo)."
            ),
            dueno="gerente_tienda",
            impacto_dinero=float(exactitud.get("valor_discrepancia_absoluta") or 0),
            clave_dedup=f"exactitud_baja:{datetime.now(timezone.utc):%Y-%m}",
            datos=exactitud,
        )
        return 1 if emitida else 0

    async def _detectar_forecast_degradado(self) -> int:
        """P4 · admin — el forecast pierde contra el baseline o su error explotó.

        Regla de gobernanza (Fase 2): nunca decidir con un modelo
        silenciosamente roto.
        """
        try:
            from app.services.forecast import ForecastService

            backtest = await ForecastService(self.db).get_ultimo_backtest()
        except Exception:
            await self.db.rollback()
            return 0
        if not backtest:
            return 0

        wc = backtest.get("wmape_champion")
        wb = backtest.get("wmape_baseline")
        if wc is None:
            return 0
        pierde_contra_baseline = wb is not None and wc > wb
        error_alto = wc > 0.6
        if not pierde_contra_baseline and not error_alto:
            return 0

        motivo = (
            f"pierde contra el baseline ingenuo (WMAPE {wc:.0%} vs {wb:.0%})"
            if pierde_contra_baseline
            else f"su error es demasiado alto (WMAPE {wc:.0%})"
        )
        emitida = await self._emitir(
            codigo_alerta="forecast_degradado",
            prioridad="P4",
            titulo="El modelo de forecast está degradado: no usarlo para comprar",
            que_pasa=(
                f"En el último backtest ({backtest['productos_evaluados']} productos, "
                f"{backtest['dias_holdout']} días de holdout) el modelo champion {motivo}."
            ),
            por_que=(
                "Causas típicas: cambio de patrón de demanda (promociones, estacionalidad "
                "nueva), historia contaminada por quiebres largos, o datos sin consolidar. "
                "Un modelo que no le gana al promedio simple no aporta y puede dañar."
            ),
            que_hacer=(
                "Mientras se corrige, usar el baseline (promedio por día de semana) para "
                "reabastecimiento. Revisar la consolidación del historial y volver a correr "
                "el backtest tras acumular más días de historia."
            ),
            dueno="admin",
            impacto_dinero=None,
            clave_dedup=f"forecast_degradado:{datetime.now(timezone.utc):%Y-%W}",
            datos=backtest,
        )
        return 1 if emitida else 0

    async def _detectar_venta_perdida_semanal(self) -> int:
        """P3 · comprador — resumen semanal de venta perdida por quiebres."""
        try:
            from app.services.forecast import ForecastService

            vp = await ForecastService(self.db).get_venta_perdida(dias=7)
        except Exception:
            await self.db.rollback()
            return 0

        total = float(vp.get("venta_perdida_total") or 0)
        if total <= 0 or vp.get("productos_en_quiebre", 0) == 0:
            return 0

        margen = float(vp.get("margen_perdido_total") or 0)
        emitida = await self._emitir(
            codigo_alerta="venta_perdida_semanal",
            prioridad="P3",
            titulo=(
                f"Venta perdida por quiebres esta semana: ${total:,.0f} "
                f"({vp['productos_en_quiebre']} productos sin stock)"
            ),
            que_pasa=(
                f"{vp['productos_en_quiebre']} productos con demanda comprobada están en "
                f"quiebre. Venta no realizada estimada: ${total:,.0f}; margen no capturado: "
                f"${margen:,.0f}."
            ),
            por_que=(
                "La demanda se estimó con la velocidad de venta ANTERIOR al quiebre "
                "(demanda censurada). Si estos productos siguen sin stock, la pérdida "
                "crece cada día y el cliente aprende a comprar en otra parte."
            ),
            que_hacer=(
                "Priorizar en la próxima orden de compra los productos del detalle "
                "(ordenados por venta perdida). Revisar por qué el punto de reorden no "
                "disparó a tiempo: ¿lead time del proveedor mal registrado?"
            ),
            dueno="comprador",
            impacto_dinero=margen if margen > 0 else total,
            clave_dedup=f"venta_perdida_semanal:{datetime.now(timezone.utc):%Y-%W}",
            datos=vp.get("detalle", [])[:25],
        )
        return 1 if emitida else 0

    async def _detectar_proveedor_deteriorado(self) -> int:
        """P3 · comprador — el OTIF de un proveedor cayó vs su histórico.

        Un proveedor errático obliga a más stock de seguridad (capital) y
        causa quiebres. Detectarlo a las 3 órdenes, no al trimestre.
        """
        try:
            from app.services.scorecard_proveedores import ScorecardProveedoresService

            deteriorados = await ScorecardProveedoresService(self.db).get_deteriorados()
        except Exception:
            await self.db.rollback()
            return 0

        emitidas = 0
        for d in deteriorados:
            emitida = await self._emitir(
                codigo_alerta="proveedor_deteriorado",
                prioridad="P3",
                titulo=(
                    f"{d['proveedor']}: OTIF cayó {d['caida_pts']} pts "
                    f"({d['otif_historico']}% → {d['otif_reciente']}%)"
                ),
                que_pasa=(
                    f"En las últimas {d['ordenes_recientes']} órdenes, {d['proveedor']} "
                    f"entregó a tiempo y completo el {d['otif_reciente']}% de las veces; "
                    f"su histórico de 90 días era {d['otif_historico']}%."
                ),
                por_que=(
                    "Un deterioro sostenido suele anticipar problemas del proveedor "
                    "(capacidad, flujo de caja, transporte). Cada entrega tardía o "
                    "incompleta se paga en quiebres y stock de seguridad extra."
                ),
                que_hacer=(
                    "Contactar al proveedor y pedir causa y plan. Mientras tanto: subir "
                    "su lead time registrado (el sistema recalculará ROP y SS) y evaluar "
                    "proveedor alterno para los productos clase A que le compras."
                ),
                dueno="comprador",
                clave_dedup=f"proveedor_deteriorado:{d['proveedor_id']}",
                datos=d,
            )
            emitidas += 1 if emitida else 0
        return emitidas

    async def _detectar_merma_alta(self) -> int:
        """P3 · gerente_tienda — la merma del mes supera el objetivo (1% de la venta)."""
        try:
            from app.services.merma import MermaService

            reporte = await MermaService(self.db).get_reporte(dias=30)
        except Exception:
            await self.db.rollback()
            return 0

        pct = reporte.get("merma_pct_sobre_venta")
        if pct is None or pct < semantica.MERMA_PCT_ALERTA:
            return 0

        causa_principal = (
            reporte["por_causa"][0]["causa"] if reporte.get("por_causa") else "desconocida"
        )
        emitida = await self._emitir(
            codigo_alerta="merma_alta",
            prioridad="P3",
            titulo=(
                f"Merma del mes: {pct:.2f}% de la venta "
                f"(${reporte['merma_total_valor']:,.0f}) — objetivo < {semantica.MERMA_PCT_ALERTA}%"
            ),
            que_pasa=(
                f"La merma valorizada de 30 días es ${reporte['merma_total_valor']:,.0f} "
                f"({pct:.2f}% de la venta). La causa principal es '{causa_principal}'."
            ),
            por_que=(
                "Cada causa tiene un dueño distinto: vencimiento apunta a sobre-compra o "
                "mala rotación; daño a manipulación; robo a seguridad; error administrativo "
                "a proceso. El desglose por causa está en los datos de esta decisión."
            ),
            que_hacer=(
                f"Atacar la causa '{causa_principal}' primero (es la mayor). Revisar el top "
                "de productos con merma en los datos adjuntos y asignar acción por causa."
            ),
            dueno="gerente_tienda",
            impacto_dinero=reporte["merma_total_valor"],
            clave_dedup=f"merma_alta:{datetime.now(timezone.utc):%Y-%m}",
            datos={
                "por_causa": reporte.get("por_causa", []),
                "top_productos": reporte.get("top_productos", [])[:10],
            },
        )
        return 1 if emitida else 0

    async def _detectar_oc_vencida_sin_recibir(self) -> int:
        """P2 · comprador — OC enviadas cuya fecha promesa ya pasó sin recepción."""
        query = """
            SELECT o.id, o.numero, o.fecha_promesa, o.total_costo,
                   p.nombre as proveedor,
                   CURRENT_DATE - o.fecha_promesa as dias_vencida
            FROM ordenes_compra o
            LEFT JOIN proveedores p ON p.id = o.proveedor_id
            WHERE o.estado = 'enviada'
              AND o.fecha_promesa < CURRENT_DATE
            ORDER BY o.fecha_promesa
        """
        try:
            result = await self.db.execute(text(query))
            vencidas = result.fetchall()
        except Exception:
            await self.db.rollback()
            return 0

        emitidas = 0
        for oc in vencidas:
            total = float(oc[3]) if oc[3] is not None else None
            proveedor = oc[4] or "sin proveedor"
            emitida = await self._emitir(
                codigo_alerta="oc_vencida_sin_recibir",
                prioridad="P2",
                titulo=(
                    f"OC {oc[1]} de {proveedor} lleva {int(oc[5])} días vencida sin recibirse"
                ),
                que_pasa=(
                    f"La orden {oc[1]} tenía fecha promesa {oc[2]} y no se ha registrado "
                    f"recepción. Los productos que cubría siguen descubiertos."
                ),
                por_que=(
                    "O el proveedor incumplió (cuenta contra su OTIF) o la mercancía llegó "
                    "y nadie registró la recepción — en ese caso el inventario perpetuo está "
                    "subestimado y el sistema pedirá de más."
                ),
                que_hacer=(
                    f"Confirmar con {proveedor} el estado del despacho. Si ya llegó, "
                    "registrar la recepción hoy mismo. Si no llegará, cancelar la OC y "
                    "regenerar el pedido con otro proveedor."
                ),
                dueno="comprador",
                impacto_dinero=total,
                clave_dedup=f"oc_vencida:{oc[0]}",
                datos={"orden_id": int(oc[0]), "numero": oc[1], "proveedor": proveedor},
            )
            emitidas += 1 if emitida else 0
        return emitidas

    async def _detectar_markdown_recomendado(self) -> int:
        """P3 · pricing — capital atrapado con plan de salida vía markdown."""
        try:
            from app.services.pricing import PricingService

            await PricingService(self.db).sugerir_markdowns()
            oportunidades = await PricingService(self.db).get_oportunidades_precio(limite=30)
        except Exception:
            await self.db.rollback()
            return 0

        if not oportunidades:
            return 0

        capital = sum(o.get("impacto_estimado") or 0 for o in oportunidades)
        top = oportunidades[:10]

        emitida = await self._emitir(
            codigo_alerta="markdown_recomendado",
            prioridad="P3",
            titulo=f"{len(oportunidades)} productos con markdown recomendado",
            que_pasa=(
                f"Hay {len(oportunidades)} productos con inventario muerto o exceso de cobertura "
                f"donde un markdown escalonado liberaría capital estimado en ${capital:,.0f}."
            ),
            por_que=(
                "Sin rotación, el capital atrapado no genera margen y ocupa espacio que podría "
                "ir a productos con GMROI alto. Cada día sin acción aumenta el riesgo de "
                "obsolescencia total."
            ),
            que_hacer=(
                "Revisar la lista en Precio y Surtido: aplicar markdown en el top 10, "
                "verificar exhibición física antes de rebajar, y no recomprar estos SKUs."
            ),
            dueno="pricing",
            impacto_dinero=capital,
            clave_dedup=f"markdown_recomendado:{datetime.now(timezone.utc):%Y-%W}",
            datos=top,
        )
        return 1 if emitida else 0

    async def _detectar_surtido_eliminar(self) -> int:
        """P3 · comprador — SKUs en zona eliminar de la matriz GMROI×velocidad."""
        try:
            from app.services.surtido import SurtidoService

            revision = await SurtidoService(self.db).generar_revision()
            metricas = await SurtidoService(self.db).get_revision_surtido(limite=200)
        except Exception:
            await self.db.rollback()
            return 0

        eliminar = [m for m in metricas if m.get("accion") == "eliminar"]
        if not eliminar:
            return 0

        capital = sum(m.get("inventario_costo") or 0 for m in eliminar)
        detalle = [
            {
                "nombre": m["nombre"],
                "gmroi": m.get("gmroi"),
                "velocidad_relativa": m.get("velocidad_relativa"),
                "inventario_costo": m.get("inventario_costo"),
                "transferencia_proxy_pct": m.get("transferencia_proxy_pct"),
            }
            for m in eliminar[:15]
        ]

        emitida = await self._emitir(
            codigo_alerta="surtido_eliminar",
            prioridad="P3",
            titulo=f"{len(eliminar)} SKUs candidatos a eliminar del surtido",
            que_pasa=(
                f"La matriz GMROI×velocidad clasificó {len(eliminar)} productos como 'eliminar'. "
                f"Capital en riesgo: ${capital:,.0f}."
            ),
            por_que=(
                "GMROI bajo y/o velocidad por debajo del 25% de la mediana indica que el espacio "
                "y el capital invertido no se pagan. La transferencia proxy estima qué % de la "
                "demanda capturarían otros SKUs de la misma familia."
            ),
            que_hacer=(
                "Revisar revisión de surtido: para cada candidato, confirmar si hay sustituto en "
                "la familia. Aplicar baja lógica solo tras liquidar stock remanente."
            ),
            dueno="comprador",
            impacto_dinero=capital,
            clave_dedup=f"surtido_eliminar:{datetime.now(timezone.utc):%Y-%m}",
            datos={"revision": revision, "candidatos": detalle},
        )
        return 1 if emitida else 0

    async def _detectar_margen_erosion_mix(self) -> int:
        """P4 · pricing — el mix explica caída de margen (no volumen ni precio)."""
        try:
            from app.services.diagnostico_causal import DiagnosticoCausalService

            diag = await DiagnosticoCausalService(self.db).get_descomposicion()
        except Exception:
            await self.db.rollback()
            return 0

        delta_margen = float(diag.get("delta_margen") or 0)
        delta_venta = float(diag.get("delta_venta") or 0)
        efecto_mix = float(diag.get("efecto_mix") or 0)

        if delta_margen >= 0:
            return 0
        if abs(efecto_mix) < abs(delta_venta) * 0.2:
            return 0

        emitida = await self._emitir(
            codigo_alerta="margen_erosion_mix",
            prioridad="P4",
            titulo=f"Margen cayó ${abs(delta_margen):,.0f}: el mix de productos empeoró",
            que_pasa=(
                f"En los últimos {diag.get('dias_reciente', 7)} días vs el período previo, "
                f"el margen bajó ${abs(delta_margen):,.0f} mientras la venta cambió "
                f"${delta_venta:+,.0f}. El efecto mix (${efecto_mix:+,.0f}) explica buena "
                f"parte de la desviación."
            ),
            por_que=(
                "La mezcla de productos vendidos se desplazó hacia SKUs de menor margen o "
                "con más descuento. No es un problema de volumen total ni de lista de precios "
                "uniforme: es composición del ticket."
            ),
            que_hacer=(
                "Revisar el detalle del diagnóstico causal: identificar familias/productos "
                "que ganaron share con margen bajo. Evaluar exhibición, promos no rentables "
                "y surtido complementario."
            ),
            dueno="pricing",
            impacto_dinero=abs(delta_margen),
            clave_dedup=f"margen_erosion_mix:{datetime.now(timezone.utc):%Y-%W}",
            datos={
                "interpretacion": diag.get("interpretacion"),
                "detalle": diag.get("detalle", [])[:10],
            },
        )
        return 1 if emitida else 0

    # ------------------------------------------------------------- orquestación

    async def evaluar(self) -> Dict[str, Any]:
        """Corre todos los detectores, dedup incluida, y expira vencidas."""
        emitidas = 0
        detectores = [
            self._detectar_margen_negativo,
            self._detectar_quiebre_inminente,
            self._detectar_quiebre_fantasma,
            self._detectar_inventario_muerto,
            self._detectar_facturas_por_vencer,
            self._detectar_exactitud_baja,
            self._detectar_forecast_degradado,
            self._detectar_venta_perdida_semanal,
            self._detectar_proveedor_deteriorado,
            self._detectar_merma_alta,
            self._detectar_oc_vencida_sin_recibir,
            self._detectar_markdown_recomendado,
            self._detectar_surtido_eliminar,
            self._detectar_margen_erosion_mix,
        ]
        errores = []
        for detector in detectores:
            try:
                emitidas += await detector()
            except Exception as e:  # un detector roto no tumba a los demás
                await self.db.rollback()
                errores.append({"detector": detector.__name__, "error": str(e)})

        # Expirar pendientes vencidas (el SLA importa: lo viejo sin acción se archiva)
        await self.db.execute(
            text(
                """
                UPDATE decisiones SET estado = 'expirada'
                WHERE estado = 'pendiente' AND vence_en < NOW()
                """
            )
        )
        await self.db.commit()
        return {"decisiones_emitidas": emitidas, "errores": errores}

    async def get_bandeja(
        self,
        dueno: Optional[str] = None,
        estado: str = "pendiente",
        limite: int = 50,
    ) -> List[Dict[str, Any]]:
        """Bandeja de decisiones ordenada por prioridad y dinero en juego."""
        # Los casts explícitos son necesarios: asyncpg no puede inferir el tipo
        # de un parámetro usado en ":param IS NULL" y falla con AmbiguousParameterError.
        query = """
            SELECT id, codigo_alerta, prioridad, titulo, que_pasa, por_que, que_hacer,
                   impacto_dinero, dueno, vence_en, estado, datos, created_at
            FROM decisiones
            WHERE (CAST(:estado AS TEXT) = 'todas' OR estado = CAST(:estado AS TEXT))
              AND (CAST(:dueno AS TEXT) IS NULL OR dueno = CAST(:dueno AS TEXT))
            ORDER BY prioridad ASC, impacto_dinero DESC NULLS LAST, created_at DESC
            LIMIT :limite
        """
        result = await self.db.execute(
            text(query), {"estado": estado, "dueno": dueno, "limite": limite}
        )
        filas = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            fila["impacto_dinero"] = (
                float(fila["impacto_dinero"]) if fila["impacto_dinero"] is not None else None
            )
            filas.append(fila)
        return filas

    async def resolver(
        self,
        decision_id: int,
        estado: str,
        usuario: str,
        nota: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cierra una decisión registrando quién y con qué resultado.

        Este registro es el insumo del circuito de aprendizaje: qué alertas
        se aceptan, cuáles se rechazan y por qué.
        """
        if estado not in {"aprobada", "rechazada", "resuelta"}:
            raise ValueError(f"Estado de resolución inválido: {estado}")

        result = await self.db.execute(
            text(
                """
                UPDATE decisiones
                SET estado = :estado, resuelto_por = :usuario,
                    resultado_nota = :nota, resuelto_en = NOW()
                WHERE id = :id AND estado = 'pendiente'
                RETURNING id
                """
            ),
            {"estado": estado, "usuario": usuario, "nota": nota, "id": decision_id},
        )
        row = result.fetchone()
        await self.db.commit()
        if not row:
            raise ValueError("La decisión no existe o ya no está pendiente")
        return {"id": decision_id, "estado": estado}

    async def get_resumen(self) -> Dict[str, Any]:
        """Resumen para la cabecera de la bandeja."""
        result = await self.db.execute(
            text(
                """
                SELECT prioridad,
                       COUNT(*) as pendientes,
                       COALESCE(SUM(impacto_dinero), 0) as dinero
                FROM decisiones
                WHERE estado = 'pendiente'
                GROUP BY prioridad
                ORDER BY prioridad
                """
            )
        )
        por_prioridad = {
            r[0]: {"pendientes": int(r[1]), "impacto_dinero": float(r[2])}
            for r in result.fetchall()
        }
        total_dinero = sum(v["impacto_dinero"] for v in por_prioridad.values())
        total_pendientes = sum(v["pendientes"] for v in por_prioridad.values())
        return {
            "pendientes": total_pendientes,
            "impacto_dinero_total": round(total_dinero, 2),
            "por_prioridad": por_prioridad,
        }

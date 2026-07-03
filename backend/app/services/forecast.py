"""
Servicio de forecast (Fase 2) — el corazón del sistema.

Un único pronóstico probabilístico por producto alimenta compras,
reabastecimiento y venta perdida. Responsabilidades:

1. Consolidar el historial diario (la tabla fuente es una ventana rodante
   de 30 días; sin acumulación no hay estacionalidad ni modelos serios).
2. Generar y persistir el forecast P10/P50/P90 por producto-día.
3. Backtesting honesto: el modelo champion contra el baseline ingenuo
   (promedio del mismo día de semana, últimas 4 semanas). Si el champion
   no le gana al baseline, no se usa — gobernanza de modelos.
4. Venta perdida valorizada: la métrica que financia el programa.
"""
import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import forecast_models as fm
from app import semantica


class ForecastService:
    """Consolidación de historial, forecast, backtest y venta perdida."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------- consolidación

    async def consolidar_historial(self) -> Dict[str, Any]:
        """Vuelca la ventana rodante de ventas al historial persistente.

        Idempotente: corre a diario (upsert por producto-fecha). Es el paso
        que convierte una foto de 30 días en una historia acumulada.

        Sincroniza los maestros primero: el historial se indexa por producto_id
        del maestro, así que sin maestro poblado no habría nada que consolidar
        (y los productos nuevos deben entrar al maestro cada día).
        """
        from app.services.maestros import MaestrosService

        maestros = await MaestrosService(self.db).sincronizar()

        query = """
            INSERT INTO ventas_diarias_historicas
                (producto_id, fecha, unidades, venta_neta, precio_promedio, costo_promedio)
            SELECT
                p.id,
                v.fecha_venta,
                SUM(v.cantidad),
                SUM(v.precio * v.cantidad),
                AVG(v.precio),
                AVG(v.precio_promedio_compra)
            FROM reportes_ventas_30dias v
            JOIN productos p
              ON p.nombre = REGEXP_REPLACE(UPPER(TRIM(v.nombre)), '\\s+', ' ', 'g')
            WHERE v.fecha_venta IS NOT NULL
            GROUP BY p.id, v.fecha_venta
            ON CONFLICT (producto_id, fecha) DO UPDATE SET
                unidades = EXCLUDED.unidades,
                venta_neta = EXCLUDED.venta_neta,
                precio_promedio = EXCLUDED.precio_promedio,
                costo_promedio = EXCLUDED.costo_promedio
        """
        result = await self.db.execute(text(query))
        await self.db.commit()

        rango = await self.db.execute(
            text(
                """
                SELECT MIN(fecha), MAX(fecha), COUNT(DISTINCT producto_id)
                FROM ventas_diarias_historicas
                """
            )
        )
        fila = rango.fetchone()
        return {
            "filas_upsert": result.rowcount,
            "historia_desde": str(fila[0]) if fila and fila[0] else None,
            "historia_hasta": str(fila[1]) if fila and fila[1] else None,
            "productos_con_historia": int(fila[2] or 0) if fila else 0,
            "maestros_sincronizados": maestros.get("productos_desde_items", 0)
            + maestros.get("productos_solo_en_ventas", 0),
        }

    # ------------------------------------------------------------- lectura

    async def _series_por_producto(
        self, dias_max: int = 400, solo_activos_dias: int = 60
    ) -> Dict[int, Dict[str, Any]]:
        """Series diarias por producto con venta en los últimos N días."""
        query = """
            SELECT h.producto_id, p.nombre, h.fecha, h.unidades,
                   h.precio_promedio, h.costo_promedio
            FROM ventas_diarias_historicas h
            JOIN productos p ON p.id = h.producto_id
            WHERE h.fecha >= CURRENT_DATE - CAST(:dias_max AS INTEGER)
              AND h.producto_id IN (
                  SELECT DISTINCT producto_id FROM ventas_diarias_historicas
                  WHERE fecha >= CURRENT_DATE - CAST(:activos AS INTEGER)
                    AND unidades > 0
              )
            ORDER BY h.producto_id, h.fecha
        """
        result = await self.db.execute(
            text(query), {"dias_max": dias_max, "activos": solo_activos_dias}
        )
        series: Dict[int, Dict[str, Any]] = {}
        for r in result.fetchall():
            pid = int(r[0])
            if pid not in series:
                series[pid] = {"nombre": r[1], "ventas": {}, "precios": [], "costos": []}
            series[pid]["ventas"][r[2]] = float(r[3] or 0)
            if r[4] is not None:
                series[pid]["precios"].append(float(r[4]))
            if r[5] is not None:
                series[pid]["costos"].append(float(r[5]))
        return series

    # ------------------------------------------------------------- generación

    async def generar(self, horizonte_dias: int = 28) -> Dict[str, Any]:
        """Genera y persiste el forecast P10/P50/P90 para productos activos."""
        series = await self._series_por_producto()
        hoy = date.today()

        # Limpiar pronósticos futuros previos (se reemplazan por los nuevos)
        await self.db.execute(
            text("DELETE FROM forecasts WHERE fecha_objetivo >= :hoy"), {"hoy": hoy}
        )

        productos_ok = 0
        modelos_usados: Dict[str, int] = {}
        for pid, data in series.items():
            pronostico = fm.generar_forecast_producto(
                data["ventas"], fecha_desde=hoy, horizonte_dias=horizonte_dias
            )
            if not pronostico:
                continue
            productos_ok += 1
            modelos_usados[pronostico[0].modelo] = modelos_usados.get(pronostico[0].modelo, 0) + 1
            for fd in pronostico:
                await self.db.execute(
                    text(
                        """
                        INSERT INTO forecasts
                            (producto_id, fecha_objetivo, p10, p50, p90, modelo)
                        VALUES (:p, :f, :p10, :p50, :p90, :m)
                        """
                    ),
                    {
                        "p": pid,
                        "f": fd.fecha,
                        "p10": round(fd.p10, 3),
                        "p50": round(fd.p50, 3),
                        "p90": round(fd.p90, 3),
                        "m": fd.modelo,
                    },
                )
        await self.db.commit()
        return {
            "productos_pronosticados": productos_ok,
            "horizonte_dias": horizonte_dias,
            "modelos_usados": modelos_usados,
        }

    # -------------------------------------------------------------- backtest

    async def backtest(self, dias_holdout: int = 14) -> Dict[str, Any]:
        """Backtest honesto con corte temporal real.

        Entrena con la historia hasta (hoy − holdout) y compara contra lo que
        realmente pasó en el holdout: champion (modelos de fm) vs baseline
        (mismo día de semana, últimas 4 semanas). Persiste el resultado.
        """
        series = await self._series_por_producto()
        hoy = date.today()
        corte = hoy - timedelta(days=dias_holdout)

        reales_todos: List[float] = []
        champion_todos: List[float] = []
        baseline_todos: List[float] = []
        detalle_productos: List[Dict[str, Any]] = []

        for pid, data in series.items():
            ventas = data["ventas"]
            entrenamiento = {f: v for f, v in ventas.items() if f < corte}
            if len(entrenamiento) < fm.MIN_DIAS_HISTORIA:
                continue

            # Reales del holdout (densos: días sin venta = 0)
            reales = [
                float(ventas.get(corte + timedelta(days=i), 0.0)) for i in range(dias_holdout)
            ]
            if sum(reales) == 0:
                continue  # productos muertos en el holdout no miden nada

            champ = fm.generar_forecast_producto(entrenamiento, corte, dias_holdout)
            champion = [fd.p50 for fd in champ]
            baseline = fm.forecast_baseline_naive(entrenamiento, corte, dias_holdout)

            reales_todos.extend(reales)
            champion_todos.extend(champion)
            baseline_todos.extend(baseline)

            w_champ = fm.wmape(reales, champion)
            w_base = fm.wmape(reales, baseline)
            detalle_productos.append(
                {
                    "nombre": data["nombre"],
                    "unidades_reales": round(sum(reales), 1),
                    "wmape_champion": round(w_champ, 3) if w_champ is not None else None,
                    "wmape_baseline": round(w_base, 3) if w_base is not None else None,
                    "modelo": champ[0].modelo if champ else None,
                }
            )

        wmape_champion = fm.wmape(reales_todos, champion_todos)
        wmape_baseline = fm.wmape(reales_todos, baseline_todos)
        sesgo_champion = fm.sesgo_pct(reales_todos, champion_todos)
        sesgo_baseline = fm.sesgo_pct(reales_todos, baseline_todos)

        detalle_productos.sort(key=lambda x: x["unidades_reales"], reverse=True)
        resumen = {
            "dias_holdout": dias_holdout,
            "productos_evaluados": len(detalle_productos),
            "wmape_champion": round(wmape_champion, 4) if wmape_champion is not None else None,
            "wmape_baseline": round(wmape_baseline, 4) if wmape_baseline is not None else None,
            "sesgo_champion_pct": round(sesgo_champion, 2) if sesgo_champion is not None else None,
            "sesgo_baseline_pct": round(sesgo_baseline, 2) if sesgo_baseline is not None else None,
            "champion_gana": (
                wmape_champion < wmape_baseline
                if wmape_champion is not None and wmape_baseline is not None
                else None
            ),
            "top_productos": detalle_productos[:30],
        }

        await self.db.execute(
            text(
                """
                INSERT INTO forecast_backtests
                    (dias_holdout, productos_evaluados, wmape_champion, wmape_baseline,
                     sesgo_champion_pct, sesgo_baseline_pct, detalle)
                VALUES (:dias, :n, :wc, :wb, :sc, :sb, CAST(:detalle AS JSON))
                """
            ),
            {
                "dias": dias_holdout,
                "n": len(detalle_productos),
                "wc": resumen["wmape_champion"],
                "wb": resumen["wmape_baseline"],
                "sc": resumen["sesgo_champion_pct"],
                "sb": resumen["sesgo_baseline_pct"],
                "detalle": json.dumps(detalle_productos[:100], default=str),
            },
        )
        await self.db.commit()
        return resumen

    async def get_ultimo_backtest(self) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT ejecutado_en, dias_holdout, productos_evaluados,
                       wmape_champion, wmape_baseline,
                       sesgo_champion_pct, sesgo_baseline_pct, detalle
                FROM forecast_backtests
                ORDER BY ejecutado_en DESC LIMIT 1
                """
            )
        )
        r = result.fetchone()
        if not r:
            return None
        return {
            "ejecutado_en": str(r[0]),
            "dias_holdout": int(r[1]),
            "productos_evaluados": int(r[2]),
            "wmape_champion": float(r[3]) if r[3] is not None else None,
            "wmape_baseline": float(r[4]) if r[4] is not None else None,
            "sesgo_champion_pct": float(r[5]) if r[5] is not None else None,
            "sesgo_baseline_pct": float(r[6]) if r[6] is not None else None,
            "detalle": r[7],
        }

    # -------------------------------------------------------- precisión real

    async def get_precision(self, dias: int = 28) -> Dict[str, Any]:
        """Precisión REAL: forecasts persistidos vs lo que pasó después.

        Es la métrica de gobernanza (no el backtest): mide el forecast que
        de verdad se usó para decidir, contra la venta observada.
        """
        query = """
            SELECT f.p50, COALESCE(h.unidades, 0) as real
            FROM forecasts f
            LEFT JOIN ventas_diarias_historicas h
                   ON h.producto_id = f.producto_id AND h.fecha = f.fecha_objetivo
            WHERE f.fecha_objetivo >= CURRENT_DATE - CAST(:dias AS INTEGER)
              AND f.fecha_objetivo < CURRENT_DATE
        """
        result = await self.db.execute(text(query), {"dias": dias})
        filas = result.fetchall()
        if not filas:
            return {"evaluaciones": 0, "wmape": None, "sesgo_pct": None}

        predichos = [float(r[0]) for r in filas]
        reales = [float(r[1]) for r in filas]
        w = fm.wmape(reales, predichos)
        s = fm.sesgo_pct(reales, predichos)
        return {
            "evaluaciones": len(filas),
            "wmape": round(w, 4) if w is not None else None,
            "sesgo_pct": round(s, 2) if s is not None else None,
        }

    # ------------------------------------------------------ venta perdida

    async def get_venta_perdida(self, dias: int = 30) -> Dict[str, Any]:
        """Venta y margen perdidos por quiebre, valorizados por producto.

        Metodología (documentada, conservadora):
        - Solo productos HOY sin stock (quiebre confirmado por inventario).
        - Días de quiebre = días desde la última venta registrada (tope: N).
        - Demanda perdida = velocidad esperada ANTES del quiebre (demanda
          censurada: jamás se usa la venta observada durante el quiebre).
        - Valorización con precio y margen reales del producto.
        """
        query = """
            WITH sin_stock AS (
                SELECT p.id, p.nombre, p.precio_venta, p.costo_unitario
                FROM productos p
                JOIN items i ON UPPER(TRIM(i.nombre)) = p.nombre
                WHERE COALESCE(i.cantidad_disponible, 0) <= 0 AND p.activo
            ),
            ultima AS (
                SELECT producto_id, MAX(fecha) as ultima_venta
                FROM ventas_diarias_historicas
                WHERE unidades > 0
                GROUP BY producto_id
            ),
            velocidad AS (
                SELECT h.producto_id,
                       SUM(h.unidades) as unidades,
                       COUNT(*) as dias_con_registro,
                       MIN(h.fecha) as desde,
                       MAX(h.fecha) as hasta
                FROM ventas_diarias_historicas h
                JOIN ultima u ON u.producto_id = h.producto_id
                WHERE h.fecha > u.ultima_venta - INTERVAL '30 days'
                  AND h.fecha <= u.ultima_venta
                GROUP BY h.producto_id
            )
            SELECT s.nombre, s.precio_venta, s.costo_unitario,
                   u.ultima_venta, v.unidades, v.desde, v.hasta
            FROM sin_stock s
            JOIN ultima u ON u.producto_id = s.id
            JOIN velocidad v ON v.producto_id = s.id
        """
        result = await self.db.execute(text(query))
        hoy = date.today()

        detalle: List[Dict[str, Any]] = []
        venta_perdida_total = 0.0
        margen_perdido_total = 0.0
        for r in result.fetchall():
            nombre, precio, costo, ultima_venta, unidades, desde, hasta = r
            if ultima_venta is None or desde is None:
                continue
            dias_ventana = max((hasta - desde).days + 1, 1)
            vd = semantica.venta_diaria(float(unidades or 0), dias_ventana)
            if vd <= 0:
                continue
            dias_quiebre = min((hoy - ultima_venta).days, dias)
            if dias_quiebre <= 0:
                continue

            precio_f = float(precio or 0)
            costo_f = float(costo) if costo is not None else None
            vp = semantica.venta_perdida(vd, dias_quiebre, precio_f)
            mp = semantica.margen_perdido(vd, dias_quiebre, precio_f, costo_f)
            venta_perdida_total += vp
            if mp is not None:
                margen_perdido_total += mp
            detalle.append(
                {
                    "nombre": nombre,
                    "dias_en_quiebre": dias_quiebre,
                    "venta_diaria_previa": round(vd, 2),
                    "venta_perdida": round(vp, 2),
                    "margen_perdido": round(mp, 2) if mp is not None else None,
                }
            )

        detalle.sort(key=lambda x: x["venta_perdida"], reverse=True)
        return {
            "ventana_dias": dias,
            "productos_en_quiebre": len(detalle),
            "venta_perdida_total": round(venta_perdida_total, 2),
            "margen_perdido_total": round(margen_perdido_total, 2),
            "detalle": detalle[:50],
        }

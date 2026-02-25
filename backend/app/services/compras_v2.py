"""
Servicio de compras v2 — algoritmo con historial completo (40 meses).

Mejoras sobre v1:
- Usa la tabla `facturas` directamente (no la vista de 30 días)
- Velocidad de venta ponderada exponencialmente (meses recientes pesan más)
- Ajuste estacional: detecta si el mes actual es históricamente alto/bajo
- Comparación de precios entre proveedores por SKU
- Resumen de urgencias por proveedor para las cards de la UI
"""
import math
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    PrecioProveedorComparativo,
    ProveedorUrgenciaResponse,
    SugerenciaCompraV2Response,
)


class ComprasV2Service:
    """Sugerencias de compra con historial completo y ajuste estacional."""

    # Decaimiento exponencial: e^(-LAMBDA * meses_atras)
    # 0 meses: peso 1.0 | 12 meses: ~0.43 | 24 meses: ~0.19
    LAMBDA = 0.07

    # Coberturas objetivo en días según clasificación ABC
    COBERTURA_ABC = {"A": 45, "B": 30, "C": 21}

    # Umbrales de urgencia en días de stock
    UMBRAL_URGENTE = 7
    UMBRAL_ALTA = 14
    UMBRAL_MEDIA = 30

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Queries a la DB
    # -------------------------------------------------------------------------

    async def _get_ventas_historicas(self) -> Dict[str, List[Tuple[int, int, float, float]]]:
        """
        Devuelve {nombre: [(año, mes, unidades, total_ventas), ...]}
        para todos los SKUs con historia de los últimos 40 meses.
        """
        query = """
            SELECT
                f.nombre,
                EXTRACT(YEAR FROM f.fecha)::int  AS año,
                EXTRACT(MONTH FROM f.fecha)::int AS mes,
                SUM(f.cantidad)                  AS unidades,
                SUM(f.precio * f.cantidad)        AS total_ventas
            FROM facturas f
            WHERE f.fecha >= CURRENT_DATE - INTERVAL '40 months'
              AND f.cantidad > 0
            GROUP BY f.nombre,
                     EXTRACT(YEAR FROM f.fecha),
                     EXTRACT(MONTH FROM f.fecha)
            ORDER BY f.nombre, año, mes
        """
        result = await self.db.execute(text(query))
        rows = result.fetchall()

        historial: Dict[str, List] = {}
        for row in rows:
            nombre = row[0]
            historial.setdefault(nombre, []).append(
                (int(row[1]), int(row[2]), float(row[3]), float(row[4]))
            )
        return historial

    async def _get_stock_actual(self) -> Dict[str, float]:
        """Devuelve {nombre: stock_disponible} desde la tabla items."""
        query = "SELECT nombre, COALESCE(cantidad_disponible, 0) FROM items WHERE nombre IS NOT NULL"
        result = await self.db.execute(text(query))
        return {row[0]: float(row[1]) for row in result.fetchall()}

    async def _get_familias(self) -> Dict[str, str]:
        """Devuelve {nombre: familia}."""
        query = "SELECT nombre, familia FROM items WHERE familia IS NOT NULL AND nombre IS NOT NULL"
        result = await self.db.execute(text(query))
        return {row[0]: row[1] for row in result.fetchall()}

    async def _get_precios_proveedor(self) -> Dict[str, List[Dict]]:
        """
        Devuelve {nombre: [{proveedor, precio_compra, fecha_ultima_compra}, ...]}
        Obtiene el precio más reciente por proveedor por producto.
        """
        query = """
            SELECT DISTINCT ON (nombre, proveedor)
                nombre,
                proveedor,
                precio   AS precio_compra,
                fecha    AS fecha_ultima_compra
            FROM facturas_proveedor
            WHERE proveedor IS NOT NULL
              AND nombre   IS NOT NULL
              AND precio   IS NOT NULL
              AND precio   > 0
            ORDER BY nombre, proveedor, fecha DESC
        """
        result = await self.db.execute(text(query))
        rows = result.fetchall()

        precios: Dict[str, List] = {}
        for row in rows:
            precios.setdefault(row[0], []).append(
                {
                    "proveedor": row[1],
                    "precio_compra": float(row[2]),
                    "fecha_ultima_compra": row[3],
                }
            )
        return precios

    async def _get_proveedor_moda(self) -> Dict[str, str]:
        """
        Devuelve {nombre: proveedor_principal} basado en las compras
        de los últimos 6 meses (proveedor más frecuente por SKU).
        """
        query = """
            SELECT DISTINCT ON (nombre)
                nombre,
                proveedor
            FROM (
                SELECT
                    nombre,
                    proveedor,
                    COUNT(*) AS frecuencia
                FROM facturas_proveedor
                WHERE fecha >= CURRENT_DATE - INTERVAL '6 months'
                  AND proveedor IS NOT NULL
                  AND nombre   IS NOT NULL
                GROUP BY nombre, proveedor
            ) ranked
            ORDER BY nombre, frecuencia DESC
        """
        result = await self.db.execute(text(query))
        return {row[0]: row[1] for row in result.fetchall()}

    # -------------------------------------------------------------------------
    # Cálculos estadísticos
    # -------------------------------------------------------------------------

    @classmethod
    def _velocidad_ponderada(cls, ventas: List[Tuple]) -> float:
        """
        Promedio mensual ponderado exponencialmente → velocidad diaria.
        ventas: [(año, mes, unidades, total_ventas), ...] de más antiguo a más reciente.
        """
        if not ventas:
            return 0.0

        total_meses = len(ventas)
        num = 0.0
        den = 0.0
        for i, (_, _, unidades, _) in enumerate(ventas):
            meses_atras = total_meses - 1 - i
            peso = math.exp(-cls.LAMBDA * meses_atras)
            num += unidades * peso
            den += peso

        if den == 0:
            return 0.0
        return (num / den) / 30  # unidades por día

    @staticmethod
    def _factor_estacional(ventas: List[Tuple], mes_objetivo: int) -> float:
        """
        Factor multiplicador estacional para el mes actual.
        1.0 = mes normal | 1.4 = mes 40% por encima del promedio.
        """
        if len(ventas) < 6:
            return 1.0

        por_mes: Dict[int, List[float]] = {}
        for _, mes, unidades, _ in ventas:
            por_mes.setdefault(mes, []).append(float(unidades))

        if len(por_mes) < 3:
            return 1.0

        all_vals = [v for vals in por_mes.values() for v in vals]
        promedio_global = sum(all_vals) / len(all_vals)
        if promedio_global == 0 or mes_objetivo not in por_mes:
            return 1.0

        promedio_mes = sum(por_mes[mes_objetivo]) / len(por_mes[mes_objetivo])
        return max(0.5, min(2.0, promedio_mes / promedio_global))

    @staticmethod
    def _tendencia(ventas: List[Tuple]) -> str:
        """Compara últimos 3 meses vs los 3 anteriores."""
        if len(ventas) < 4:
            return "estable"
        recent = ventas[-3:]
        older = ventas[-6:-3]
        if not older:
            return "estable"
        avg_r = sum(u for _, _, u, _ in recent) / len(recent)
        avg_o = sum(u for _, _, u, _ in older) / len(older)
        if avg_o == 0:
            return "estable"
        ratio = avg_r / avg_o
        if ratio > 1.2:
            return "creciente"
        if ratio < 0.8:
            return "decreciente"
        return "estable"

    @staticmethod
    def _clases_abc(total_por_producto: Dict[str, float]) -> Dict[str, str]:
        """Clasifica todos los productos en A/B/C según contribución al total."""
        if not total_por_producto:
            return {}
        total = sum(total_por_producto.values())
        if total == 0:
            return {n: "C" for n in total_por_producto}

        sorted_items = sorted(total_por_producto.items(), key=lambda x: x[1], reverse=True)
        clases: Dict[str, str] = {}
        acum = 0.0
        for nombre, venta in sorted_items:
            if acum < 0.80:
                clases[nombre] = "A"
            elif acum < 0.95:
                clases[nombre] = "B"
            else:
                clases[nombre] = "C"
            acum += venta / total
        return clases

    # -------------------------------------------------------------------------
    # Método principal
    # -------------------------------------------------------------------------

    async def get_sugerencias_v2(
        self, proveedor: Optional[str] = None
    ) -> List[SugerenciaCompraV2Response]:
        """
        Calcula sugerencias de compra usando historial completo de 40 meses.
        Si se pasa `proveedor`, filtra solo los SKUs de ese proveedor.
        """
        historial = await self._get_ventas_historicas()
        stock = await self._get_stock_actual()
        familias = await self._get_familias()
        precios = await self._get_precios_proveedor()
        moda = await self._get_proveedor_moda()

        # Total de ventas por producto para ABC (últimos 12 meses)
        total_ventas_12m: Dict[str, float] = {}
        hoy = date.today()
        for nombre, meses in historial.items():
            ventas_12m = [
                total
                for anio, mes, _, total in meses
                if (hoy.year - anio) * 12 + (hoy.month - mes) <= 12
            ]
            total_ventas_12m[nombre] = sum(ventas_12m)

        clases_abc = self._clases_abc(total_ventas_12m)
        mes_actual = hoy.month
        sugerencias: List[SugerenciaCompraV2Response] = []

        for nombre, ventas_mensuales in historial.items():
            if not ventas_mensuales:
                continue

            # Velocidad diaria con ajuste estacional
            vel_base = self._velocidad_ponderada(ventas_mensuales)
            if vel_base <= 0:
                continue
            factor = self._factor_estacional(ventas_mensuales, mes_actual)
            velocidad = vel_base * factor

            # Stock y días de cobertura
            stock_actual = stock.get(nombre, 0)
            dias_stock = stock_actual / velocidad if velocidad > 0 else 999.0

            # Clasificación ABC y cobertura objetivo
            abc = clases_abc.get(nombre, "C")
            cobertura = self.COBERTURA_ABC[abc]

            # Cantidad sugerida
            cantidad_sugerida = max(0, int(round(velocidad * cobertura - stock_actual)))

            # Urgencia
            if dias_stock <= self.UMBRAL_URGENTE:
                urgencia = "urgente"
            elif dias_stock <= self.UMBRAL_ALTA:
                urgencia = "alta"
            elif dias_stock <= self.UMBRAL_MEDIA:
                urgencia = "media"
            elif cantidad_sugerida > 0:
                urgencia = "baja"
            else:
                urgencia = "ok"

            # Proveedor principal
            prov_principal = moda.get(nombre)
            otros_provs = precios.get(nombre, [])

            # Si se filtra por proveedor, saltar SKUs que no correspondan
            if proveedor:
                proveedores_sku = {p["proveedor"] for p in otros_provs}
                if prov_principal != proveedor and proveedor not in proveedores_sku:
                    continue
                # Si el proveedor solicitado no es el principal pero sí vende el SKU, lo mostramos
                if prov_principal != proveedor and proveedor in proveedores_sku:
                    prov_principal = proveedor

            # Precio del proveedor principal y lista comparativa
            precio_ultimo: Optional[float] = None
            lista_comparativa: List[PrecioProveedorComparativo] = []

            # Ordenar otros proveedores: primero el más barato
            otros_provs_sorted = sorted(otros_provs, key=lambda p: p["precio_compra"])
            for p in otros_provs_sorted:
                es_principal = p["proveedor"] == prov_principal
                lista_comparativa.append(
                    PrecioProveedorComparativo(
                        proveedor=p["proveedor"],
                        precio_compra=p["precio_compra"],
                        fecha_ultima_compra=p["fecha_ultima_compra"],
                        es_proveedor_principal=es_principal,
                    )
                )
                if es_principal:
                    precio_ultimo = p["precio_compra"]

            # Si no encontramos precio del principal, usar el más reciente disponible
            if precio_ultimo is None and otros_provs_sorted:
                precio_ultimo = otros_provs_sorted[0]["precio_compra"]

            costo_estimado = cantidad_sugerida * (precio_ultimo or 0)
            tendencia = self._tendencia(ventas_mensuales)

            sugerencias.append(
                SugerenciaCompraV2Response(
                    nombre=nombre,
                    familia=familias.get(nombre),
                    proveedor_principal=prov_principal,
                    stock_actual=int(stock_actual),
                    velocidad_diaria=round(velocidad, 2),
                    dias_stock=round(dias_stock, 1),
                    cantidad_sugerida=cantidad_sugerida,
                    precio_ultimo=precio_ultimo,
                    costo_estimado=round(costo_estimado, 2),
                    urgencia=urgencia,
                    clasificacion_abc=abc,
                    tendencia=tendencia,
                    factor_estacional=round(factor, 2),
                    otros_proveedores=lista_comparativa,
                )
            )

        # Orden: urgencia desc, días de stock asc
        _orden = {"urgente": 0, "alta": 1, "media": 2, "baja": 3, "ok": 4}
        sugerencias.sort(key=lambda x: (_orden.get(x.urgencia, 5), x.dias_stock))
        return sugerencias

    async def get_urgencias_por_proveedor(self) -> List[ProveedorUrgenciaResponse]:
        """
        Resumen de urgencias por proveedor para las tarjetas de la UI.
        """
        sugerencias = await self.get_sugerencias_v2()

        por_proveedor: Dict[str, Dict] = {}
        for s in sugerencias:
            prov = s.proveedor_principal or "Sin proveedor"
            if prov not in por_proveedor:
                por_proveedor[prov] = {
                    "urgente": 0,
                    "alta": 0,
                    "media": 0,
                    "baja_ok": 0,
                    "inversion": 0.0,
                }
            d = por_proveedor[prov]
            if s.urgencia == "urgente":
                d["urgente"] += 1
            elif s.urgencia == "alta":
                d["alta"] += 1
            elif s.urgencia == "media":
                d["media"] += 1
            else:
                d["baja_ok"] += 1
            d["inversion"] += s.costo_estimado

        result = [
            ProveedorUrgenciaResponse(
                proveedor=prov,
                urgente=d["urgente"],
                alta=d["alta"],
                media=d["media"],
                ok=d["baja_ok"],
                total_productos_activos=d["urgente"] + d["alta"] + d["media"] + d["baja_ok"],
                inversion_estimada=round(d["inversion"], 2),
            )
            for prov, d in por_proveedor.items()
        ]

        # Más urgente primero
        result.sort(key=lambda x: -(x.urgente * 3 + x.alta * 2 + x.media))
        return result

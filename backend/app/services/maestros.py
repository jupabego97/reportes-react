"""
Servicio de maestros únicos (Fase 1) — producto, proveedor, familia, tienda.

Construye y mantiene la versión canónica de cada entidad a partir de las
fuentes crudas (`items` y `reportes_ventas_30dias`), normalizando nombres
con la capa semántica. También produce el reporte de calidad de datos:
sin datos limpios no hay decisiones confiables.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica


class MaestrosService:
    """Sincronización y diagnóstico de los maestros únicos."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ fuentes

    async def _leer_items(self) -> List[Dict[str, Any]]:
        """Lee la tabla items tolerando esquemas con o sin columna proveedor."""
        for query in (
            """SELECT nombre, familia, precio, cantidad_disponible, proveedor
               FROM items WHERE nombre IS NOT NULL""",
            """SELECT nombre, familia, precio, cantidad_disponible, NULL as proveedor
               FROM items WHERE nombre IS NOT NULL""",
        ):
            try:
                result = await self.db.execute(text(query))
                return [dict(r._asdict()) for r in result.fetchall()]
            except Exception:
                await self.db.rollback()
                continue
        return []

    async def _leer_ventas_agregadas(self) -> List[Dict[str, Any]]:
        """Proveedor más frecuente y costo promedio por producto según ventas."""
        query = """
            SELECT
                nombre,
                MAX(familia) as familia,
                MAX(proveedor_moda) as proveedor,
                AVG(precio_promedio_compra) as costo_promedio,
                AVG(precio) as precio_promedio
            FROM reportes_ventas_30dias
            WHERE nombre IS NOT NULL
            GROUP BY nombre
        """
        try:
            result = await self.db.execute(text(query))
            return [dict(r._asdict()) for r in result.fetchall()]
        except Exception:
            await self.db.rollback()
            return []

    # ------------------------------------------------------------ sincronización

    async def sincronizar(self) -> Dict[str, Any]:
        """Reconstruye los maestros desde las fuentes crudas (idempotente).

        Orden: familias → proveedores → productos. Los nombres se normalizan
        una sola vez aquí; el resto del sistema consume los maestros.
        """
        items = await self._leer_items()
        ventas = await self._leer_ventas_agregadas()
        ventas_por_nombre = {
            semantica.normalizar_nombre(v["nombre"]): v for v in ventas if v.get("nombre")
        }

        # --- familias (desde items y ventas)
        familias_vistas = set()
        for fila in items:
            fam = semantica.familia_canonica(fila.get("familia"))
            if fam:
                familias_vistas.add(fam)
        for fila in ventas:
            fam = semantica.familia_canonica(fila.get("familia"))
            if fam:
                familias_vistas.add(fam)

        for fam in sorted(familias_vistas):
            await self.db.execute(
                text("INSERT INTO familias (nombre) VALUES (:n) ON CONFLICT (nombre) DO NOTHING"),
                {"n": fam},
            )

        # --- proveedores (alias crudos → nombre canónico)
        alias_por_canonico: Dict[str, set] = {}
        for fila in list(items) + list(ventas):
            crudo = fila.get("proveedor")
            canonico = semantica.proveedor_canonico(crudo)
            if canonico:
                alias_por_canonico.setdefault(canonico, set())
                if crudo and str(crudo).strip() != canonico:
                    alias_por_canonico[canonico].add(str(crudo).strip())

        for prov, alias in sorted(alias_por_canonico.items()):
            await self.db.execute(
                text(
                    """
                    INSERT INTO proveedores (nombre, alias)
                    VALUES (:n, :a)
                    ON CONFLICT (nombre) DO UPDATE SET alias = EXCLUDED.alias
                    """
                ),
                {"n": prov, "a": " | ".join(sorted(alias)) or None},
            )

        # --- productos (items es la fuente primaria; ventas complementa costo/proveedor)
        productos_sync = 0
        nombres_vistos = set()
        for fila in items:
            nombre = semantica.normalizar_nombre(fila.get("nombre"))
            if not nombre or nombre in nombres_vistos:
                continue
            nombres_vistos.add(nombre)

            venta = ventas_por_nombre.get(nombre, {})
            familia = semantica.familia_canonica(fila.get("familia")) or semantica.familia_canonica(
                venta.get("familia")
            )
            proveedor = semantica.proveedor_canonico(
                fila.get("proveedor")
            ) or semantica.proveedor_canonico(venta.get("proveedor"))
            costo = venta.get("costo_promedio")

            await self.db.execute(
                text(
                    """
                    INSERT INTO productos
                        (nombre, familia_id, proveedor_principal_id, precio_venta, costo_unitario)
                    VALUES (
                        :nombre,
                        (SELECT id FROM familias WHERE nombre = :familia),
                        (SELECT id FROM proveedores WHERE nombre = :proveedor),
                        :precio,
                        :costo
                    )
                    ON CONFLICT (nombre) DO UPDATE SET
                        familia_id = EXCLUDED.familia_id,
                        proveedor_principal_id = EXCLUDED.proveedor_principal_id,
                        precio_venta = EXCLUDED.precio_venta,
                        costo_unitario = COALESCE(EXCLUDED.costo_unitario, productos.costo_unitario),
                        updated_at = NOW()
                    """
                ),
                {
                    "nombre": nombre,
                    "familia": familia,
                    "proveedor": proveedor,
                    "precio": float(fila.get("precio") or 0) or None,
                    "costo": float(costo) if costo is not None else None,
                },
            )
            productos_sync += 1

        # Productos que solo aparecen en ventas (vendidos pero no en items)
        productos_solo_ventas = 0
        for nombre, venta in ventas_por_nombre.items():
            if not nombre or nombre in nombres_vistos:
                continue
            nombres_vistos.add(nombre)
            await self.db.execute(
                text(
                    """
                    INSERT INTO productos
                        (nombre, familia_id, proveedor_principal_id, precio_venta, costo_unitario)
                    VALUES (
                        :nombre,
                        (SELECT id FROM familias WHERE nombre = :familia),
                        (SELECT id FROM proveedores WHERE nombre = :proveedor),
                        :precio,
                        :costo
                    )
                    ON CONFLICT (nombre) DO NOTHING
                    """
                ),
                {
                    "nombre": nombre,
                    "familia": semantica.familia_canonica(venta.get("familia")),
                    "proveedor": semantica.proveedor_canonico(venta.get("proveedor")),
                    "precio": float(venta.get("precio_promedio") or 0) or None,
                    "costo": (
                        float(venta["costo_promedio"])
                        if venta.get("costo_promedio") is not None
                        else None
                    ),
                },
            )
            productos_solo_ventas += 1

        await self.db.commit()

        return {
            "familias": len(familias_vistas),
            "proveedores": len(alias_por_canonico),
            "productos_desde_items": productos_sync,
            "productos_solo_en_ventas": productos_solo_ventas,
        }

    # ------------------------------------------------------------ calidad de datos

    async def get_calidad_datos(self) -> Dict[str, Any]:
        """Reporte de calidad de los maestros: qué contamina qué decisión.

        Cada problema indica la decisión que afecta — la calidad de datos
        no es un fin estético, es un prerrequisito de las Fases 2+.
        """
        problemas: List[Dict[str, Any]] = []

        consultas = {
            # Sin costo: margen incalculable → pricing y compras deciden a ciegas
            "sin_costo": (
                """
                SELECT nombre FROM productos
                WHERE activo AND costo_unitario IS NULL
                ORDER BY nombre LIMIT 500
                """,
                "producto",
                "Sin costo unitario: margen incalculable",
                "Contamina: márgenes, GMROI, sugerencias de compra, venta perdida",
            ),
            # Costo >= precio: o el costo está mal o se vende a pérdida
            "costo_mayor_precio": (
                """
                SELECT nombre FROM productos
                WHERE activo AND costo_unitario IS NOT NULL AND precio_venta IS NOT NULL
                  AND costo_unitario >= precio_venta
                ORDER BY nombre LIMIT 500
                """,
                "producto",
                "Costo unitario >= precio de venta",
                "Contamina: alertas de margen negativo (falsos positivos o venta real a pérdida)",
            ),
            "sin_familia": (
                """
                SELECT nombre FROM productos
                WHERE activo AND familia_id IS NULL
                ORDER BY nombre LIMIT 500
                """,
                "producto",
                "Sin familia asignada",
                "Contamina: análisis por categoría, surtido, GMROI por familia",
            ),
            "sin_proveedor": (
                """
                SELECT nombre FROM productos
                WHERE activo AND proveedor_principal_id IS NULL
                ORDER BY nombre LIMIT 500
                """,
                "producto",
                "Sin proveedor principal",
                "Contamina: órdenes de compra, scorecard de proveedores, riesgo de concentración",
            ),
        }

        resumen: Dict[str, int] = {}
        for tipo, (query, entidad, detalle, impacto) in consultas.items():
            result = await self.db.execute(text(query))
            filas = result.fetchall()
            resumen[tipo] = len(filas)
            for fila in filas[:50]:
                problemas.append(
                    {
                        "tipo": tipo,
                        "entidad": entidad,
                        "clave": fila[0],
                        "detalle": detalle,
                        "impacto": impacto,
                    }
                )

        total_result = await self.db.execute(
            text("SELECT COUNT(*) FROM productos WHERE activo")
        )
        total_productos = int(total_result.scalar() or 0)

        con_costo = total_productos - resumen.get("sin_costo", 0)
        salud_pct = round(con_costo / total_productos * 100, 1) if total_productos else None

        return {
            "total_productos": total_productos,
            "resumen": resumen,
            "salud_costos_pct": salud_pct,
            "problemas": problemas,
        }

    async def get_resumen(self) -> Dict[str, Any]:
        """Conteos básicos de los maestros para la UI."""
        out: Dict[str, Any] = {}
        for clave, query in {
            "productos": "SELECT COUNT(*) FROM productos WHERE activo",
            "familias": "SELECT COUNT(*) FROM familias",
            "proveedores": "SELECT COUNT(*) FROM proveedores WHERE activo",
            "tiendas": "SELECT COUNT(*) FROM tiendas WHERE activa",
        }.items():
            try:
                result = await self.db.execute(text(query))
                out[clave] = int(result.scalar() or 0)
            except Exception:
                await self.db.rollback()
                out[clave] = None
        return out

"""
Servicio de órdenes de compra (Fase 3).

Convierte las sugerencias de reabastecimiento en OC ejecutables con
restricciones reales del proveedor (múltiplo de empaque, pedido mínimo)
y ciclo de vida completo: borrador → aprobada → enviada → recibida.

Las fechas del ciclo (envío, promesa, recepción) son el insumo del
scorecard OTIF: sin OC registradas no hay medición de proveedores.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import semantica
from app.services.reabastecimiento import ReabastecimientoService

ESTADOS_OC = {"borrador", "aprobada", "enviada", "recibida_parcial", "recibida", "cancelada"}


class OrdenesCompraService:
    """Generación, aprobación, envío y recepción de órdenes de compra."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------- generación

    async def generar_borradores(self, usuario: Optional[str] = None) -> Dict[str, Any]:
        """Genera OC en borrador agrupando las sugerencias urgentes por proveedor.

        Reglas:
        - Solo urgencias 'quiebre' y 'pedir_ya' (lo demás es planificación).
        - Cantidad redondeada al múltiplo de empaque del producto.
        - Una OC por proveedor; los productos sin proveedor van a una OC
          especial 'SIN PROVEEDOR' que el comprador debe completar.
        - Si ya existe una OC en borrador para el proveedor, se reemplaza
          (los borradores son fotos de la necesidad, no compromisos).
        """
        sugerencias = await ReabastecimientoService(self.db).get_sugerencias()
        urgentes = [s for s in sugerencias if s["urgencia"] in ("quiebre", "pedir_ya")]
        if not urgentes:
            return {"ordenes_creadas": 0, "lineas": 0, "mensaje": "No hay productos urgentes"}

        # Datos de producto y proveedor necesarios para las restricciones
        result = await self.db.execute(
            text(
                """
                SELECT p.nombre, p.id as producto_id, p.unidades_por_empaque,
                       prov.id as proveedor_id, prov.nombre as proveedor_nombre,
                       prov.pedido_minimo, prov.lead_time_dias
                FROM productos p
                LEFT JOIN proveedores prov ON prov.id = p.proveedor_principal_id
                WHERE p.activo
                """
            )
        )
        info = {r[0]: dict(r._asdict()) for r in result.fetchall()}

        # Agrupar líneas por proveedor
        por_proveedor: Dict[Any, List[Dict[str, Any]]] = {}
        for s in urgentes:
            datos = info.get(s["nombre"])
            if not datos:
                continue
            cantidad = semantica.redondear_a_empaque(
                s["cantidad_sugerida"], datos["unidades_por_empaque"]
            )
            if cantidad <= 0:
                continue
            clave = datos["proveedor_id"]  # None agrupa los sin proveedor
            por_proveedor.setdefault(clave, []).append(
                {
                    "producto_id": datos["producto_id"],
                    "cantidad": cantidad,
                    "costo": (
                        (s["costo_estimado"] / s["cantidad_sugerida"])
                        if s["costo_estimado"] and s["cantidad_sugerida"]
                        else None
                    ),
                    "urgencia": s["urgencia"],
                    "demanda_diaria": s["demanda_diaria"],
                    "stock": s["stock_actual"],
                    "pedido_minimo": datos["pedido_minimo"],
                    "proveedor_nombre": datos["proveedor_nombre"],
                }
            )

        ordenes_creadas = 0
        total_lineas = 0
        for proveedor_id, lineas in por_proveedor.items():
            # Reemplazar el borrador anterior del mismo proveedor
            await self.db.execute(
                text(
                    """
                    DELETE FROM ordenes_compra
                    WHERE estado = 'borrador'
                      AND proveedor_id IS NOT DISTINCT FROM :prov
                    """
                ),
                {"prov": proveedor_id},
            )

            total = sum(
                (l["cantidad"] * l["costo"]) for l in lineas if l["costo"] is not None
            )
            minimo = lineas[0]["pedido_minimo"]
            cumple_minimo = (
                None if minimo is None else (total >= float(minimo))
            )

            numero = await self._siguiente_numero()
            result = await self.db.execute(
                text(
                    """
                    INSERT INTO ordenes_compra
                        (numero, proveedor_id, estado, total_costo,
                         cumple_pedido_minimo, usuario_creo)
                    VALUES (:numero, :prov, 'borrador', :total, :cumple, :usuario)
                    RETURNING id
                    """
                ),
                {
                    "numero": numero,
                    "prov": proveedor_id,
                    "total": round(total, 2) if total else None,
                    "cumple": cumple_minimo,
                    "usuario": usuario,
                },
            )
            orden_id = result.fetchone()[0]

            for l in lineas:
                await self.db.execute(
                    text(
                        """
                        INSERT INTO ordenes_compra_lineas
                            (orden_id, producto_id, cantidad_pedida, costo_unitario,
                             urgencia, demanda_diaria, stock_al_pedir)
                        VALUES (:orden, :producto, :cantidad, :costo,
                                :urgencia, :demanda, :stock)
                        """
                    ),
                    {
                        "orden": orden_id,
                        "producto": l["producto_id"],
                        "cantidad": l["cantidad"],
                        "costo": round(l["costo"], 2) if l["costo"] is not None else None,
                        "urgencia": l["urgencia"],
                        "demanda": l["demanda_diaria"],
                        "stock": l["stock"],
                    },
                )
                total_lineas += 1
            ordenes_creadas += 1

        await self.db.commit()
        return {"ordenes_creadas": ordenes_creadas, "lineas": total_lineas}

    async def _siguiente_numero(self) -> str:
        """Número consecutivo de OC: OC-AAAA-NNNN."""
        anio = date.today().year
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM ordenes_compra
                WHERE numero LIKE :patron
                """
            ),
            {"patron": f"OC-{anio}-%"},
        )
        consecutivo = int(result.scalar() or 0) + 1
        return f"OC-{anio}-{consecutivo:04d}"

    # ------------------------------------------------------------ ciclo de vida

    async def aprobar(self, orden_id: int, usuario: str) -> Dict[str, Any]:
        """Borrador → aprobada. Queda lista para enviarse al proveedor."""
        return await self._transicionar(
            orden_id,
            desde={"borrador"},
            hacia="aprobada",
            extra_sql="usuario_aprobo = :usuario, fecha_aprobacion = NOW()",
            extra_params={"usuario": usuario},
        )

    async def enviar(self, orden_id: int) -> Dict[str, Any]:
        """Aprobada → enviada. Fija la fecha promesa = hoy + lead time del proveedor.

        La fecha promesa es el compromiso contra el que se mide OTIF.
        """
        result = await self.db.execute(
            text(
                """
                SELECT o.estado, COALESCE(p.lead_time_dias, :lt) as lead_time
                FROM ordenes_compra o
                LEFT JOIN proveedores p ON p.id = o.proveedor_id
                WHERE o.id = :id
                """
            ),
            {"id": orden_id, "lt": semantica.LEAD_TIME_DEFAULT},
        )
        row = result.fetchone()
        if not row:
            raise ValueError("La orden no existe")
        if row[0] != "aprobada":
            raise ValueError(f"Solo se envía una orden aprobada (estado actual: {row[0]})")

        promesa = date.today() + timedelta(days=int(row[1]))
        await self.db.execute(
            text(
                """
                UPDATE ordenes_compra
                SET estado = 'enviada', fecha_envio = NOW(), fecha_promesa = :promesa
                WHERE id = :id
                """
            ),
            {"id": orden_id, "promesa": promesa},
        )
        await self.db.commit()
        return {"id": orden_id, "estado": "enviada", "fecha_promesa": str(promesa)}

    async def recibir(
        self,
        orden_id: int,
        recepciones: List[Dict[str, Any]],
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra la recepción física de una OC enviada.

        recepciones: [{producto_id, cantidad_recibida}]. Además de cerrar la
        OC (completa o parcial), registra los movimientos de inventario tipo
        'compra' en el libro perpetuo: la recepción ES el hecho auditable.
        """
        result = await self.db.execute(
            text("SELECT estado FROM ordenes_compra WHERE id = :id"), {"id": orden_id}
        )
        row = result.fetchone()
        if not row:
            raise ValueError("La orden no existe")
        if row[0] not in ("enviada", "recibida_parcial"):
            raise ValueError(f"Solo se recibe una orden enviada (estado actual: {row[0]})")

        recibido_por_producto = {
            int(r["producto_id"]): float(r["cantidad_recibida"]) for r in recepciones
        }

        result = await self.db.execute(
            text(
                """
                SELECT producto_id, cantidad_pedida, cantidad_recibida, costo_unitario
                FROM ordenes_compra_lineas WHERE orden_id = :id
                """
            ),
            {"id": orden_id},
        )
        lineas = result.fetchall()

        tienda = await self.db.execute(
            text("SELECT id FROM tiendas WHERE activa ORDER BY id LIMIT 1")
        )
        tienda_id = int(tienda.fetchone()[0])

        completa = True
        for l in lineas:
            producto_id = int(l[0])
            nueva = recibido_por_producto.get(producto_id)
            if nueva is None:
                if float(l[2] or 0) < float(l[1]):
                    completa = False
                continue

            incremento = nueva - float(l[2] or 0)
            await self.db.execute(
                text(
                    """
                    UPDATE ordenes_compra_lineas
                    SET cantidad_recibida = :nueva
                    WHERE orden_id = :orden AND producto_id = :producto
                    """
                ),
                {"nueva": nueva, "orden": orden_id, "producto": producto_id},
            )
            if incremento > 0:
                await self.db.execute(
                    text(
                        """
                        INSERT INTO movimientos_inventario
                            (producto_id, tienda_id, tipo, cantidad, costo_unitario,
                             referencia, usuario)
                        VALUES (:producto, :tienda, 'compra', :cantidad, :costo,
                                :referencia, :usuario)
                        """
                    ),
                    {
                        "producto": producto_id,
                        "tienda": tienda_id,
                        "cantidad": incremento,
                        "costo": l[3],
                        "referencia": f"OC id {orden_id}",
                        "usuario": usuario,
                    },
                )
            if nueva < float(l[1]):
                completa = False

        estado = "recibida" if completa else "recibida_parcial"
        await self.db.execute(
            text(
                """
                UPDATE ordenes_compra
                SET estado = :estado, fecha_recepcion = NOW()
                WHERE id = :id
                """
            ),
            {"estado": estado, "id": orden_id},
        )
        await self.db.commit()
        return {"id": orden_id, "estado": estado}

    async def cancelar(self, orden_id: int) -> Dict[str, Any]:
        """Cancela una OC no recibida."""
        return await self._transicionar(
            orden_id,
            desde={"borrador", "aprobada", "enviada"},
            hacia="cancelada",
        )

    async def _transicionar(
        self,
        orden_id: int,
        desde: set,
        hacia: str,
        extra_sql: str = "",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            text("SELECT estado FROM ordenes_compra WHERE id = :id"), {"id": orden_id}
        )
        row = result.fetchone()
        if not row:
            raise ValueError("La orden no existe")
        if row[0] not in desde:
            raise ValueError(
                f"Transición inválida: {row[0]} → {hacia} (se requiere {' o '.join(sorted(desde))})"
            )
        set_clause = f"estado = :hacia{', ' + extra_sql if extra_sql else ''}"
        params: Dict[str, Any] = {"hacia": hacia, "id": orden_id}
        params.update(extra_params or {})
        await self.db.execute(
            text(f"UPDATE ordenes_compra SET {set_clause} WHERE id = :id"), params
        )
        await self.db.commit()
        return {"id": orden_id, "estado": hacia}

    # --------------------------------------------------------------- lectura

    async def get_ordenes(
        self, estado: Optional[str] = None, limite: int = 50
    ) -> List[Dict[str, Any]]:
        """Lista de OC con proveedor y totales, más recientes primero."""
        query = """
            SELECT o.id, o.numero, o.estado, o.total_costo, o.cumple_pedido_minimo,
                   o.created_at, o.fecha_envio, o.fecha_promesa, o.fecha_recepcion,
                   p.nombre as proveedor, p.pedido_minimo,
                   COUNT(l.id) as num_lineas,
                   SUM(l.cantidad_pedida) as unidades_pedidas,
                   SUM(l.cantidad_recibida) as unidades_recibidas
            FROM ordenes_compra o
            LEFT JOIN proveedores p ON p.id = o.proveedor_id
            LEFT JOIN ordenes_compra_lineas l ON l.orden_id = o.id
            WHERE (CAST(:estado AS TEXT) IS NULL OR o.estado = CAST(:estado AS TEXT))
            GROUP BY o.id, p.nombre, p.pedido_minimo
            ORDER BY o.created_at DESC
            LIMIT :limite
        """
        result = await self.db.execute(text(query), {"estado": estado, "limite": limite})
        ordenes = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            for k in ("total_costo", "pedido_minimo", "unidades_pedidas", "unidades_recibidas"):
                fila[k] = float(fila[k]) if fila[k] is not None else None
            for k in ("created_at", "fecha_envio", "fecha_recepcion"):
                fila[k] = str(fila[k]) if fila[k] else None
            fila["fecha_promesa"] = str(fila["fecha_promesa"]) if fila["fecha_promesa"] else None
            ordenes.append(fila)
        return ordenes

    async def get_detalle(self, orden_id: int) -> Dict[str, Any]:
        """Cabecera + líneas de una OC."""
        ordenes = await self.get_ordenes(estado=None, limite=10000)
        cabecera = next((o for o in ordenes if o["id"] == orden_id), None)
        if not cabecera:
            raise ValueError("La orden no existe")

        result = await self.db.execute(
            text(
                """
                SELECT l.producto_id, p.nombre, l.cantidad_pedida, l.cantidad_recibida,
                       l.costo_unitario, l.urgencia, l.demanda_diaria, l.stock_al_pedir
                FROM ordenes_compra_lineas l
                JOIN productos p ON p.id = l.producto_id
                WHERE l.orden_id = :id
                ORDER BY l.urgencia ASC, p.nombre
                """
            ),
            {"id": orden_id},
        )
        lineas = []
        for r in result.fetchall():
            fila = dict(r._asdict())
            for k in ("cantidad_pedida", "cantidad_recibida", "costo_unitario",
                      "demanda_diaria", "stock_al_pedir"):
                fila[k] = float(fila[k]) if fila[k] is not None else None
            lineas.append(fila)
        cabecera["lineas"] = lineas
        return cabecera

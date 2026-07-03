"""Fase 1 — Fundaciones: maestros únicos, inventario perpetuo, conteos y decisiones.

Crea:
- tiendas: maestro de tiendas (hoy 1, diseñado para N)
- familias: jerarquía de categorías (auto-referenciada)
- proveedores: maestro único con lead time y plazo de pago
- productos: maestro único de productos (SKU), vinculado a familia y proveedor
- movimientos_inventario: libro de inventario perpetuo (toda entrada/salida)
- conteos_ciclicos: conteos físicos con discrepancia y exactitud
- decisiones: bandeja de alertas/acciones (causa + acción + dinero + dueño + SLA)

Revision ID: 002
Revises: 001
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ tiendas
    op.create_table(
        "tiendas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(20), unique=True, nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("ciudad", sa.String(100), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # ----------------------------------------------------------------- familias
    op.create_table(
        "familias",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(255), unique=True, nullable=False),
        sa.Column(
            "padre_id",
            sa.Integer(),
            sa.ForeignKey("familias.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -------------------------------------------------------------- proveedores
    op.create_table(
        "proveedores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Nombre canónico (normalizado con semantica.proveedor_canonico)
        sa.Column("nombre", sa.String(255), unique=True, nullable=False),
        # Alias crudos vistos en los datos de origen, separados por " | "
        sa.Column("alias", sa.Text(), nullable=True),
        sa.Column("lead_time_dias", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("dias_plazo_pago", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # ---------------------------------------------------------------- productos
    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Código de la fuente (columna Codigo de items); único cuando existe
        sa.Column("codigo_fuente", sa.String(50), nullable=True, index=True),
        # Nombre canónico normalizado — clave de conciliación con ventas/items
        sa.Column("nombre", sa.String(500), unique=True, nullable=False),
        sa.Column("codigo_barras", sa.String(100), nullable=True, index=True),
        sa.Column(
            "familia_id",
            sa.Integer(),
            sa.ForeignKey("familias.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "proveedor_principal_id",
            sa.Integer(),
            sa.ForeignKey("proveedores.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("precio_venta", sa.Numeric(14, 2), nullable=True),
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True),
        sa.Column("gama", sa.String(20), nullable=True),
        sa.Column("fecha_ingreso", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=True,
        ),
    )

    # ------------------------------------------------- movimientos_inventario
    op.create_table(
        "movimientos_inventario",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tienda_id",
            sa.Integer(),
            sa.ForeignKey("tiendas.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # venta | compra | ajuste_conteo | merma | devolucion | transferencia_in | transferencia_out | carga_inicial
        sa.Column("tipo", sa.String(30), nullable=False, index=True),
        # Positiva = entra stock, negativa = sale stock
        sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True),
        # Referencia al documento de origen (factura, conteo, OC…)
        sa.Column("referencia", sa.String(255), nullable=True),
        sa.Column("usuario", sa.String(100), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_movimientos_producto_fecha",
        "movimientos_inventario",
        ["producto_id", "fecha"],
    )

    # ---------------------------------------------------------- conteos_ciclicos
    op.create_table(
        "conteos_ciclicos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tienda_id",
            sa.Integer(),
            sa.ForeignKey("tiendas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stock_sistema", sa.Numeric(14, 3), nullable=False),
        sa.Column("stock_fisico", sa.Numeric(14, 3), nullable=False),
        # Redundantes pero congelados al momento del conteo (el costo cambia)
        sa.Column("diferencia", sa.Numeric(14, 3), nullable=False),
        sa.Column("valor_diferencia", sa.Numeric(14, 2), nullable=True),
        sa.Column("es_exacto", sa.Boolean(), nullable=False),
        sa.Column("motivo", sa.String(255), nullable=True),
        sa.Column("usuario", sa.String(100), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---------------------------------------------------------------- decisiones
    op.create_table(
        "decisiones",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        # Código estable del tipo de alerta (p.ej. "margen_negativo", "quiebre_inminente")
        sa.Column("codigo_alerta", sa.String(60), nullable=False, index=True),
        # P1 crítica (horas) | P2 alta (hoy) | P3 media (semana) | P4 estructural (comité)
        sa.Column("prioridad", sa.String(2), nullable=False, index=True),
        sa.Column("titulo", sa.String(500), nullable=False),
        sa.Column("que_pasa", sa.Text(), nullable=False),
        sa.Column("por_que", sa.Text(), nullable=False),
        sa.Column("que_hacer", sa.Text(), nullable=False),
        sa.Column("impacto_dinero", sa.Numeric(16, 2), nullable=True),
        # Rol responsable: comprador | pricing | gerente_tienda | finanzas | admin
        sa.Column("dueno", sa.String(50), nullable=False, index=True),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=True),
        # pendiente | aprobada | rechazada | resuelta | expirada
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente", index=True),
        sa.Column("resultado_nota", sa.Text(), nullable=True),
        sa.Column("resuelto_por", sa.String(100), nullable=True),
        sa.Column("resuelto_en", sa.DateTime(timezone=True), nullable=True),
        # Payload con los datos de soporte (productos afectados, cifras)
        sa.Column("datos", sa.JSON(), nullable=True),
        # Clave de deduplicación: misma clave + estado pendiente = no se duplica
        sa.Column("clave_dedup", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_decisiones_dedup_pendiente",
        "decisiones",
        ["clave_dedup", "estado"],
    )

    # Tienda por defecto: la operación actual es una sola bodega "Principal"
    op.execute(
        "INSERT INTO tiendas (codigo, nombre) VALUES ('T001', 'Principal')"
    )


def downgrade() -> None:
    op.drop_table("decisiones")
    op.drop_table("conteos_ciclicos")
    op.drop_index("ix_movimientos_producto_fecha", table_name="movimientos_inventario")
    op.drop_table("movimientos_inventario")
    op.drop_table("productos")
    op.drop_table("proveedores")
    op.drop_table("familias")
    op.drop_table("tiendas")

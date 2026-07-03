"""Fase 3 — Compras: órdenes de compra con restricciones, scorecard OTIF y merma por causa.

Crea:
- ordenes_compra: cabecera con ciclo de vida (borrador → aprobada → enviada → recibida)
  y fechas que alimentan el scorecard OTIF del proveedor
- ordenes_compra_lineas: detalle pedido vs recibido por producto
- mermas: registro de merma clasificada por causa (cada causa tiene tratamiento distinto)

Extiende:
- proveedores.pedido_minimo: restricción real de compra (monto mínimo por OC)
- productos.unidades_por_empaque: múltiplo de empaque para redondear pedidos

Revision ID: 004
Revises: 003
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------- restricciones de compra
    op.add_column(
        "proveedores",
        sa.Column("pedido_minimo", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "productos",
        sa.Column("unidades_por_empaque", sa.Integer(), nullable=False, server_default="1"),
    )

    # ------------------------------------------------------------ ordenes_compra
    op.create_table(
        "ordenes_compra",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("numero", sa.String(30), unique=True, nullable=False),
        sa.Column(
            "proveedor_id",
            sa.Integer(),
            sa.ForeignKey("proveedores.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        # borrador | aprobada | enviada | recibida_parcial | recibida | cancelada
        sa.Column("estado", sa.String(20), nullable=False, server_default="borrador", index=True),
        sa.Column("total_costo", sa.Numeric(16, 2), nullable=True),
        # Restricción evaluada al generar: si el total no llega al pedido mínimo
        sa.Column("cumple_pedido_minimo", sa.Boolean(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("usuario_creo", sa.String(100), nullable=True),
        sa.Column("usuario_aprobo", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("fecha_aprobacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_envio", sa.DateTime(timezone=True), nullable=True),
        # Fecha comprometida de entrega = envío + lead time del proveedor
        sa.Column("fecha_promesa", sa.Date(), nullable=True),
        sa.Column("fecha_recepcion", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------- ordenes_compra_lineas
    op.create_table(
        "ordenes_compra_lineas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "orden_id",
            sa.BigInteger(),
            sa.ForeignKey("ordenes_compra.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("cantidad_pedida", sa.Numeric(14, 3), nullable=False),
        sa.Column("cantidad_recibida", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True),
        # Contexto congelado al crear la línea (justifica la cantidad sugerida)
        sa.Column("urgencia", sa.String(20), nullable=True),
        sa.Column("demanda_diaria", sa.Numeric(14, 3), nullable=True),
        sa.Column("stock_al_pedir", sa.Numeric(14, 3), nullable=True),
    )

    # ---------------------------------------------------------------- mermas
    op.create_table(
        "mermas",
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
        # vencimiento | dano | robo_externo | robo_interno | error_administrativo
        sa.Column("causa", sa.String(30), nullable=False, index=True),
        sa.Column("cantidad", sa.Numeric(14, 3), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor", sa.Numeric(16, 2), nullable=True),
        sa.Column("nota", sa.String(500), nullable=True),
        sa.Column("usuario", sa.String(100), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mermas_fecha", "mermas", ["fecha"])


def downgrade() -> None:
    op.drop_index("ix_mermas_fecha", table_name="mermas")
    op.drop_table("mermas")
    op.drop_table("ordenes_compra_lineas")
    op.drop_table("ordenes_compra")
    op.drop_column("productos", "unidades_por_empaque")
    op.drop_column("proveedores", "pedido_minimo")

"""Fase 4 — Precio, surtido y diagnóstico causal (operativa).

Crea:
- precios_historicos: serie temporal de precio/costo por producto-día
- recomendaciones_precio: markdowns y cambios de precio sugeridos
- decisiones_surtido: revisión de surtido (potenciar/mantener/reducir/eliminar)

Extiende:
- productos.rol_surtido: kvi | regular | complementario (opcional)

Revision ID: 005
Revises: 004
Create Date: 2026-07-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "productos",
        sa.Column("rol_surtido", sa.String(20), nullable=True),
    )

    op.create_table(
        "precios_historicos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("precio_venta", sa.Numeric(14, 2), nullable=True),
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True),
        sa.Column("fuente", sa.String(30), nullable=False, server_default="ventas"),
        sa.UniqueConstraint("producto_id", "fecha", name="uq_precios_producto_fecha"),
    )
    op.create_index("ix_precios_historicos_producto_fecha", "precios_historicos", ["producto_id", "fecha"])

    op.create_table(
        "recomendaciones_precio",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # markdown | subida | revision
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("precio_actual", sa.Numeric(14, 2), nullable=True),
        sa.Column("precio_sugerido", sa.Numeric(14, 2), nullable=True),
        sa.Column("elasticidad", sa.Numeric(8, 4), nullable=True),
        sa.Column("confianza", sa.String(10), nullable=True),
        sa.Column("impacto_estimado", sa.Numeric(16, 2), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        # pendiente | aplicada | descartada
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente", index=True),
        sa.Column("clave_dedup", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_recomendaciones_dedup", "recomendaciones_precio", ["clave_dedup", "estado"])

    op.create_table(
        "decisiones_surtido",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # potenciar | mantener | reducir | eliminar
        sa.Column("accion", sa.String(20), nullable=False),
        sa.Column("gmroi", sa.Numeric(10, 4), nullable=True),
        sa.Column("velocidad_relativa", sa.Numeric(10, 4), nullable=True),
        sa.Column("impacto_estimado", sa.Numeric(16, 2), nullable=True),
        sa.Column("transferencia_proxy_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente", index=True),
        sa.Column("clave_dedup", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_decisiones_surtido_dedup", "decisiones_surtido", ["clave_dedup", "estado"])


def downgrade() -> None:
    op.drop_index("ix_decisiones_surtido_dedup", table_name="decisiones_surtido")
    op.drop_table("decisiones_surtido")
    op.drop_index("ix_recomendaciones_dedup", table_name="recomendaciones_precio")
    op.drop_table("recomendaciones_precio")
    op.drop_index("ix_precios_historicos_producto_fecha", table_name="precios_historicos")
    op.drop_table("precios_historicos")
    op.drop_column("productos", "rol_surtido")

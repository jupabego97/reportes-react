"""Fase 2 — Forecast y disponibilidad.

Crea:
- ventas_diarias_historicas: historial diario persistente por producto.
  La tabla fuente (reportes_ventas_30dias) es una ventana rodante; sin un
  historial que se acumule no hay estacionalidad ni forecast serio.
- forecasts: pronósticos probabilísticos persistidos (P10/P50/P90) para
  medir la precisión real contra lo que efectivamente pasó.
- forecast_backtests: bitácora de cada backtest (champion vs baseline)
  para gobernanza de modelos.

Revision ID: 003
Revises: 002
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ventas_diarias_historicas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("unidades", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("venta_neta", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("precio_promedio", sa.Numeric(14, 2), nullable=True),
        sa.Column("costo_promedio", sa.Numeric(14, 2), nullable=True),
        sa.UniqueConstraint("producto_id", "fecha", name="uq_ventas_hist_producto_fecha"),
    )
    op.create_index(
        "ix_ventas_hist_producto_fecha",
        "ventas_diarias_historicas",
        ["producto_id", "fecha"],
    )

    op.create_table(
        "forecasts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha_objetivo", sa.Date(), nullable=False),
        # Unidades pronosticadas para ese día
        sa.Column("p10", sa.Numeric(14, 3), nullable=False),
        sa.Column("p50", sa.Numeric(14, 3), nullable=False),
        sa.Column("p90", sa.Numeric(14, 3), nullable=False),
        # intermitente_tsb | estacional_dow | media_movil
        sa.Column("modelo", sa.String(40), nullable=False),
        sa.Column(
            "generado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_forecasts_producto_fecha", "forecasts", ["producto_id", "fecha_objetivo"]
    )

    op.create_table(
        "forecast_backtests",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "ejecutado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("dias_holdout", sa.Integer(), nullable=False),
        sa.Column("productos_evaluados", sa.Integer(), nullable=False),
        # Métricas del modelo nuevo (champion) y del método de referencia (baseline)
        sa.Column("wmape_champion", sa.Numeric(8, 4), nullable=True),
        sa.Column("wmape_baseline", sa.Numeric(8, 4), nullable=True),
        sa.Column("sesgo_champion_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("sesgo_baseline_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("detalle", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("forecast_backtests")
    op.drop_index("ix_forecasts_producto_fecha", table_name="forecasts")
    op.drop_table("forecasts")
    op.drop_index("ix_ventas_hist_producto_fecha", table_name="ventas_diarias_historicas")
    op.drop_table("ventas_diarias_historicas")

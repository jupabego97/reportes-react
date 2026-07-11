"""Fase 5 — Autonomía y control ejecutivo (operativa).

Crea:
- jobs_ejecucion: log de corridas del orquestador nocturno
- politicas_autonomia: umbrales por tipo de acción (Nivel 1 auto)
- aprendizaje_decisiones: snapshot al resolver para métricas de aceptación

Revision ID: 006
Revises: 005
Create Date: 2026-07-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs_ejecucion",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job", sa.String(60), nullable=False, index=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="corriendo"),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "iniciado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finalizado_en", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "politicas_autonomia",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # codigo de alerta o 'oc_borrador'
        sa.Column("codigo", sa.String(60), unique=True, nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
        # Impacto máximo en dinero para auto-ejecutar (Nivel 1)
        sa.Column("auto_max_impacto", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("habilitado", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "aprendizaje_decisiones",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.BigInteger(), nullable=True),
        sa.Column("codigo_alerta", sa.String(60), nullable=False, index=True),
        sa.Column("prioridad", sa.String(2), nullable=True),
        sa.Column("estado_final", sa.String(20), nullable=False),
        sa.Column("impacto_dinero", sa.Numeric(16, 2), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("usuario", sa.String(100), nullable=True),
        sa.Column("fue_auto", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Seed de políticas Nivel 1 (conservadoras)
    op.execute(
        """
        INSERT INTO politicas_autonomia (codigo, descripcion, auto_max_impacto, habilitado)
        VALUES
            ('oc_borrador', 'Auto-aprobar OC en borrador bajo umbral', 500000, true),
            ('inventario_muerto', 'Auto-marcar inventario muerto como revisado bajo umbral', 200000, true),
            ('markdown_recomendado', 'Auto-aceptar plan de markdown bajo umbral', 300000, true),
            ('exactitud_baja', 'Auto-archivar alerta de exactitud bajo umbral', 0, false)
        """
    )


def downgrade() -> None:
    op.drop_table("aprendizaje_decisiones")
    op.drop_table("politicas_autonomia")
    op.drop_table("jobs_ejecucion")

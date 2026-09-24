"""referans durumu onaylandi -> yanitlandi

Revision ID: 2d69c67aa540
Revises: bbfac2425ba7
Create Date: 2026-09-24 11:20:35.779555
"""
from collections.abc import Sequence

import pgvector.sqlalchemy  # noqa: F401  (Vector kolonları için)
import sqlalchemy as sa
from alembic import op


revision: str = '2d69c67aa540'
down_revision: str | None = 'bbfac2425ba7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Durum adı değişti: "onaylandi" olumsuz bir referansı yanlış temsil
    # ediyordu (bkz. docs/data-schema.md § Tasarım Kararları).
    op.execute("UPDATE referans_istegi SET durum = 'yanitlandi' WHERE durum = 'onaylandi'")


def downgrade() -> None:
    op.execute("UPDATE referans_istegi SET durum = 'onaylandi' WHERE durum = 'yanitlandi'")

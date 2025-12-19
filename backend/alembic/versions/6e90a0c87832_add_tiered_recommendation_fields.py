"""add tiered recommendation fields

Revision ID: 6e90a0c87832
Revises: r1234567ghij
Create Date: 2025-12-19 15:10:02.389051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e90a0c87832'
down_revision: Union[str, None] = 'r1234567ghij'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to eval_runbooks table
    op.add_column(
        "eval_runbooks",
        sa.Column("recommendation_tier", sa.String(20), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("quality_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("strategic_fit_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("combined_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("price_position", sa.String(20), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("suggested_offer", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("recommendation_reasoning", sa.String(500), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column(
            "strategic_floor_applied",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column(
            "quality_floor_applied",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column(
            "scoring_version",
            sa.String(20),
            nullable=False,
            server_default="2025-01",
        ),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column(
            "score_source",
            sa.String(20),
            nullable=False,
            server_default="eval_runbook",
        ),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("last_scored_price", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("napoleon_recommendation", sa.String(20), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("napoleon_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("napoleon_analyzed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_runbooks", "napoleon_analyzed_at")
    op.drop_column("eval_runbooks", "napoleon_reasoning")
    op.drop_column("eval_runbooks", "napoleon_recommendation")
    op.drop_column("eval_runbooks", "last_scored_price")
    op.drop_column("eval_runbooks", "score_source")
    op.drop_column("eval_runbooks", "scoring_version")
    op.drop_column("eval_runbooks", "quality_floor_applied")
    op.drop_column("eval_runbooks", "strategic_floor_applied")
    op.drop_column("eval_runbooks", "recommendation_reasoning")
    op.drop_column("eval_runbooks", "suggested_offer")
    op.drop_column("eval_runbooks", "price_position")
    op.drop_column("eval_runbooks", "combined_score")
    op.drop_column("eval_runbooks", "strategic_fit_score")
    op.drop_column("eval_runbooks", "quality_score")
    op.drop_column("eval_runbooks", "recommendation_tier")

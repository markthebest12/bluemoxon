"""Add eval_runbooks and eval_price_history tables.

Revision ID: m5678901qrst
Revises: l4567890mnop
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa

revision = "m5678901qrst"
down_revision = "l4567890mnop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runbooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.String(20), nullable=False),
        sa.Column("original_asking_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("current_asking_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_code", sa.String(100), nullable=True),
        sa.Column("price_notes", sa.Text(), nullable=True),
        sa.Column("fmv_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("fmv_high", sa.Numeric(10, 2), nullable=True),
        sa.Column("recommended_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("ebay_comparables", sa.JSON(), nullable=True),
        sa.Column("abebooks_comparables", sa.JSON(), nullable=True),
        sa.Column("condition_grade", sa.String(20), nullable=True),
        sa.Column("condition_positives", sa.JSON(), nullable=True),
        sa.Column("condition_negatives", sa.JSON(), nullable=True),
        sa.Column("critical_issues", sa.JSON(), nullable=True),
        sa.Column("analysis_narrative", sa.Text(), nullable=True),
        sa.Column("item_identification", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id"),
    )
    op.create_index("ix_eval_runbooks_book_id", "eval_runbooks", ["book_id"])

    op.create_table(
        "eval_price_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("eval_runbook_id", sa.Integer(), nullable=False),
        sa.Column("previous_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_code", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("score_before", sa.Integer(), nullable=True),
        sa.Column("score_after", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["eval_runbook_id"], ["eval_runbooks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_price_history_runbook_id", "eval_price_history", ["eval_runbook_id"])


def downgrade() -> None:
    op.drop_index("ix_eval_price_history_runbook_id", table_name="eval_price_history")
    op.drop_table("eval_price_history")
    op.drop_index("ix_eval_runbooks_book_id", table_name="eval_runbooks")
    op.drop_table("eval_runbooks")

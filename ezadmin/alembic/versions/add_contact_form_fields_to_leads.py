"""add contact form fields to leads

Revision ID: d4c8e9f1a2b3
Revises: 021450f5732b
Create Date: 2025-10-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4c8e9f1a2b3'
down_revision: Union[str, None] = '021450f5732b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new fields to leads table
    op.add_column('leads', sa.Column('ip_address', sa.String(length=50), nullable=True))
    op.add_column('leads', sa.Column('user_agent', sa.String(length=500), nullable=True))
    op.add_column('leads', sa.Column('raw_form_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('leads', 'raw_form_data')
    op.drop_column('leads', 'user_agent')
    op.drop_column('leads', 'ip_address')


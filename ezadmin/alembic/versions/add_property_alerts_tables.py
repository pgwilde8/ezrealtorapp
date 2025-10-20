"""add property alerts tables

Revision ID: e5f9d2a3b4c5
Revises: d4c8e9f1a2b3
Create Date: 2025-10-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f9d2a3b4c5'
down_revision: Union[str, None] = 'd4c8e9f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create property_alerts table
    op.create_table('property_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('square_feet', sa.Integer(), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=False),
        sa.Column('bathrooms', sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('mls_link', sa.String(length=500), nullable=True),
        sa.Column('is_hot', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_sent_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('sms_sent_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('click_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_property_alerts_agent_id', 'property_alerts', ['agent_id'])
    op.create_index('ix_property_alerts_created_at', 'property_alerts', ['created_at'])
    op.create_index('ix_property_alerts_id', 'property_alerts', ['id'])
    
    # Create property_images table
    op.create_table('property_images',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('property_id', sa.UUID(), nullable=False),
        sa.Column('image_url', sa.String(length=1000), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=1000), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['property_alerts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_property_images_id', 'property_images', ['id'])
    op.create_index('ix_property_images_property_id', 'property_images', ['property_id'])


def downgrade() -> None:
    op.drop_index('ix_property_images_property_id', table_name='property_images')
    op.drop_index('ix_property_images_id', table_name='property_images')
    op.drop_table('property_images')
    
    op.drop_index('ix_property_alerts_id', table_name='property_alerts')
    op.drop_index('ix_property_alerts_created_at', table_name='property_alerts')
    op.drop_index('ix_property_alerts_agent_id', table_name='property_alerts')
    op.drop_table('property_alerts')


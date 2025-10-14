"""update_for_concierge_pricing

Revision ID: 021450f5732b
Revises: cb8a7703cd53
Create Date: 2025-10-14 17:55:34.806906

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021450f5732b'
down_revision = 'cb8a7703cd53'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create new plan_catalog table
    op.create_table('plan_catalog',
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('price_month_usd', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_page_views', sa.Integer(), nullable=False),
        sa.Column('max_lead_events', sa.Integer(), nullable=False),
        sa.Column('max_ai_tokens', sa.Integer(), nullable=False),
        sa.Column('max_emails', sa.Integer(), nullable=False),
        sa.Column('max_sms', sa.Integer(), nullable=False),
        sa.Column('max_voice_minutes', sa.Integer(), nullable=False),
        sa.Column('daily_email_cap', sa.Integer(), nullable=True),
        sa.Column('daily_sms_cap', sa.Integer(), nullable=True),
        sa.Column('daily_voice_cap', sa.Integer(), nullable=True),
        sa.Column('overage_ai_per_1k_tokens', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('overage_email_each', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('overage_sms_each', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('overage_voice_per_minute', sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column('default_spend_cap_usd', sa.Integer(), nullable=False),
        sa.Column('is_trial', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_overages', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('code')
    )

    # Create new agent_usage table
    op.create_table('agent_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('month_year', sa.Text(), nullable=False),
        sa.Column('plan_code', sa.Text(), nullable=False),
        sa.Column('page_views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lead_events', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('emails_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sms_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('voice_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_date', sa.Date(), nullable=True, server_default=sa.text('CURRENT_DATE')),
        sa.Column('daily_emails', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_sms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_voice', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_spend_usd', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'month_year')
    )
    op.create_index('ix_agent_usage_agent_month', 'agent_usage', ['agent_id', 'month_year'])

    # Create pending_actions table
    op.create_table('pending_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.Text(), nullable=False),
        sa.Column('action_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pending_actions_agent', 'pending_actions', ['agent_id', 'created_at'])

    # Add new columns to agents table
    op.add_column('agents', sa.Column('trial_started_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('agents', sa.Column('trial_ends_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('agents', sa.Column('overages_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('agents', sa.Column('spend_cap_usd', sa.Integer(), nullable=True, server_default='50'))

    # Insert plan configurations
    op.execute("""
        INSERT INTO plan_catalog VALUES
        ('trial', 'Free Trial', 0.00, 
         2000, 50, 150000, 100, 50, 15,
         30, 15, 5,
         NULL, NULL, NULL, NULL,
         0, TRUE, FALSE, NOW()),
        ('concierge', 'Concierge (2 Pages)', 97.00,
         5000, 300, 1500000, 1000, 300, 60,
         NULL, NULL, NULL,
         4.0, 2.0, 15.0, 30.0,
         50, FALSE, TRUE, NOW()),
        ('concierge_plus', 'Concierge Plus (4 Pages)', 249.00,
         20000, 1500, 6000000, 5000, 1500, 300,
         NULL, NULL, NULL,
         3.6, 1.8, 13.5, 27.0,
         250, FALSE, TRUE, NOW())
    """)

    # Initialize trial dates for existing agents
    op.execute("""
        UPDATE agents SET 
          trial_started_at = created_at,
          trial_ends_at = created_at + INTERVAL '14 days',
          plan_tier = 'trial'
        WHERE trial_started_at IS NULL
    """)

def downgrade() -> None:
    op.drop_table('pending_actions')
    op.drop_table('agent_usage')
    op.drop_table('plan_catalog')
    op.drop_column('agents', 'spend_cap_usd')
    op.drop_column('agents', 'overages_enabled')
    op.drop_column('agents', 'trial_ends_at')
    op.drop_column('agents', 'trial_started_at')
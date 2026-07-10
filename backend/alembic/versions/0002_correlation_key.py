"""add correlation_key to events"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE events ADD COLUMN correlation_key VARCHAR(128);

        UPDATE events
        SET correlation_key = COALESCE(
            NULLIF(session_id, ''),
            NULLIF(visitor_id, '')
        )
        WHERE correlation_key IS NULL;

        CREATE INDEX idx_events_site_correlation
            ON events (site_id, correlation_key, occurred_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_events_site_correlation;
        ALTER TABLE events DROP COLUMN IF EXISTS correlation_key;
    """)

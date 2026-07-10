"""add visitor_hash for browser fingerprint identity"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE events ADD COLUMN visitor_hash VARCHAR(64);

        CREATE INDEX idx_events_site_visitor_hash
            ON events (site_id, visitor_hash, occurred_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_events_site_visitor_hash;
        ALTER TABLE events DROP COLUMN IF EXISTS visitor_hash;
    """)

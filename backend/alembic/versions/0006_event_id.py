"""add event_id for collect replay protection"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE events ADD COLUMN event_id VARCHAR(36);

        CREATE UNIQUE INDEX idx_events_site_event_id
            ON events (site_id, event_id)
            WHERE event_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_events_site_event_id;
        ALTER TABLE events DROP COLUMN IF EXISTS event_id;
    """)

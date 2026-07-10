"""init schema"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE sites (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            site_key VARCHAR(64) NOT NULL UNIQUE,
            allowed_domains TEXT[] NOT NULL DEFAULT '{}',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
            type VARCHAR(16) NOT NULL,
            path VARCHAR(512) NOT NULL DEFAULT '',
            title VARCHAR(512) NOT NULL DEFAULT '',
            track_id VARCHAR(128),
            referrer VARCHAR(1024),
            visitor_id VARCHAR(64),
            session_id VARCHAR(64),
            ip_hash VARCHAR(64),
            country VARCHAR(8),
            region VARCHAR(64),
            city VARCHAR(128),
            user_agent VARCHAR(512),
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_events_site_occurred ON events (site_id, occurred_at DESC);
        CREATE INDEX idx_events_site_type_occurred ON events (site_id, type, occurred_at DESC);
        CREATE INDEX idx_events_site_track_id ON events (site_id, track_id);
        CREATE INDEX idx_sites_site_key ON sites (site_key);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS sites;
        DROP TABLE IF EXISTS users;
    """)

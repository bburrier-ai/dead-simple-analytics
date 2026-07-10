"""normalize legacy admin@example.com username to admin"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE users
        SET username = 'admin'
        WHERE username = 'admin@example.com'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE users
        SET username = 'admin@example.com'
        WHERE username = 'admin'
    """)

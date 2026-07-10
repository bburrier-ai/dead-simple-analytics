"""rename users.email to username"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users RENAME COLUMN email TO username")


def downgrade() -> None:
    op.execute("ALTER TABLE users RENAME COLUMN username TO email")

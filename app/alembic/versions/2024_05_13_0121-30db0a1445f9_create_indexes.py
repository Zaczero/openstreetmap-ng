"""Create indexes

Revision ID: 30db0a1445f9
Revises: dec64c0631e1
Create Date: 2024-05-13 01:21:12.804562+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '30db0a1445f9'
down_revision: str | None = 'dec64c0631e1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('element_members_idx', 'element', ['members'], unique=False, postgresql_using='gin')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('element_members_idx', table_name='element', postgresql_using='gin')
    # ### end Alembic commands ###
"""修改用户表昵称字段名

Revision ID: 6bc0eb9a11d9
Revises: 39dc760cc66f
Create Date: 2025-04-14 20:50:08.209542

"""

# revision identifiers, used by Alembic.
revision = '6bc0eb9a11d9'
down_revision = '39dc760cc66f'

from alembic import op
from sqlalchemy.dialects import mysql


def upgrade():
    op.alter_column('users', 'name', new_column_name='nickname', existing_type=mysql.VARCHAR(length=64))
    # ### end Alembic commands ###

def downgrade():
    op.alter_column('users', 'nickname', new_column_name='name', existing_type=mysql.VARCHAR(length=64))
    # ### end Alembic commands ###

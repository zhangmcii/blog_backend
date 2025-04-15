"""增加通知类型AT

Revision ID: 26f63d68afbb
Revises: 6bc0eb9a11d9
Create Date: 2025-04-15 20:45:47.668172

"""

# revision identifiers, used by Alembic.
revision = '26f63d68afbb'
down_revision = '6bc0eb9a11d9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # 修改列的枚举类型定义，添加新的枚举值
    op.alter_column('notifications', 'type',
                    type_=sa.Enum('COMMENT', 'REPLY', 'LIKE', 'CHAT', 'AT'),
                    existing_type=sa.Enum('COMMENT', 'REPLY', 'LIKE', 'CHAT'),
                    existing_nullable=True)


def downgrade():
    # 恢复列的枚举类型定义，移除新的枚举值
    op.alter_column('notifications', 'type',
                    type_=sa.Enum('COMMENT', 'REPLY', 'LIKE', 'CHAT'),
                    existing_type=sa.Enum('COMMENT', 'REPLY', 'LIKE', 'CHAT', 'AT'),
                    existing_nullable=True)

"""修改通知表type枚举

Revision ID: 39dc760cc66f
Revises: f06b1721d987
Create Date: 2025-04-13 23:27:39.997865

"""

# revision identifiers, used by Alembic.
revision = '39dc760cc66f'
down_revision = 'f06b1721d987'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # 修改列的枚举类型定义，添加新的枚举值
    op.alter_column('notifications', 'type',
                    type_=sa.Enum('COMMENT', 'REPLY', 'LIKE', 'CHAT'),
                    existing_type=sa.Enum('COMMENT', 'REPLY', 'LIKE'),
                    existing_nullable=True)


def downgrade():
    # 恢复列的枚举类型定义，移除新的枚举值
    op.alter_column('notifications', 'type',
                    type_=sa.Enum('COMMENT', 'REPLY', 'LIKE'),
                    existing_type=sa.Enum('COMMENT', 'REPLY', 'LIKE', 'CHAT'),
                    existing_nullable=True)

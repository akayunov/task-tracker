"""Initial schema for users, tasks, comments, and refresh tokens.

Revision ID: 20261028_0001
Revises:
Create Date: 2026-10-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20261028_0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role = postgresql.ENUM('user', 'admin', name='user_role')
    task_status = postgresql.ENUM('todo', 'in_progress', 'done', name='task_status')
    task_priority = postgresql.ENUM('low', 'medium', 'high', 'critical', name='task_priority')
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    task_status.create(bind, checkfirst=True)
    task_priority.create(bind, checkfirst=True)

    user_role_column = postgresql.ENUM('user', 'admin', name='user_role', create_type=False)
    task_status_column = postgresql.ENUM(
        'todo', 'in_progress', 'done', name='task_status', create_type=False
    )
    task_priority_column = postgresql.ENUM(
        'low', 'medium', 'high', 'critical', name='task_priority', create_type=False
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('hashed_password', sa.String(length=512), nullable=False),
        sa.Column(
            'role',
            user_role_column,
            server_default=sa.text("'user'::user_role"),
            nullable=False,
        ),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint('char_length(full_name) >= 1', name='ck_users_full_name_length'),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_refresh_tokens_user_id_users',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_refresh_tokens'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_tokens_token_hash'),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])

    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'status',
            task_status_column,
            server_default=sa.text("'todo'::task_status"),
            nullable=False,
        ),
        sa.Column(
            'priority',
            task_priority_column,
            server_default=sa.text("'medium'::task_priority"),
            nullable=False,
        ),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('assignee_id', sa.Uuid(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            'char_length(title) BETWEEN 1 AND 200',
            name='ck_tasks_title_length',
        ),
        sa.CheckConstraint(
            'description IS NULL OR char_length(description) <= 5000',
            name='ck_tasks_description_length',
        ),
        sa.CheckConstraint('version >= 1', name='ck_tasks_version_positive'),
        sa.CheckConstraint(
            "(status = 'done' AND completed_at IS NOT NULL) "
            "OR (status <> 'done' AND completed_at IS NULL)",
            name='ck_tasks_completed_at_matches_status',
        ),
        sa.ForeignKeyConstraint(
            ['author_id'],
            ['users.id'],
            name='fk_tasks_author_id_users',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['assignee_id'],
            ['users.id'],
            name='fk_tasks_assignee_id_users',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_tasks'),
    )
    op.create_index('ix_tasks_author_id', 'tasks', ['author_id'])
    op.create_index('ix_tasks_assignee_id', 'tasks', ['assignee_id'])
    op.create_index('ix_tasks_created_at', 'tasks', ['created_at'])
    op.create_index('ix_tasks_status_created_at', 'tasks', ['status', 'created_at'])

    op.create_table(
        'comments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint('char_length(body) BETWEEN 1 AND 2000', name='ck_comments_body_length'),
        sa.CheckConstraint('version >= 1', name='ck_comments_version_positive'),
        sa.ForeignKeyConstraint(
            ['author_id'],
            ['users.id'],
            name='fk_comments_author_id_users',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['task_id'],
            ['tasks.id'],
            name='fk_comments_task_id_tasks',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_comments'),
    )
    op.create_index('ix_comments_author_id', 'comments', ['author_id'])
    op.create_index('ix_comments_task_id_created_at', 'comments', ['task_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_comments_task_id_created_at', table_name='comments')
    op.drop_index('ix_comments_author_id', table_name='comments')
    op.drop_table('comments')
    op.drop_index('ix_tasks_status_created_at', table_name='tasks')
    op.drop_index('ix_tasks_created_at', table_name='tasks')
    op.drop_index('ix_tasks_assignee_id', table_name='tasks')
    op.drop_index('ix_tasks_author_id', table_name='tasks')
    op.drop_table('tasks')
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    bind = op.get_bind()
    postgresql.ENUM(name='task_priority').drop(bind, checkfirst=True)
    postgresql.ENUM(name='task_status').drop(bind, checkfirst=True)
    postgresql.ENUM(name='user_role').drop(bind, checkfirst=True)

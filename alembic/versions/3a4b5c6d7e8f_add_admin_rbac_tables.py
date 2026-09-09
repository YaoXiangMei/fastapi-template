"""Add Admin RBAC tables.

Revision ID: 3a4b5c6d7e8f
Revises: 2f3a8b9c1d2e
Create Date: 2026-09-09 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '3a4b5c6d7e8f'
down_revision = '2f3a8b9c1d2e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_superuser column to admins table
    op.add_column('admins', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create admin_roles table
    op.create_table(
        'admin_roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create admin_permissions table
    op.create_table(
        'admin_permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_permissions_code', 'admin_permissions', ['code'], unique=True)
    
    # Create admin_role_assignments association table
    op.create_table(
        'admin_role_assignments',
        sa.Column('admin_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['admin_roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('admin_id', 'role_id')
    )
    
    # Create admin_role_permissions association table
    op.create_table(
        'admin_role_permissions',
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('permission_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['admin_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['admin_permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )


def downgrade() -> None:
    op.drop_table('admin_role_permissions')
    op.drop_table('admin_role_assignments')
    op.drop_index('ix_admin_permissions_code', table_name='admin_permissions')
    op.drop_table('admin_permissions')
    op.drop_table('admin_roles')
    op.drop_column('admins', 'is_superuser')

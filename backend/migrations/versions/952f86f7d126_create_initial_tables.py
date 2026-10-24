"""create initial tables

Revision ID: 952f86f7d126
Revises: 
"""
from alembic import op
import sqlalchemy as sa


revision = '952f86f7d126'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('balance_cents', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('balance_cents >= 0', name='ck_accounts_balance_nonnegative'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)
    op.create_table('debit_cards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('last_four', sa.String(length=4), nullable=False),
    sa.Column('expires_on', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', name='card_status'), nullable=False),
    sa.Column('cardholder_name', sa.Text(), nullable=False),
    sa.CheckConstraint("last_four ~ '^[0-9]{4}$'", name='ck_debit_cards_last_four_digits'),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'account_id', name='uq_debit_cards_id_account')
    )
    op.create_index(op.f('ix_debit_cards_account_id'), 'debit_cards', ['account_id'], unique=False)
    op.create_index('one_active_card_per_account', 'debit_cards', ['account_id'], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table('transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('card_id', sa.Integer(), nullable=True),
    sa.Column('amount_cents', sa.BigInteger(), nullable=False),
    sa.Column('balance_change_cents', sa.BigInteger(), nullable=False),
    sa.Column('category', sa.Enum('DOCTOR_VISIT', 'PHARMACY', 'HOSPITAL', 'PRESCRIPTION', 'DENTAL', 'VISION', 'OTC_MEDICINE', 'PREVENTATIVE_CARE', 'RESTAURANT', 'MOVIES', 'ELECTRONICS', name='expense_category'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('type', sa.Enum('DEPOSIT', 'PURCHASE', name='transaction_type'), nullable=False),
    sa.Column('status', sa.Enum('APPROVED', 'DECLINED', name='transaction_status'), nullable=False),
    sa.Column('decline_reason', sa.Enum('INSUFFICIENT_FUNDS', 'INVALID_EXPENSE', 'INACTIVE_CARD', 'EXPIRED_CARD', name='decline_reason'), nullable=True),
    sa.Column('idempotency_key', sa.Text(), nullable=False),
    sa.Column('request_hash', sa.Text(), nullable=False),
    sa.CheckConstraint("(status = 'APPROVED' AND decline_reason IS NULL AND ((type = 'DEPOSIT' AND balance_change_cents = amount_cents) OR (type = 'PURCHASE' AND balance_change_cents = -amount_cents))) OR (status = 'DECLINED' AND type = 'PURCHASE' AND decline_reason IS NOT NULL AND balance_change_cents = 0)", name='ck_transactions_outcome'),
    sa.CheckConstraint("(type = 'DEPOSIT' AND card_id IS NULL AND category IS NULL) OR (type = 'PURCHASE' AND card_id IS NOT NULL AND category IS NOT NULL)", name='ck_transactions_type_fields'),
    sa.CheckConstraint('amount_cents > 0', name='ck_transactions_positive_amount'),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['card_id', 'account_id'], ['debit_cards.id', 'debit_cards.account_id'], name='fk_transactions_card_account'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id', 'idempotency_key', name='uq_transactions_account_idempotency')
    )
    op.create_index('ix_transactions_account_history', 'transactions', ['account_id', 'created_at', 'id'], unique=False)


def downgrade():
    op.drop_index('ix_transactions_account_history', table_name='transactions')
    op.drop_table('transactions')
    op.drop_index('one_active_card_per_account', table_name='debit_cards', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index(op.f('ix_debit_cards_account_id'), table_name='debit_cards')
    op.drop_table('debit_cards')
    op.drop_index(op.f('ix_accounts_user_id'), table_name='accounts')
    op.drop_table('accounts')
    op.drop_table('users')
    # PostgreSQL enum types survive table drops and must be removed explicitly.
    for name in (
        'decline_reason', 'transaction_status', 'transaction_type',
        'expense_category', 'card_status',
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=False)

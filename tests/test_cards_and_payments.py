import calendar
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select, update

from src.database.models import Account, DebitCard, Transaction
from src.enums import CardStatus

MAX_CENTS = 100_000_000_000_000


@pytest.fixture
def account_context(db_client):
    user = db_client.post('/users', json={'name': 'Van', 'email': 'van@example.com'}).json()
    account = db_client.post(f"/users/{user['id']}/accounts", json={}).json()
    return f"/users/{user['id']}/accounts/{account['id']}", account['id']


@pytest.fixture
def card_context(db_client, account_context):
    base, account_id = account_context
    response = db_client.post(base + '/cards', json={'cardholder_name': 'Van'})
    assert response.status_code == 201
    return base, account_id, response.json()['id']


def payment(db_client, base, operation, amount=100, key='key', card_id=None, category='PHARMACY'):
    body = {'amount_cents': amount}
    if operation == 'purchases':
        body.update(card_id=card_id, category=category)
    return db_client.post(base + '/' + operation, json=body, headers={'Idempotency-Key': key})


def assert_finances(connection, account_id, balance, entries):
    assert connection.scalar(select(Account.balance_cents).where(Account.id == account_id)) == balance
    assert connection.scalar(select(func.count()).select_from(Transaction).where(Transaction.account_id == account_id)) == entries
    total = connection.scalar(select(func.coalesce(func.sum(Transaction.balance_change_cents), 0)).where(Transaction.account_id == account_id))
    assert total == balance


def test_issue_card_and_reject_second_active_card(db_client, db_connection, account_context):
    base, aid = account_context
    before = datetime.now(timezone.utc).date()
    response = db_client.post(base + '/cards', json={'cardholder_name': 'Van'})
    after = datetime.now(timezone.utc).date()
    assert response.status_code == 201
    card = response.json()
    assert card['account_id'] == aid and card['status'] == 'ACTIVE'
    assert card['cardholder_name'] == 'Van'
    assert len(card['last_four']) == 4 and card['last_four'].isdigit()
    expected = {date(day.year + 3, day.month, calendar.monthrange(day.year + 3, day.month)[1]).isoformat() for day in (before, after)}
    assert card['expires_on'] in expected
    assert datetime.fromisoformat(card['created_at']).tzinfo is not None
    assert db_connection.scalar(select(DebitCard.id).where(DebitCard.id == card['id'])) == card['id']
    assert db_client.post(base + '/cards', json={'cardholder_name': 'Van'}).status_code == 409
    assert db_connection.scalar(select(func.count()).select_from(DebitCard)) == 1
    assert_finances(db_connection, aid, 0, 0)


@pytest.mark.parametrize('body', [{}, {'cardholder_name': ''}, {'cardholder_name': '   '},
    *[{'cardholder_name': value} for value in [123, True, None, [], {}]],
    {'cardholder_name': 'Van', 'status': 'ACTIVE'}, {'cardholder_name': 'Van', 'expires_on': '2030-01-01'},
    [], 'letters'])
def test_invalid_card_body(db_client, db_connection, account_context, body):
    base, aid = account_context
    assert db_client.post(base + '/cards', json=body).status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(DebitCard)) == 0
    assert_finances(db_connection, aid, 0, 0)


def test_deactivation_is_idempotent_and_allows_replacement(db_client, db_connection, card_context):
    base, aid, cid = card_context
    for _ in range(2):
        response = db_client.post(f'{base}/cards/{cid}/deactivate')
        assert response.status_code == 200
        assert response.json()['status'] == 'INACTIVE'
    assert db_connection.scalar(select(DebitCard.status).where(DebitCard.id == cid)) == CardStatus.INACTIVE
    assert db_client.post(base + '/cards', json={'cardholder_name': 'New card'}).status_code == 201
    assert_finances(db_connection, aid, 0, 0)


def test_issuance_deactivates_expired_card(db_client, db_connection, card_context):
    base, _, cid = card_context
    db_connection.execute(update(DebitCard).where(DebitCard.id == cid).values(expires_on=date(2020, 1, 1)))
    assert db_client.post(base + '/cards', json={'cardholder_name': 'Replacement'}).status_code == 201
    assert db_connection.scalar(select(DebitCard.status).where(DebitCard.id == cid)) == CardStatus.INACTIVE


@pytest.mark.parametrize('operation', ['deposits', 'purchases'])
@pytest.mark.parametrize('amount', ['letters', '100', True, False, None, [], {}, 1.5, 0, -1, MAX_CENTS + 1])
def test_invalid_payment_amount(db_client, db_connection, card_context, operation, amount):
    base, aid, cid = card_context
    assert payment(db_client, base, operation, amount=amount, card_id=cid).status_code == 422
    assert_finances(db_connection, aid, 0, 0)


@pytest.mark.parametrize('operation', ['deposits', 'purchases'])
@pytest.mark.parametrize('key', [None, '', '   ', 'x' * 256])
def test_invalid_idempotency_header(db_client, db_connection, card_context, operation, key):
    base, aid, cid = card_context
    body = {'amount_cents': 100}
    if operation == 'purchases':
        body.update(card_id=cid, category='PHARMACY')
    headers = {} if key is None else {'Idempotency-Key': key}
    assert db_client.post(base + '/' + operation, json=body, headers=headers).status_code == 422
    assert_finances(db_connection, aid, 0, 0)


@pytest.mark.parametrize('operation', ['deposits', 'purchases'])
@pytest.mark.parametrize('body', [{}, [], 'letters', {'amount_cents': 100, 'unexpected': True}])
def test_invalid_payment_body(db_client, db_connection, card_context, operation, body):
    base, aid, _ = card_context
    assert db_client.post(base + '/' + operation, json=body, headers={'Idempotency-Key': 'key'}).status_code == 422
    assert_finances(db_connection, aid, 0, 0)


@pytest.mark.parametrize('overrides', [
    {'card_id': 'letters'}, {'card_id': '1'}, {'card_id': True}, {'card_id': None},
    {'card_id': 0}, {'card_id': -1}, {'card_id': 2147483648},
    {'category': 'UNKNOWN'}, {'category': 12}, {'category': None},
])
def test_invalid_purchase_fields(db_client, db_connection, card_context, overrides):
    base, aid, cid = card_context
    body = {'card_id': cid, 'amount_cents': 100, 'category': 'PHARMACY', **overrides}
    assert db_client.post(base + '/purchases', json=body, headers={'Idempotency-Key': 'key'}).status_code == 422
    assert_finances(db_connection, aid, 0, 0)


def test_deposit_limit_replay_conflict_and_account_scoping(db_client, db_connection, account_context):
    base, aid = account_context
    first = payment(db_client, base, 'deposits', MAX_CENTS)
    assert first.status_code == 201
    row = first.json()
    assert row['type'] == 'DEPOSIT' and row['status'] == 'APPROVED'
    assert row['amount_cents'] == row['balance_change_cents'] == MAX_CENTS
    assert row['card_id'] is row['category'] is row['decline_reason'] is None
    replay = payment(db_client, base, 'deposits', MAX_CENTS)
    assert replay.status_code == 200 and replay.json() == row
    assert payment(db_client, base, 'deposits', 1).status_code == 409
    assert_finances(db_connection, aid, MAX_CENTS, 1)
    user_base = base.rsplit('/accounts/', 1)[0]
    other = db_client.post(user_base + '/accounts', json={}).json()
    assert payment(db_client, user_base + f"/accounts/{other['id']}", 'deposits', 1).status_code == 201
    assert_finances(db_connection, other['id'], 1, 1)


def test_purchase_limit_exact_balance_replay_and_operation_conflict(db_client, db_connection, card_context):
    base, aid, cid = card_context
    assert payment(db_client, base, 'deposits', MAX_CENTS, 'fund').status_code == 201
    assert payment(db_client, base, 'purchases', 1, 'fund', cid).status_code == 409
    result = payment(db_client, base, 'purchases', MAX_CENTS, 'buy', cid)
    assert result.status_code == 201
    row = result.json()
    assert row['status'] == 'APPROVED' and row['type'] == 'PURCHASE'
    assert row['balance_change_cents'] == -MAX_CENTS and row['decline_reason'] is None
    replay = payment(db_client, base, 'purchases', MAX_CENTS, 'buy', cid)
    assert replay.status_code == 200 and replay.json() == row
    assert payment(db_client, base, 'purchases', 1, 'buy', cid).status_code == 409
    assert_finances(db_connection, aid, 0, 2)


@pytest.mark.parametrize('reason', ['INSUFFICIENT_FUNDS', 'INVALID_EXPENSE', 'INACTIVE_CARD', 'EXPIRED_CARD'])
def test_declines_persist_without_balance_change(db_client, db_connection, card_context, reason):
    base, aid, cid = card_context
    assert payment(db_client, base, 'deposits', 100, 'fund').status_code == 201
    category, amount = 'PHARMACY', 50
    if reason == 'INSUFFICIENT_FUNDS':
        amount = 101
    elif reason == 'INVALID_EXPENSE':
        category = 'RESTAURANT'
    elif reason == 'INACTIVE_CARD':
        assert db_client.post(f'{base}/cards/{cid}/deactivate').status_code == 200
    else:
        db_connection.execute(update(DebitCard).where(DebitCard.id == cid).values(expires_on=date(2020, 1, 1)))
    response = payment(db_client, base, 'purchases', amount, 'buy', cid, category)
    assert response.status_code == 201
    row = response.json()
    assert row['status'] == 'DECLINED' and row['decline_reason'] == reason
    assert row['balance_change_cents'] == 0
    assert payment(db_client, base, 'purchases', amount, 'buy', cid, category).json() == row
    assert_finances(db_connection, aid, 100, 2)
    if reason == 'EXPIRED_CARD':
        assert db_connection.scalar(select(DebitCard.status).where(DebitCard.id == cid)) == CardStatus.INACTIVE


def test_decline_replay_after_funding(db_client, db_connection, card_context):
    base, aid, cid = card_context
    first = payment(db_client, base, 'purchases', 100, 'buy', cid)
    assert first.json()['decline_reason'] == 'INSUFFICIENT_FUNDS'
    payment(db_client, base, 'deposits', 100, 'fund')
    replay = payment(db_client, base, 'purchases', 100, 'buy', cid)
    assert replay.status_code == 200 and replay.json() == first.json()
    assert_finances(db_connection, aid, 100, 2)


@pytest.mark.parametrize('operation', ['deposits', 'purchases'])
def test_ledger_failure_rolls_back_balance(db_client, db_connection, card_context, monkeypatch, operation):
    base, aid, cid = card_context
    payment(db_client, base, 'deposits', 500, 'fund')
    def fail(*args, **kwargs):
        raise RuntimeError('simulated ledger failure')
    module = 'deposit' if operation == 'deposits' else 'purchase'
    monkeypatch.setattr(f'src.services.{module}.append_transaction', fail)
    with pytest.raises(RuntimeError, match='simulated ledger failure'):
        payment(db_client, base, operation, 100, 'failure', cid)
    assert_finances(db_connection, aid, 500, 1)


@pytest.mark.parametrize('operation', ['cards', 'deposits', 'purchases', 'deactivate'])
def test_wrong_owner_and_missing_account(db_client, db_connection, card_context, operation):
    base, aid, cid = card_context
    other = db_client.post('/users', json={'name': 'Other', 'email': 'other@example.com'}).json()['id']
    for target in [f'/users/{other}/accounts/{aid}', f'/users/{other}/accounts/2147483647']:
        if operation == 'cards':
            response = db_client.post(target + '/cards', json={'cardholder_name': 'Other'})
        elif operation == 'deactivate':
            response = db_client.post(f'{target}/cards/{cid}/deactivate')
        else:
            response = payment(db_client, target, operation, card_id=cid)
        assert response.status_code == 404
    assert db_connection.scalar(select(DebitCard.status).where(DebitCard.id == cid)) == CardStatus.ACTIVE
    assert_finances(db_connection, aid, 0, 0)


def test_missing_and_wrong_account_cards(db_client, db_connection, card_context):
    base, aid, cid = card_context
    user_base = base.rsplit('/accounts/', 1)[0]
    other = db_client.post(user_base + '/accounts', json={}).json()['id']
    other_base = user_base + f'/accounts/{other}'
    for target, card in [(base, 2147483647), (other_base, cid)]:
        assert payment(db_client, target, 'purchases', card_id=card).status_code == 404
        assert db_client.post(f'{target}/cards/{card}/deactivate').status_code == 404
    assert_finances(db_connection, aid, 0, 0)
    assert_finances(db_connection, other, 0, 0)


@pytest.mark.parametrize('operation', ['cards', 'deposits', 'purchases', 'deactivate'])
@pytest.mark.parametrize('bad_id', ['letters', '1.5', 'true', '-1', '0', '2147483648', '99999999999999999999999'])
def test_invalid_path_ids(db_client, db_connection, card_context, operation, bad_id):
    base, aid, cid = card_context
    paths = [base.replace('/users/' + base.split('/')[2], '/users/' + bad_id),
             base.rsplit('/', 1)[0] + '/' + bad_id]
    if operation == 'deactivate':
        paths.append(base)
    for i, target in enumerate(paths):
        if operation == 'cards':
            response = db_client.post(target + '/cards', json={'cardholder_name': 'Van'})
        elif operation == 'deactivate':
            card = bad_id if i == 2 else cid
            response = db_client.post(f'{target}/cards/{card}/deactivate')
        else:
            response = payment(db_client, target, operation, card_id=cid)
        assert response.status_code == 422
    assert_finances(db_connection, aid, 0, 0)


@pytest.mark.parametrize('category,approved', [
    ('DOCTOR_VISIT', True), ('PHARMACY', True), ('HOSPITAL', True),
    ('PRESCRIPTION', True), ('DENTAL', True), ('VISION', True),
    ('OTC_MEDICINE', True), ('PREVENTATIVE_CARE', True),
    ('RESTAURANT', False), ('MOVIES', False), ('ELECTRONICS', False),
])
def test_category_eligibility(db_client, db_connection, card_context, category, approved):
    base, aid, cid = card_context
    assert payment(db_client, base, 'deposits', 100, 'fund').status_code == 201
    response = payment(db_client, base, 'purchases', 100, 'buy', cid, category)
    assert response.status_code == 201
    assert response.json()['status'] == ('APPROVED' if approved else 'DECLINED')
    assert response.json()['decline_reason'] == (None if approved else 'INVALID_EXPENSE')
    assert_finances(db_connection, aid, 0 if approved else 100, 2)


@pytest.mark.parametrize('operation', ['cards', 'deposits', 'purchases'])
@pytest.mark.parametrize('content', ['', '{broken'])
def test_missing_or_malformed_json(db_client, db_connection, card_context, operation, content):
    base, aid, _ = card_context
    response = db_client.post(base + '/' + operation, content=content,
        headers={'Content-Type': 'application/json', 'Idempotency-Key': 'key'})
    assert response.status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(DebitCard)) == 1
    assert_finances(db_connection, aid, 0, 0)


def test_card_valid_through_expiration_date(db_client, db_connection, card_context, monkeypatch):
    base, aid, cid = card_context
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2028, 2, 29, 12, tzinfo=timezone.utc)
    monkeypatch.setattr('src.services.purchase.datetime', FixedDatetime)
    db_connection.execute(update(DebitCard).where(DebitCard.id == cid).values(expires_on=date(2028, 2, 29)))
    payment(db_client, base, 'deposits', 100, 'fund')
    assert payment(db_client, base, 'purchases', 100, 'buy', cid).json()['status'] == 'APPROVED'
    assert db_connection.scalar(select(DebitCard.status).where(DebitCard.id == cid)) == CardStatus.ACTIVE
    assert_finances(db_connection, aid, 0, 2)


def test_deposit_rejects_balance_overflow(db_client, db_connection, account_context):
    base, aid = account_context
    maximum = 9_223_372_036_854_775_807
    # Seed a matching ledger and balance directly to exercise the storage boundary.
    db_connection.execute(Transaction.__table__.insert().values(
        account_id=aid, amount_cents=maximum, balance_change_cents=maximum,
        type='DEPOSIT', status='APPROVED', idempotency_key='seed', request_hash='seed'))
    db_connection.execute(update(Account).where(Account.id == aid).values(balance_cents=maximum))
    assert payment(db_client, base, 'deposits', 1).status_code == 409
    assert_finances(db_connection, aid, maximum, 1)

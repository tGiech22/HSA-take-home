from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from src.database.models import Transaction


@pytest.fixture
def history_account(db_client):
    user = db_client.post('/users', json={'name': 'History', 'email': 'history@example.com'})
    assert user.status_code == 201
    user_id = user.json()['id']
    account = db_client.post(f'/users/{user_id}/accounts', json={})
    assert account.status_code == 201
    return user_id, account.json()['id']


def test_empty_history(db_client, history_account):
    uid, aid = history_account
    response = db_client.get(f'/users/{uid}/accounts/{aid}/transactions')
    assert response.status_code == 200
    assert response.json() == []


def test_history_outcomes_ordering_and_pagination(db_client, db_connection, history_account):
    uid, aid = history_account
    base = f'/users/{uid}/accounts/{aid}'
    card = db_client.post(base + '/cards', json={'cardholder_name': 'History'})
    assert card.status_code == 201
    entries = []
    for key, operation, payload in [
        ('fund', 'deposits', {'amount_cents': 1000}),
        ('buy', 'purchases', {'amount_cents': 200, 'card_id': card.json()['id'], 'category': 'PHARMACY'}),
        ('decline', 'purchases', {'amount_cents': 100, 'card_id': card.json()['id'], 'category': 'MOVIES'}),
    ]:
        response = db_client.post(base + '/' + operation, json=payload,
                                  headers={'Idempotency-Key': key})
        assert response.status_code == 201
        entries.append(response.json())

    # Give the deposit the newest timestamp; purchase timestamps tie so ID decides.
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, entry in enumerate(entries):
        created_at = timestamp + timedelta(days=1) if index == 0 else timestamp
        db_connection.execute(update(Transaction).where(Transaction.id == entry['id'])
                              .values(created_at=created_at))
        entry['created_at'] = created_at.isoformat()
    expected = [entries[0], entries[2], entries[1]]
    response = db_client.get(base + '/transactions')
    assert response.status_code == 200
    actual = response.json()
    for item in actual:
        item['created_at'] = datetime.fromisoformat(item['created_at']).isoformat()
    assert actual == expected
    assert actual[1]['status'] == 'DECLINED'
    assert actual[1]['decline_reason'] == 'INVALID_EXPENSE'
    assert actual[1]['balance_change_cents'] == 0
    page = db_client.get(base + '/transactions', params={'limit': 1, 'offset': 1})
    assert page.status_code == 200
    assert [entry['id'] for entry in page.json()] == [entries[2]['id']]
    assert db_client.get(base + '/transactions?offset=3').json() == []
    balance = next(a['balance_cents'] for a in db_client.get('/accounts').json() if a['id'] == aid)
    assert balance == 800


def test_history_account_isolation_and_missing_accounts(db_client, history_account):
    uid, aid = history_account
    base = f'/users/{uid}/accounts/{aid}'
    assert db_client.post(base + '/deposits', json={'amount_cents': 100},
                          headers={'Idempotency-Key': 'fund'}).status_code == 201
    other_account = db_client.post(f'/users/{uid}/accounts', json={}).json()['id']
    assert db_client.get(f'/users/{uid}/accounts/{other_account}/transactions').json() == []
    other_user = db_client.post('/users', json={'name': 'Other', 'email': 'other@example.com'}).json()['id']
    for user_id, account_id in [(other_user, aid), (uid, 2147483647), (2147483647, aid)]:
        response = db_client.get(f'/users/{user_id}/accounts/{account_id}/transactions')
        assert response.status_code == 404
        assert response.json() == {'detail': 'Account not found.'}


@pytest.mark.parametrize('query', ['limit=0', 'limit=-1', 'limit=101', 'limit=text',
                                   'limit=1.5', 'offset=-1', 'offset=text', 'offset=1.5'])
def test_invalid_history_pagination(db_client, history_account, query):
    uid, aid = history_account
    assert db_client.get(f'/users/{uid}/accounts/{aid}/transactions?{query}').status_code == 422


@pytest.mark.parametrize('bad_id', ['0', '-1', '2147483648', 'text', '1.5'])
def test_invalid_history_path_ids(db_client, history_account, bad_id):
    uid, aid = history_account
    assert db_client.get(f'/users/{bad_id}/accounts/{aid}/transactions').status_code == 422
    assert db_client.get(f'/users/{uid}/accounts/{bad_id}/transactions').status_code == 422

from datetime import datetime

import pytest
from sqlalchemy import func, select

from src.database.models import Account, Transaction


@pytest.fixture
def user_id(db_client):
    response = db_client.post('/users', json={'name': 'Van', 'email': 'van@example.com'})
    assert response.status_code == 201
    return response.json()['id']


def test_create_multiple_accounts_persists_defaults(db_client, db_connection, user_id):
    ids = []
    for _ in range(2):
        response = db_client.post(f'/users/{user_id}/accounts', json={})
        assert response.status_code == 201
        body = response.json()
        assert set(body) == {'id', 'user_id', 'balance_cents', 'created_at'}
        assert body['user_id'] == user_id
        assert body['balance_cents'] == 0
        assert datetime.fromisoformat(body['created_at']).tzinfo is not None
        ids.append(body['id'])
    assert len(set(ids)) == 2
    stored = db_connection.execute(select(Account.__table__)).mappings().all()
    assert len(stored) == 2
    assert all(row['user_id'] == user_id and row['balance_cents'] == 0 for row in stored)
    assert db_connection.scalar(select(func.count()).select_from(Transaction)) == 0


@pytest.mark.parametrize('path_id', ['letters', '1.5', 'true', '0', '-1', '2147483648', '999999999999999999999999'])
def test_invalid_user_id_does_not_create_account(db_client, db_connection, path_id):
    response = db_client.post(f'/users/{path_id}/accounts', json={})
    assert response.status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(Account)) == 0


def test_missing_user_does_not_create_account(db_client, db_connection):
    assert db_client.post('/users/2147483647/accounts', json={}).status_code == 404
    assert db_connection.scalar(select(func.count()).select_from(Account)) == 0


@pytest.mark.parametrize('payload', [
    {'balance_cents': 100}, {'balance_cents': 'letters'}, {'balance_cents': -1},
    {'user_id': 'letters'}, {'id': 1}, {'created_at': '2026-01-01'},
    [], 'letters', 123,
])
def test_invalid_account_body_does_not_persist(db_client, db_connection, user_id, payload):
    assert db_client.post(f'/users/{user_id}/accounts', json=payload).status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(Account)) == 0


def test_missing_account_body(db_client, db_connection, user_id):
    assert db_client.post(f'/users/{user_id}/accounts').status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(Account)) == 0

from datetime import datetime

import pytest
from sqlalchemy import func, select

from src.database.models import User


def test_create_user_persists_normalized_email(db_client, db_connection):
    response = db_client.post('/users', json={'name': 'Van', 'email': ' Van+Shopping@Example.COM '})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {'id', 'name', 'email', 'created_at'}
    assert isinstance(body['id'], int)
    assert body['name'] == 'Van'
    assert body['email'] == 'van+shopping@example.com'
    assert datetime.fromisoformat(body['created_at']).tzinfo is not None
    stored = db_connection.execute(select(User.__table__)).mappings().one()
    assert stored['id'] == body['id']
    assert stored['name'] == body['name']
    assert stored['email'] == body['email']


@pytest.mark.parametrize('payload', [
    {}, {'name': 'Van'}, {'email': 'van@example.com'},
    {'name': '', 'email': 'van@example.com'},
    *[{'name': value, 'email': 'van@example.com'} for value in [None, 123, True, [], {}]],
    *[{'name': 'Van', 'email': value} for value in [None, 123, True, [], {}, '', 'letters', 'van@@example.com']],
    {'name': 'Van', 'email': 'van@example.com', 'id': 1},
    {'name': 'Van', 'email': 'van@example.com', 'created_at': '2026-01-01'},
    [], 'letters', 123,
])
def test_invalid_user_request_does_not_persist(db_client, db_connection, payload):
    assert db_client.post('/users', json=payload).status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(User)) == 0


def test_duplicate_email_conflict_and_recovery(db_client, db_connection):
    assert db_client.post('/users', json={'name': 'One', 'email': 'van@example.com'}).status_code == 201
    duplicate = db_client.post('/users', json={'name': 'Two', 'email': ' VAN@EXAMPLE.COM '})
    assert duplicate.status_code == 409
    assert db_connection.scalar(select(func.count()).select_from(User)) == 1
    assert db_client.post('/users', json={'name': 'Three', 'email': 'other@example.com'}).status_code == 201
    assert db_connection.scalar(select(func.count()).select_from(User)) == 2


def test_malformed_user_json(db_client, db_connection):
    response = db_client.post('/users', content='{broken', headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert db_connection.scalar(select(func.count()).select_from(User)) == 0

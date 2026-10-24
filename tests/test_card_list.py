from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from src.database.models import DebitCard
from src.enums import CardStatus


@pytest.fixture
def card_list_account(db_client):
    user = db_client.post('/users', json={'name': 'Cards', 'email': 'cards@example.com'})
    assert user.status_code == 201
    uid = user.json()['id']
    account = db_client.post(f'/users/{uid}/accounts', json={})
    assert account.status_code == 201
    return uid, account.json()['id']


def test_empty_card_list(db_client, card_list_account):
    uid, aid = card_list_account
    response = db_client.get(f'/users/{uid}/accounts/{aid}/cards')
    assert response.status_code == 200
    assert response.json() == []


def test_card_details_ordering_and_expired_status_unchanged(db_client, db_connection, card_list_account):
    uid, aid = card_list_account
    base = f'/users/{uid}/accounts/{aid}/cards'
    cards = []
    for index in range(3):
        response = db_client.post(base, json={'cardholder_name': f'Card {index}'})
        assert response.status_code == 201
        card = response.json()
        cards.append(card)
        if index < 2:
            assert db_client.post(f"{base}/{card['id']}/deactivate").status_code == 200
            card['status'] = 'INACTIVE'

    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, card in enumerate(cards):
        # The oldest ID has the newest timestamp; the other two timestamps tie.
        created_at = timestamp + timedelta(days=1) if index == 0 else timestamp
        db_connection.execute(update(DebitCard).where(DebitCard.id == card['id'])
                              .values(created_at=created_at))
        card['created_at'] = created_at.isoformat()
    db_connection.execute(update(DebitCard).where(DebitCard.id == cards[2]['id'])
                          .values(expires_on=date(2020, 1, 1)))
    cards[2]['expires_on'] = '2020-01-01'

    for _ in range(2):
        response = db_client.get(base)
        assert response.status_code == 200
        actual = response.json()
        for card in actual:
            card['created_at'] = datetime.fromisoformat(card['created_at']).isoformat()
        assert actual == [cards[0], cards[2], cards[1]]
    assert db_connection.scalar(select(DebitCard.status).where(
        DebitCard.id == cards[2]['id'])) == CardStatus.ACTIVE


def test_card_list_account_isolation(db_client, card_list_account):
    uid, aid = card_list_account
    assert db_client.post(f'/users/{uid}/accounts/{aid}/cards',
                          json={'cardholder_name': 'Cards'}).status_code == 201
    other_account = db_client.post(f'/users/{uid}/accounts', json={}).json()['id']
    response = db_client.get(f'/users/{uid}/accounts/{other_account}/cards')
    assert response.status_code == 200
    assert response.json() == []
    other_user = db_client.post('/users', json={
        'name': 'Other', 'email': 'other@example.com'}).json()['id']
    for user_id, account_id in [(other_user, aid), (uid, 2147483647), (2147483647, aid)]:
        response = db_client.get(f'/users/{user_id}/accounts/{account_id}/cards')
        assert response.status_code == 404
        assert response.json() == {'detail': 'Account not found.'}


@pytest.mark.parametrize('bad_id', ['0', '-1', '2147483648', 'text', '1.5', 'true'])
def test_card_list_invalid_ids(db_client, card_list_account, bad_id):
    uid, aid = card_list_account
    assert db_client.get(f'/users/{bad_id}/accounts/{aid}/cards').status_code == 422
    assert db_client.get(f'/users/{uid}/accounts/{bad_id}/cards').status_code == 422

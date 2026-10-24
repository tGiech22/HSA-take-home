from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select

from src.database.models import Account, Transaction


def run_together(first_request, second_request):
    """Start two independent requests together and propagate worker failures."""
    start = Barrier(2)

    def run(request):
        start.wait(timeout=10)
        return request()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(run, first_request)
        second = executor.submit(run, second_request)
        return [first.result(timeout=20), second.result(timeout=20)]


def deposit(context, amount, key):
    with context.client() as client:
        return client.post(
            context.base_url + '/deposits',
            json={'amount_cents': amount},
            headers={'Idempotency-Key': key},
        )


def read_finances(context):
    # A fresh connection sees only the committed outcomes of the requests.
    with context.session() as session:
        balance = session.scalar(select(Account.balance_cents).where(Account.id == context.account_id))
        entries = list(session.scalars(select(Transaction).where(
            Transaction.account_id == context.account_id
        ).order_by(Transaction.id)))
        assert balance == sum(entry.balance_change_cents for entry in entries)
        return balance, entries


def test_sequential_deposit_idempotency_and_conflict(concurrent_account):
    context = concurrent_account
    first = deposit(context, 1000, 'deposit')
    retry = deposit(context, 1000, 'deposit')
    conflict = deposit(context, 2000, 'deposit')

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert conflict.status_code == 409
    balance, entries = read_finances(context)
    assert balance == 1000
    assert len(entries) == 1
    assert entries[0].id == first.json()['id']
    assert entries[0].amount_cents == entries[0].balance_change_cents == 1000


def test_concurrent_identical_deposits_apply_once(concurrent_account):
    context = concurrent_account
    responses = run_together(
        lambda: deposit(context, 1000, 'same-key'),
        lambda: deposit(context, 1000, 'same-key'),
    )

    assert sorted(response.status_code for response in responses) == [200, 201]
    assert responses[0].json() == responses[1].json()
    balance, entries = read_finances(context)
    assert balance == 1000
    assert len(entries) == 1
    assert entries[0].id == responses[0].json()['id']
    assert entries[0].status.value == 'APPROVED'
    assert entries[0].balance_change_cents == 1000


def test_concurrent_purchases_cannot_overspend(concurrent_account):
    context = concurrent_account
    assert deposit(context, 10000, 'funding').status_code == 201

    def purchase(key):
        with context.client() as client:
            return client.post(
                context.base_url + '/purchases',
                json={'card_id': context.card_id, 'amount_cents': 8000, 'category': 'PHARMACY'},
                headers={'Idempotency-Key': key},
            )

    responses = run_together(lambda: purchase('one'), lambda: purchase('two'))
    assert all(response.status_code == 201 for response in responses)
    results = [response.json() for response in responses]
    assert sorted(row['status'] for row in results) == ['APPROVED', 'DECLINED']
    approved = next(row for row in results if row['status'] == 'APPROVED')
    declined = next(row for row in results if row['status'] == 'DECLINED')
    assert approved['balance_change_cents'] == -8000
    assert declined['decline_reason'] == 'INSUFFICIENT_FUNDS'
    assert declined['balance_change_cents'] == 0
    balance, entries = read_finances(context)
    assert balance == 2000
    assert len(entries) == 3
    assert {entry.id for entry in entries if entry.type.value == 'PURCHASE'} == {
        row['id'] for row in results
    }

from sqlalchemy.orm import Session

from src.database.models import Account, User


class UserNotFoundError(Exception):
    pass


def create_account(session: Session, *, user_id: int) -> Account:
    with session.begin():
        if session.get(User, user_id) is None:
            raise UserNotFoundError
        account = Account(user_id=user_id)
        session.add(account)
        session.flush()
    return account

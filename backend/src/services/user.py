from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import User


class DuplicateEmailError(Exception):
    pass


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.id)).all())


def create_user(session: Session, *, name: str, email: str) -> User:
    user = User(name=name, email=email)
    try:
        with session.begin():
            session.add(user)
            session.flush()
    except IntegrityError as error:
        if (
            getattr(error.orig, "sqlstate", None) == "23505"
            and getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            == "users_email_key"
        ):
            raise DuplicateEmailError from error
        raise
    return user

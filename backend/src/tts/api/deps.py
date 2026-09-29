"""Request dependencies: one database session per request, committed on success."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker


def session_factory(request: Request) -> sessionmaker[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    return factory


def db_session(request: Request) -> Iterator[Session]:
    session = session_factory(request)()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(db_session)]

from __future__ import annotations
from sqlalchemy.orm import Session
from src.db.base import SessionLocal


class _SessionContextManager:
    """Provides a transactional database session compatible with both sync and async with blocks."""

    def __init__(self):
        self.session: Session = SessionLocal()

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        self.session.close()

    async def __aenter__(self) -> Session:
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        self.session.close()


def get_session() -> _SessionContextManager:
    """Returns a context manager for database session management."""
    return _SessionContextManager()

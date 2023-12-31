from datetime import datetime

from sqlalchemy import DateTime, PrimaryKeyConstraint, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from src.limits import OAUTH1_NONCE_MAX_LENGTH
from src.models.db.base import Base

# TODO: timestamp expire, pruner


class OAuth1Nonce(Base.NoID):
    __tablename__ = 'oauth1_nonce'

    nonce: Mapped[str] = mapped_column(Unicode(OAUTH1_NONCE_MAX_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (PrimaryKeyConstraint(nonce, created_at),)

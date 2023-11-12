from datetime import datetime

from sqlalchemy import (DateTime, Enum, ForeignKey, SmallInteger, UnicodeText,
                        func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from limits import MAIL_UNPROCESSED_EXPIRE
from models.db.base import Base
from models.db.created_at import CreatedAt
from models.db.user import User
from models.mail_from_type import MailFromType


class Mail(Base.UUID, CreatedAt):
    __tablename__ = 'mail'

    from_user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False)
    from_user: Mapped[User] = relationship(lazy='raise')
    from_type: Mapped[MailFromType] = mapped_column(Enum(MailFromType), nullable=False)
    to_user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False)
    to_user: Mapped[User] = relationship(lazy='raise')
    subject: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    body: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    ref: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # defaults
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now() + MAIL_UNPROCESSED_EXPIRE)
    processing_counter: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
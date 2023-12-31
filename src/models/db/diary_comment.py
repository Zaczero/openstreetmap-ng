from sqlalchemy import ForeignKey, LargeBinary, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.lib.crypto import HASH_SIZE
from src.lib.rich_text import RichTextMixin
from src.limits import DIARY_COMMENT_BODY_MAX_LENGTH
from src.models.db.base import Base
from src.models.db.cache_entry import CacheEntry
from src.models.db.created_at_mixin import CreatedAtMixin
from src.models.db.diary import Diary
from src.models.db.user import User
from src.models.text_format import TextFormat


class DiaryComment(Base.UUID, CreatedAtMixin, RichTextMixin):
    __tablename__ = 'diary_comment'
    __rich_text_fields__ = (('body', TextFormat.markdown),)

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False)
    user: Mapped[User] = relationship(lazy='raise')
    diary_id: Mapped[int] = mapped_column(ForeignKey(Diary.id), nullable=False)
    diary: Mapped[Diary] = relationship(lazy='raise')
    body: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    body_rich_hash: Mapped[bytes | None] = mapped_column(LargeBinary(HASH_SIZE), nullable=True, default=None)
    body_rich: Mapped[CacheEntry | None] = relationship(
        CacheEntry,
        primaryjoin=CacheEntry.id == body_rich_hash,
        viewonly=True,
        default=None,
        lazy='raise',
    )

    @validates('body')
    def validate_body(self, _: str, value: str) -> str:
        if len(value) > DIARY_COMMENT_BODY_MAX_LENGTH:
            raise ValueError('Comment is too long')
        return value

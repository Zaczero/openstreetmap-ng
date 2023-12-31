import anyio
from shapely import Point
from sqlalchemy import ForeignKey, LargeBinary, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.lib.crypto import HASH_SIZE
from src.lib.rich_text import RichTextMixin
from src.limits import DIARY_BODY_MAX_LENGTH, LANGUAGE_CODE_MAX_LENGTH
from src.models.db.base import Base
from src.models.db.cache_entry import CacheEntry
from src.models.db.created_at_mixin import CreatedAtMixin
from src.models.db.updated_at_mixin import UpdatedAtMixin
from src.models.db.user import User
from src.models.geometry_type import PointType
from src.models.text_format import TextFormat


class Diary(Base.Sequential, CreatedAtMixin, UpdatedAtMixin, RichTextMixin):
    __tablename__ = 'diary'
    __rich_text_fields__ = (('body', TextFormat.markdown),)

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False)
    user: Mapped[User] = relationship(lazy='raise')
    title: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    body: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    body_rich_hash: Mapped[bytes | None] = mapped_column(LargeBinary(HASH_SIZE), nullable=True, default=None)
    body_rich: Mapped[CacheEntry | None] = relationship(
        CacheEntry,
        primaryjoin=CacheEntry.id == body_rich_hash,
        viewonly=True,
        default=None,
        lazy='raise',
    )
    language_code: Mapped[str] = mapped_column(Unicode(LANGUAGE_CODE_MAX_LENGTH), nullable=False)
    point: Mapped[Point | None] = mapped_column(PointType, nullable=True)

    @validates('body')
    def validate_body(self, _: str, value: str) -> str:
        if len(value) > DIARY_BODY_MAX_LENGTH:
            raise ValueError('Diary is too long')
        return value

    async def resolve_comments_rich_text(self) -> None:
        """
        Resolve rich text for all comments.
        """

        async with anyio.create_task_group() as tg:
            for comment in self.comments:
                tg.start_soon(comment.resolve_rich_text)

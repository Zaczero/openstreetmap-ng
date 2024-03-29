from datetime import datetime

from shapely import Point
from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Identity, PrimaryKeyConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.lib.updating_cached_property import updating_cached_property
from app.models.db.base import Base
from app.models.db.changeset import Changeset
from app.models.db.user import User
from app.models.element_member_ref import ElementMemberRef, ElementMemberRefJSONB
from app.models.element_ref import ElementRef, VersionedElementRef
from app.models.element_type import ElementType
from app.models.geometry import PointType


class Element(Base.NoID):
    __tablename__ = 'element'

    sequence_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True, minvalue=1), init=False, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey(User.id), nullable=True)
    user: Mapped[User | None] = relationship(init=False, lazy='raise')
    changeset_id: Mapped[int] = mapped_column(ForeignKey(Changeset.id), nullable=False)
    changeset: Mapped[Changeset] = relationship(init=False, lazy='raise', innerjoin=True)
    type: Mapped[ElementType] = mapped_column(Enum('node', 'way', 'relation', name='element_type'), nullable=False)
    id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tags: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    point: Mapped[Point | None] = mapped_column(PointType, nullable=True)
    members: Mapped[list[ElementMemberRef]] = mapped_column(ElementMemberRefJSONB, nullable=False)

    # defaults
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(True),
        init=False,
        nullable=False,
        server_default=func.statement_timestamp(),
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(True),
        init=False,
        nullable=True,
        server_default=None,
    )

    __table_args__ = (PrimaryKeyConstraint(type, id, version, name='element_pkey'),)

    @updating_cached_property('id')
    def element_ref(self) -> ElementRef:
        return ElementRef(self.type, self.id)

    @updating_cached_property('id')
    def versioned_ref(self) -> VersionedElementRef:
        return VersionedElementRef(self.type, self.id, self.version)

    @updating_cached_property('members')
    def members_element_refs_set(self) -> frozenset[ElementRef]:
        return frozenset(member.element_ref for member in self.members)

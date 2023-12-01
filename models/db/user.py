import logging
from collections.abc import Sequence
from datetime import datetime
from hmac import compare_digest
from ipaddress import IPv4Address, IPv6Address
from typing import Self

from argon2 import PasswordHasher
from fastapi import Request
from fastapi.security.utils import get_authorization_scheme_param
from shapely.geometry import Point
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    LargeBinary,
    SmallInteger,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from config import DEFAULT_LANGUAGE, SECRET
from cython_lib.geoutils import haversine_distance
from lib.avatar import Avatar
from lib.cache import CACHE_HASH_SIZE
from lib.exceptions import raise_for
from lib.languages import get_language_info, normalize_language_case
from lib.oauth1 import OAuth1
from lib.oauth2 import OAuth2
from lib.password_hash import PasswordHash
from lib.rich_text import rich_text_getter
from limits import (
    FAST_PASSWORD_CACHE_EXPIRE,
    LANGUAGE_CODE_MAX_LENGTH,
    USER_DESCRIPTION_MAX_LENGTH,
    USER_LANGUAGES_LIMIT,
)
from models.db.base import Base
from models.db.created_at import CreatedAt
from models.db.oauth1_nonce import OAuth1Nonce
from models.db.user_token_session import UserTokenSession
from models.geometry_type import PointType
from models.language_info import LanguageInfo
from models.scope import Scope
from models.text_format import TextFormat
from models.user_avatar_type import UserAvatarType
from models.user_role import UserRole
from models.user_status import UserStatus


class User(Base.NoID, CreatedAt):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(BigInteger, nullable=False, primary_key=True)

    email: Mapped[str] = mapped_column(Unicode, nullable=False)
    display_name: Mapped[str] = mapped_column(Unicode, nullable=False)
    password_hashed: Mapped[str] = mapped_column(Unicode, nullable=False)
    created_ip: Mapped[IPv4Address | IPv6Address] = mapped_column(INET, nullable=False)

    consider_public_domain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    languages: Mapped[list[str]] = mapped_column(ARRAY(Unicode(LANGUAGE_CODE_MAX_LENGTH)), nullable=False)

    auth_provider: Mapped[str | None] = mapped_column(Unicode, nullable=True)
    auth_uid: Mapped[str | None] = mapped_column(Unicode, nullable=True)

    # defaults
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), nullable=False, default=UserStatus.pending)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_salt: Mapped[str | None] = mapped_column(Unicode, nullable=True, default=None)
    terms_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    roles: Mapped[list[UserRole]] = mapped_column(ARRAY(Enum(UserRole)), nullable=False, default=())
    description: Mapped[str] = mapped_column(UnicodeText, nullable=False, default='')
    description_rich_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary(CACHE_HASH_SIZE), nullable=True, default=None
    )
    home_point: Mapped[Point | None] = mapped_column(PointType, nullable=True, default=None)
    home_zoom: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=None)
    avatar_type: Mapped[UserAvatarType] = mapped_column(
        Enum(UserAvatarType), nullable=False, default=UserAvatarType.default
    )
    avatar_id: Mapped[str | None] = mapped_column(Unicode, nullable=True, default=None)
    # TODO: user preferences

    # relationships (nested imports to avoid circular imports)
    from changeset import Changeset
    from changeset_comment import ChangesetComment
    from diary_comment import DiaryComment
    from friendship import Friendship
    from message import Message
    from note_comment import NoteComment
    from oauth1_application import OAuth1Application
    from oauth1_token import OAuth1Token
    from oauth2_application import OAuth2Application
    from oauth2_token import OAuth2Token
    from trace_ import Trace
    from user_block import UserBlock

    changesets: Mapped[list[Changeset]] = relationship(
        back_populates='user',
        order_by='desc(Changeset.id)',
        lazy='raise',
    )
    changeset_comments: Mapped[list[ChangesetComment]] = relationship(
        back_populates='user',
        order_by='desc(ChangesetComment.created_at)',
        lazy='raise',
    )
    diary_comments: Mapped[list[DiaryComment]] = relationship(
        back_populates='user',
        order_by='desc(DiaryComment.created_at)',
        lazy='raise',
    )
    friendship_sent: Mapped[list['User']] = relationship(
        back_populates='friendship_received',
        secondary=Friendship,
        primaryjoin=id == Friendship.from_user_id,
        secondaryjoin=id == Friendship.to_user_id,
        lazy='raise',
    )
    friendship_received: Mapped[list['User']] = relationship(
        back_populates='friendship_sent',
        secondary=Friendship,
        primaryjoin=id == Friendship.to_user_id,
        secondaryjoin=id == Friendship.from_user_id,
        lazy='raise',
    )
    messages_sent: Mapped[list[Message]] = relationship(
        back_populates='from_user',
        order_by='desc(Message.created_at)',
        lazy='raise',
    )
    messages_received: Mapped[list[Message]] = relationship(
        back_populates='to_user',
        order_by='desc(Message.created_at)',
        lazy='raise',
    )
    note_comments: Mapped[list[NoteComment]] = relationship(
        back_populates='user',
        order_by='desc(NoteComment.created_at)',
        lazy='raise',
    )
    oauth1_applications: Mapped[list[OAuth1Application]] = relationship(
        back_populates='user',
        order_by='asc(OAuth1Application.id)',
        lazy='raise',
    )
    oauth1_tokens: Mapped[list[OAuth1Token]] = relationship(
        back_populates='user',
        order_by='asc(OAuth1Token.application_id)',
        lazy='raise',
    )
    oauth2_applications: Mapped[list[OAuth2Application]] = relationship(
        back_populates='user',
        order_by='asc(OAuth2Application.id)',
        lazy='raise',
    )
    oauth2_tokens: Mapped[list[OAuth2Token]] = relationship(
        back_populates='user',
        order_by='asc(OAuth2Token.application_id)',
        lazy='raise',
    )
    traces: Mapped[list[Trace]] = relationship(
        back_populates='user',
        order_by='desc(Trace.id)',
        lazy='raise',
    )
    user_blocks_given: Mapped[list[UserBlock]] = relationship(
        back_populates='from_user',
        order_by='desc(UserBlock.id)',
        lazy='raise',
    )
    user_blocks_received: Mapped[list[UserBlock]] = relationship(
        back_populates='to_user',
        order_by='desc(UserBlock.id)',
        lazy='raise',
    )

    __table_args__ = (
        UniqueConstraint(email),
        UniqueConstraint(display_name),
    )

    @validates('languages')
    def validate_languages(self, _: str, value: Sequence[str]):
        if len(value) > USER_LANGUAGES_LIMIT:
            raise ValueError('Too many languages')
        return value

    @validates('description')
    def validate_description(self, _: str, value: str):
        if len(value) > USER_DESCRIPTION_MAX_LENGTH:
            raise ValueError('Description is too long')
        return value

    @property
    def is_administrator(self) -> bool:
        """
        Check if the user is an administrator.
        """

        return UserRole.administrator in self.roles

    @property
    def is_moderator(self) -> bool:
        """
        Check if the user is a moderator.
        """

        return UserRole.moderator in self.roles or self.is_administrator

    @property
    def language_str(self) -> str:
        return ' '.join(self.languages)

    @language_str.setter
    def language_str(self, s: str) -> None:
        languages = s.split()
        languages = (t.strip()[:LANGUAGE_CODE_MAX_LENGTH].strip() for t in languages)
        languages = (normalize_language_case(t) for t in languages)
        languages = (t for t in languages if t)
        self.languages = tuple(set(languages))

    @property
    def preferred_diary_language(self) -> LanguageInfo:
        """
        Get the user's preferred diary language.
        """

        # return the first valid language
        for code in self.languages:
            if lang := get_language_info(code):
                return lang

        # fallback to default
        return get_language_info(DEFAULT_LANGUAGE)

    @property
    def changeset_max_size(self) -> int:
        """
        Get the maximum changeset size for this user.
        """

        return UserRole.get_changeset_max_size(self.roles)

    @property
    def password_hasher(self) -> PasswordHasher:
        """
        Get the password hasher for this user.
        """

        return UserRole.get_password_hasher(self.roles)

    @property
    def avatar_url(self) -> str:
        """
        Get the url for the user's avatar image.
        """

        # when using gravatar, use user id as the avatar id
        if self.avatar_type == UserAvatarType.gravatar:
            return Avatar.get_url(self.avatar_type, self.id)
        else:
            return Avatar.get_url(self.avatar_type, self.avatar_id)

    description_rich = rich_text_getter('description', TextFormat.markdown)

    # TODO: SQL
    @classmethod
    async def authenticate(cls, email_or_username: str, password: str, *, basic_request: Request | None) -> Self | None:
        """
        Authenticate a user by email or username and password.

        If `basic_request` is provided, the password will be cached for a short time.

        Returns `None` if the user is not found or the password is incorrect.
        """

        # TODO: normalize unicode & strip

        if '.' in email_or_username:
            field = 'email'
        else:
            field = 'display_name'

        user = await cls.find_one(
            {
                '$or': [
                    {field: email_or_username},
                    {field: email_or_username.lower()},  # TODO: collation?
                ],
            }
        )

        if user is None:
            logging.debug('User not found %r', email_or_username)
            return None

        # fast password cache with extra entropy
        # used primarily for api basic auth user:pass which is a hot spot
        if basic_request:
            key = '\0'.join(
                (
                    SECRET,
                    user.password_hashed,
                    basic_request.client.host,
                    basic_request.headers.get('user-agent', ''),
                    password,
                )
            )

            cache_id = Cache.hash_key(key)
            cache = await Cache.find_one_by_id(cache_id)
        else:
            cache = None

        if cache:
            ph = None
            ph_valid = cache.value == 'OK'
        else:
            ph = PasswordHash(user.password_hasher)
            ph_valid = ph.verify(user.password_hashed, user.password_salt, password)
            if basic_request:
                logging.debug('Fast password cache miss for user %r', user.id)
                await Cache.create_from_key_id(cache_id, 'OK' if ph_valid else '', ttl=FAST_PASSWORD_CACHE_EXPIRE)

        if not ph_valid:
            logging.debug('Password mismatch for user %r', user.id)
            return None

        if ph and ph.rehash_needed:
            user.password_hashed = ph.hash(password)
            user.password_salt = None
            await user.update()
            logging.debug('Rehashed password for user %r', user.id)

        return user

    @classmethod
    async def authenticate_session(cls, session_id: ObjectId, session_key: str) -> Self | None:
        """
        Authenticate a user by session ID and session key.

        Returns `None` if the session is not found or the session key is incorrect.
        """

        pipeline = [
            {'$match': {'_id': session_id}},
            {'$lookup': {'from': cls._collection_name(), 'localField': 'user_id', 'foreignField': '_id', 'as': 'user'}},
            {'$unwind': '$user'},
        ]

        cursor = UserTokenSession._collection().aggregate(pipeline)
        result = await cursor.to_list(1)

        if not result:
            logging.debug('Session (or user) not found %r', session_id)
            return None

        data: dict = result[0]
        user_d: dict = data.pop('user')
        token = UserTokenSession.model_validate(data)

        if not compare_digest(token.key_hashed, hash_hex(session_key)):
            logging.debug('Session key mismatch for session %r', session_id)
            return None

        return cls.model_validate(user_d)

    @classmethod
    async def authenticate_oauth(cls, request: Request) -> tuple[Self, Sequence[Scope]] | None:
        """
        Authenticate a user by OAuth1.0 or OAuth2.0.

        Returns `None` if the request is not an OAuth request.

        Raises `OAuthError` if the request is an invalid OAuth request.
        """

        authorization = request.headers.get('authorization')

        if not authorization:
            # oauth1 requests may use query params or body params
            oauth_version = 1
        else:
            scheme, _ = get_authorization_scheme_param(authorization)
            scheme = scheme.lower()

            if scheme == 'oauth':
                oauth_version = 1
            elif scheme == 'bearer':
                oauth_version = 2
            else:
                # not an OAuth request
                return None

        if oauth_version == 1:
            request_ = await OAuth1.convert_request(request)

            if not request_.signature:
                # not an OAuth request
                return None

            OAuth1Nonce.spend(request_.oauth_params.get('oauth_nonce'), request_.timestamp)

            token = await OAuth1.parse_and_validate(request_)
        elif oauth_version == 2:
            token = await OAuth2.parse_and_validate(request)
        else:
            raise NotImplementedError(f'Unsupported OAuth version {oauth_version}')

        if not token.authorized_at or token.revoked_at:
            raise_for().oauth_bad_user_token()

        user = await cls.find_one_by_id(token.user_id)

        if not user:
            raise_for().oauth_bad_user_token()

        return user, token.scopes

    async def home_distance_to(self, point: Point | None) -> float | None:
        return haversine_distance(self.home_point, point) if self.home_point and point else None

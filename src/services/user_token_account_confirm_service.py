import secrets

from sqlalchemy import delete, update

from src.db import DB
from src.lib.auth import auth_user
from src.lib.crypto import hash_b
from src.lib.exceptions import raise_for
from src.limits import USER_TOKEN_ACCOUNT_CONFIRM_EXPIRE
from src.models.db.user import User
from src.models.db.user_token_account_confirm import UserTokenAccountConfirm
from src.models.msgspec.user_token_struct import UserTokenStruct
from src.models.user_status import UserStatus
from src.repositories.user_token_account_confirm_repository import UserTokenAccountConfirmRepository
from src.utils import utcnow


class UserTokenAccountConfirmService:
    @staticmethod
    async def create() -> UserTokenStruct:
        """
        Create a new user account confirmation token.
        """

        token_b = secrets.token_bytes(32)
        token_hashed = hash_b(token_b, context=None)

        async with DB() as session:
            token = UserTokenAccountConfirm(
                user_id=auth_user().id,
                token_hashed=token_hashed,
                expires_at=utcnow() + USER_TOKEN_ACCOUNT_CONFIRM_EXPIRE,
            )

            session.add(token)

        return UserTokenStruct(token.id, token_b)

    @staticmethod
    async def confirm(token_struct: UserTokenStruct) -> None:
        """
        Confirm a user account.
        """

        token = await UserTokenAccountConfirmRepository.find_one_by_token_struct(token_struct)

        if not token:
            raise_for().bad_user_token_struct()

        # NOTE: potential timing attack, but the impact is negligible
        async with DB() as session, session.begin():
            stmt = (
                update(User)
                .where(
                    User.id == token.user_id,
                    User.status == UserStatus.pending,
                )
                .values({User.status: UserStatus.active})
            )

            await session.execute(stmt)

            stmt = delete(UserTokenAccountConfirm).where(
                UserTokenAccountConfirm.id == token_struct.id,
            )

            await session.execute(stmt)

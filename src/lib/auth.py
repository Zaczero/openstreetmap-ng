import logging
from base64 import b64decode
from collections.abc import Sequence
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

from fastapi import Request, Security
from fastapi.security import SecurityScopes
from fastapi.security.utils import get_authorization_scheme_param

from src.lib.exceptions import raise_for
from src.models.db.user import User
from src.models.msgspec.user_token_struct import UserTokenStruct
from src.models.scope import ExtendedScope, Scope
from src.services.auth_service import AuthService

# TODO: ACL
# TODO: more 0.7 scopes


_ALL_SCOPES = tuple(Scope.__members__.values())
_ALL_WEB_SCOPES = (*_ALL_SCOPES, ExtendedScope.web_user)


_context = ContextVar('Auth_context')


@asynccontextmanager
async def auth_context(request: Request):
    """
    Context manager for authenticating the user.

    API endpoints support basic auth and oauth.

    All endpoints support session cookies.
    """

    user, scopes = None, ()

    # api endpoints support basic auth and oauth
    if request.url.path.startswith(('/api/0.6/', '/api/0.7/')):
        authorization = request.headers.get('authorization')
        scheme, param = get_authorization_scheme_param(authorization)
        scheme = scheme.lower()

        # handle basic auth
        if scheme == 'basic':
            logging.debug('Attempting to authenticate with Basic')
            username, _, password = b64decode(param).decode().partition(':')
            if not username or not password:
                raise_for().bad_basic_auth_format()
            if user_ := await AuthService.authenticate(username, password, basic_request=request):
                user, scopes = user_, _ALL_SCOPES

        # handle oauth
        else:
            # don't rely on scheme for oauth, 1.0 may use query params
            logging.debug('Attempting to authenticate with OAuth')
            if result := await AuthService.authenticate_oauth(request):
                user, scopes = result

    # all endpoints support session cookies
    if not user and (token_str := request.session.get('session')):
        logging.debug('Attempting to authenticate with cookies')
        token_struct = UserTokenStruct.from_str(token_str)
        if user_ := await AuthService.authenticate_session(token_struct):
            user, scopes = user_, _ALL_WEB_SCOPES

    if user:
        logging.debug('Request authenticated as user %d', user.id)
        scopes = (*scopes, *user.extended_scopes)
    else:
        logging.debug('Request is not authenticated')

    token = _context.set((user, scopes))
    try:
        yield
    finally:
        _context.reset(token)


@contextmanager
def manual_auth_context(user: User):
    """
    Context manager for manually authenticating the user.
    """

    token = _context.set((user, ()))
    try:
        yield
    finally:
        _context.reset(token)


def auth_user_scopes() -> tuple[User | None, Sequence[ExtendedScope]]:
    """
    Get the authenticated user and scopes.
    """

    return _context.get()


def auth_user() -> User | None:
    """
    Get the authenticated user.
    """

    return _context.get()[0]


def auth_scopes() -> Sequence[ExtendedScope]:
    """
    Get the authenticated user's scopes.
    """

    return _context.get()[1]


def _get_user(require_scopes: SecurityScopes) -> User:
    user, user_scopes = auth_user_scopes()
    if not user:
        raise_for().unauthorized(request_basic_auth=True)
    if missing_scopes := set(require_scopes.scopes).difference(s.value for s in user_scopes):
        raise_for().insufficient_scopes(missing_scopes)
    return user


def api_user(*require_scopes: Scope | ExtendedScope) -> User:
    """
    Dependency for authenticating the api user.
    """

    return Security(
        _get_user,
        scopes=tuple(s.value for s in require_scopes),
    )


def web_user() -> User:
    """
    Dependency for authenticating the web user.
    """

    return Security(
        _get_user,
        scopes=(ExtendedScope.web_user,),
    )

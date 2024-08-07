from abc import abstractmethod
from collections.abc import Collection
from typing import TYPE_CHECKING, NoReturn

from starlette import status

from app.exceptions.api_error import APIError

if TYPE_CHECKING:
    from app.models.db.element import Element
    from app.models.element import ElementRef, VersionedElementRef


class ElementExceptionsMixin:
    @abstractmethod
    def element_not_found(self, element_ref: 'ElementRef | VersionedElementRef') -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def element_redacted(self, versioned_ref: 'VersionedElementRef') -> NoReturn:
        raise APIError(status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, detail='Element version redacted')

    @abstractmethod
    def element_redact_latest(self) -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def element_already_deleted(self, element: 'Element') -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def element_changeset_missing(self) -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def element_version_conflict(self, element: 'Element', local_version: int) -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def element_member_not_found(self, parent_ref: 'ElementRef', member_ref: 'ElementRef') -> NoReturn:
        raise NotImplementedError

    @abstractmethod
    def element_in_use(self, element: 'Element', used_by: Collection['ElementRef']) -> NoReturn:
        raise NotImplementedError

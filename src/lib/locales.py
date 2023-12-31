import logging
import pathlib

from src.config import DEFAULT_LANGUAGE


def _load_locales() -> set[str]:
    result: set[str] = set()

    for p in pathlib.Path('config/locale').iterdir():
        if not p.is_dir():
            continue

        result.add(p.name)

    return result


_locales = frozenset(_load_locales())
_locales_lower_map = {k.casefold(): k for k in _locales}

logging.info('Loaded %d locales', len(_locales))

if DEFAULT_LANGUAGE not in _locales:
    raise RuntimeError(f'{DEFAULT_LANGUAGE=!r} not found in locales')


def normalize_locale_case(code: str) -> str | None:
    """
    Normalize locale code case.

    >>> normalize_locale_case('EN')
    'en'
    >>> normalize_locale_case('NonExistent')
    None
    """

    if code in _locales:
        return code
    return _locales_lower_map.get(code.casefold(), None)

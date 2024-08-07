from collections.abc import Iterable

import cython

from app.lib.date_utils import legacy_date
from app.lib.format_style_context import format_is_json
from app.lib.xmltodict import get_xattr
from app.models.db.changeset import Changeset
from app.models.db.changeset_comment import ChangesetComment


class Changeset06Mixin:
    @staticmethod
    def encode_changesets(changesets: Iterable[Changeset]) -> dict:
        """
        >>> encode_changesets([
        ...     Changeset(...),
        ...     Changeset(...),
        ... ])
        {'changeset': [{'@id': 1, '@created_at': ..., ..., 'discussion': {'comment': [...]}}]}
        """
        if format_is_json():
            return {'changesets': tuple(_encode_changeset(changeset, is_json=True) for changeset in changesets)}
        else:
            return {'changeset': tuple(_encode_changeset(changeset, is_json=False) for changeset in changesets)}


@cython.cfunc
def _encode_changeset_comment(comment: ChangesetComment, *, is_json: cython.char) -> dict:
    """
    >>> _encode_changeset_comment(ChangesetComment(...))
    {'@uid': 1, '@user': ..., '@date': ..., 'text': 'lorem ipsum'}
    """
    xattr = get_xattr(is_json=is_json)
    return {
        xattr('id'): comment.id,
        xattr('date'): legacy_date(comment.created_at),
        xattr('uid'): comment.user_id,
        xattr('user'): comment.user.display_name,
        'text': comment.body,
    }


@cython.cfunc
def _encode_changeset(changeset: Changeset, *, is_json: cython.char) -> dict:
    """
    >>> _encode_changeset(Changeset(...))
    {'@id': 1, '@created_at': ..., ..., 'discussion': {'comment': [...]}}
    """
    if changeset.union_bounds is not None:
        xattr = get_xattr(is_json=is_json)
        minx, miny, maxx, maxy = changeset.union_bounds.bounds
        bounds_dict = {
            xattr('minlon', xml='min_lon'): minx,
            xattr('minlat', xml='min_lat'): miny,
            xattr('maxlon', xml='max_lon'): maxx,
            xattr('maxlat', xml='max_lat'): maxy,
        }
    else:
        bounds_dict = {}

    created_at = legacy_date(changeset.created_at)
    updated_at = legacy_date(changeset.updated_at)
    closed_at = legacy_date(changeset.closed_at)

    if is_json:
        return {
            'type': 'changeset',
            'id': changeset.id,
            'created_at': created_at,
            'updated_at': updated_at,
            **({'closed_at': closed_at} if (closed_at is not None) else {}),
            'open': closed_at is None,
            **(
                {
                    'uid': changeset.user_id,
                    'user': changeset.user.display_name,
                }
                if (changeset.user is not None)
                else {}
            ),
            **bounds_dict,
            'comments_count': changeset.num_comments,
            'changes_count': changeset.size,
            'tags': changeset.tags,
            **(
                {
                    'discussion': tuple(
                        _encode_changeset_comment(comment, is_json=True)  #
                        for comment in changeset.comments
                    )
                }
                if (changeset.comments is not None)
                else {}
            ),
        }
    else:
        return {
            '@id': changeset.id,
            '@created_at': created_at,
            '@updated_at': updated_at,
            **({'@closed_at': closed_at} if (closed_at is not None) else {}),
            '@open': closed_at is None,
            **(
                {
                    '@uid': changeset.user_id,
                    '@user': changeset.user.display_name,
                }
                if (changeset.user is not None)
                else {}
            ),
            **bounds_dict,
            '@comments_count': changeset.num_comments,
            '@changes_count': changeset.size,
            'tag': tuple({'@k': k, '@v': v} for k, v in changeset.tags.items()),
            **(
                {
                    'discussion': {
                        'comment': tuple(
                            _encode_changeset_comment(comment, is_json=False)  #
                            for comment in changeset.comments
                        )
                    }
                }
                if (changeset.comments is not None)
                else {}
            ),
        }

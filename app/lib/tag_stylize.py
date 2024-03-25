from collections.abc import Sequence

import cython

from app.lib.tag_stylizers.color import configure_color_style
from app.lib.tag_stylizers.comment import configure_comment_style
from app.lib.tag_stylizers.email import configure_email_style
from app.lib.tag_stylizers.osm_wiki import tag_stylize_osm_wiki
from app.lib.tag_stylizers.phone import configure_phone_style
from app.lib.tag_stylizers.url import configure_url_style
from app.lib.tag_stylizers.wikidata import configure_wikidata_style
from app.lib.tag_stylizers.wikimedia_commons import configure_wikimedia_commons_style
from app.lib.tag_stylizers.wikipedia import configure_wikipedia_style
from app.models.tag_style import TagStyleCollection

# TODO: 0.7 official reserved tag characters


def tag_stylize(tags: Sequence[TagStyleCollection]) -> None:
    """
    Style tags (colors, urls, etc.).
    """
    max_key_parts: cython.int = 5
    max_values: cython.int = 8

    for tag in tags:
        # split a:b:c keys into ['a', 'b', 'c']
        key_parts = tag.key.value.split(':', maxsplit=max_key_parts)

        # skip unexpectedly long sequences
        if len(key_parts) > max_key_parts:
            continue

        supported_key_parts = _method_keys.intersection(key_parts)
        supported_key_part = next(iter(supported_key_parts), None)
        if supported_key_part is None:
            continue

        # split a;b;c values into ['a', 'b', 'c']
        values = tag.values[0].value.split(';', maxsplit=max_values)

        # skip unexpectedly long sequences
        if len(values) > max_values:
            continue

        _method_map[supported_key_part](tag, key_parts, values)

    tag_stylize_osm_wiki(tags)


_method_map = {}
configure_color_style(_method_map)
configure_comment_style(_method_map)
configure_email_style(_method_map)
configure_phone_style(_method_map)
configure_url_style(_method_map)
configure_wikipedia_style(_method_map)
configure_wikidata_style(_method_map)
configure_wikimedia_commons_style(_method_map)

_method_keys = frozenset(_method_map.keys())

import logging
from asyncio import TaskGroup
from collections.abc import Sequence
from urllib.parse import urlencode

import numpy as np
from httpx import HTTPError
from shapely import MultiPolygon, Point, Polygon, box, get_coordinates, lib

from app.config import NOMINATIM_URL
from app.lib.feature_prefix import features_prefixes
from app.lib.translation import primary_translation_locale
from app.limits import (
    NOMINATIM_CACHE_LONG_EXPIRE,
    NOMINATIM_CACHE_SHORT_EXPIRE,
    NOMINATIM_HTTP_LONG_TIMEOUT,
    NOMINATIM_HTTP_SHORT_TIMEOUT,
)
from app.models.db.element import Element
from app.models.element_ref import ElementRef
from app.models.search_result import SearchResult
from app.queries.element_query import ElementQuery
from app.services.cache_service import CacheService
from app.utils import HTTP, JSON_DECODE

_cache_context = 'Nominatim'


class NominatimQuery:
    @staticmethod
    async def reverse_name(point: Point, zoom: int) -> str:
        """
        Reverse geocode a point into a human-readable name.
        """
        x, y = get_coordinates(point)[0].tolist()
        path = '/reverse?' + urlencode(
            {
                'format': 'jsonv2',
                'lon': f'{x:.7f}',
                'lat': f'{y:.7f}',
                'zoom': zoom,
                'accept-language': primary_translation_locale(),
            }
        )

        async def factory() -> bytes:
            logging.debug('Nominatim reverse cache miss for path %r', path)
            r = await HTTP.get(NOMINATIM_URL + path, timeout=NOMINATIM_HTTP_SHORT_TIMEOUT.total_seconds())
            r.raise_for_status()
            return r.content

        try:
            cache = await CacheService.get(
                path,
                context=_cache_context,
                factory=factory,
                ttl=NOMINATIM_CACHE_LONG_EXPIRE,
            )
            return JSON_DECODE(cache.value)['display_name']
        except HTTPError:
            logging.warning('Nominatim reverse geocoding failed', exc_info=True)
            # always succeed, return coordinates as a fallback
            return f'{y:.5f}, {x:.5f}'

    @staticmethod
    async def search(
        *,
        q: str,
        bounds: Polygon | MultiPolygon | None = None,
        at_sequence_id: int | None,
        limit: int,
    ) -> list[SearchResult]:
        """
        Search for a location by name and optional bounds.
        """
        polygons = bounds.geoms if isinstance(bounds, MultiPolygon) else (bounds,)

        async with TaskGroup() as tg:
            tasks = tuple(
                tg.create_task(
                    _search(
                        q=q,
                        bounds=polygon,
                        at_sequence_id=at_sequence_id,
                        limit=limit,
                    )
                )
                for polygon in polygons
            )

        # results are sorted from highest to lowest importance
        return sorted(
            (result for task in tasks for result in task.result()),
            key=lambda r: r.importance,
            reverse=True,
        )


async def _search(
    *,
    q: str,
    bounds: Polygon | None,
    at_sequence_id: int | None,
    limit: int,
) -> list[SearchResult]:
    path = '/search?' + urlencode(
        {
            'format': 'jsonv2',
            'q': q,
            'limit': limit,
            **(
                {
                    'viewbox': ','.join(f'{x:.7f}' for x in bounds.bounds),
                    'bounded': 1,
                }
                if (bounds is not None)
                else {}
            ),
            'accept-language': primary_translation_locale(),
        }
    )

    async def factory() -> bytes:
        logging.debug('Nominatim search cache miss for path %r', path)
        r = await HTTP.get(NOMINATIM_URL + path, timeout=NOMINATIM_HTTP_LONG_TIMEOUT.total_seconds())
        r.raise_for_status()
        return r.content

    # cache only stable queries
    if bounds is None:
        cache = await CacheService.get(
            path,
            context=_cache_context,
            factory=factory,
            hash_key=True,
            ttl=NOMINATIM_CACHE_SHORT_EXPIRE,
        )
        response = cache.value
    else:
        response = await factory()

    refs: list[ElementRef] = []
    entries: list[dict] = []
    for entry in JSON_DECODE(response):
        # some results are abstract and have no osm_type/osm_id
        osm_type = entry.get('osm_type')
        osm_id = entry.get('osm_id')
        if (osm_type is None) or (osm_id is None):
            continue

        ref = ElementRef(osm_type, osm_id)
        refs.append(ref)
        entries.append(entry)

    # fetch elements in the order of entries
    elements: Sequence[Element | None]
    elements = await ElementQuery.get_by_refs(refs, at_sequence_id=at_sequence_id, limit=len(refs))
    ref_element_map: dict[ElementRef, Element] = {ElementRef(e.type, e.id): e for e in elements}
    elements = tuple(ref_element_map.get(ref) for ref in refs)  # not all elements may be found in the database

    prefixes = features_prefixes(elements)
    result: list[SearchResult] = []
    for entry, element, prefix in zip(entries, elements, prefixes, strict=True):
        # skip non-existing elements
        if element is None or not element.visible:
            continue
        if prefix is None:
            continue

        bbox = entry['boundingbox']
        miny = float(bbox[0])
        maxy = float(bbox[1])
        minx = float(bbox[2])
        maxx = float(bbox[3])
        geometry: Polygon = box(minx, miny, maxx, maxy)

        lon = (minx + maxx) / 2
        lat = (miny + maxy) / 2
        point = lib.points(np.array((lon, lat), np.float64))

        result.append(
            SearchResult(
                element=element,
                rank=entry['place_rank'],
                importance=entry['importance'],
                prefix=prefix,
                display_name=entry['display_name'],
                point=point,
                bounds=geometry,
            )
        )
    return result

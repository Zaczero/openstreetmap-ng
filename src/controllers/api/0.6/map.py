from typing import Annotated

from fastapi import APIRouter, Query

from src.lib.exceptions import raise_for
from src.lib.format.format06 import Format06
from src.lib_cython.geo_utils import parse_bbox
from src.lib_cython.xmltodict import XAttr
from src.limits import MAP_QUERY_AREA_MAX_SIZE, MAP_QUERY_LEGACY_NODES_LIMIT
from src.repositories.element_repository import ElementRepository

router = APIRouter()


@router.get('/map')
@router.get('/map.xml')
@router.get('/map.json')
async def map_read(
    bbox: Annotated[str, Query(min_length=1)],
) -> dict:
    geometry = parse_bbox(bbox)

    if geometry.area > MAP_QUERY_AREA_MAX_SIZE:
        raise_for().map_query_area_too_big()

    elements = await ElementRepository.find_many_by_query(
        geometry,
        nodes_limit=MAP_QUERY_LEGACY_NODES_LIMIT,
        legacy_nodes_limit=True,
    )

    minx, miny, maxx, maxy = geometry.bounds

    return {
        'bounds': {
            XAttr('minlon'): minx,
            XAttr('minlat'): miny,
            XAttr('maxlon'): maxx,
            XAttr('maxlat'): maxy,
        },
        **Format06.encode_elements(elements),
    }

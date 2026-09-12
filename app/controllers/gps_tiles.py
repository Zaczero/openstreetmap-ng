from fastapi import APIRouter, Response
from shapely import MultiLineString
from starlette import status

from app.config import STATIC_CACHE_MAX_AGE, STATIC_CACHE_STALE
from app.lib.geo.gps_tile import empty_gps_tile_png, render_gps_tile_png
from app.lib.geo.slippy import tile_polygon, tile_xyz_valid
from app.middlewares.headers_middleware import cache_control
from app.queries.trace_query import TraceQuery

router = APIRouter()

_EMPTY = empty_gps_tile_png()
_PNG = 'image/png'


@router.get('/gps/lines/{z:int}/{x:int}/{y:int}.png')
@router.get('/gps/lines/{z:int}/{x:int}/{y:int}')
@cache_control(STATIC_CACHE_MAX_AGE, STATIC_CACHE_STALE)
async def gps_lines_tile(z: int, x: int, y: int):
    """Public GPS-trace overlay tiles, same path shape as gps.tile.openstreetmap.org."""
    if not tile_xyz_valid(z, x, y):
        return Response(None, status.HTTP_400_BAD_REQUEST)

    geometry = tile_polygon(z, x, y)
    traces = await TraceQuery.find_by_geom(
        geometry,
        identifiable_trackable=True,
        visibilities=['identifiable', 'public'],
        limit=500,
    )
    if not traces:
        return Response(_EMPTY, media_type=_PNG)

    lines = [
        line
        for trace in traces
        for line in trace['segments'].geoms
        if not line.is_empty
    ]
    png = render_gps_tile_png(MultiLineString(lines), z, x, y)
    return Response(png, media_type=_PNG)

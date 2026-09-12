from io import BytesIO

from PIL import Image
from shapely import LineString, MultiLineString

from app.lib.geo.gps_tile import empty_gps_tile_png, render_gps_tile_png
from app.lib.geo.slippy import lonlat_to_tile


def test_empty_tile_is_transparent_png():
    raw = empty_gps_tile_png()
    img = Image.open(BytesIO(raw))
    assert img.size == (256, 256)
    assert img.mode == 'RGBA'
    extrema = img.getextrema()
    assert extrema[3] == (0, 0)  # fully transparent alpha


def test_render_empty_multilinestring():
    raw = render_gps_tile_png(MultiLineString(), 0, 0, 0)
    img = Image.open(BytesIO(raw))
    assert img.size == (256, 256)
    assert img.getextrema()[3] == (0, 0)


def test_render_sample_gpx_segment_paints_pixels():
    lon, lat = 20.8726996, 51.8583922
    z = 14
    x, y = lonlat_to_tile(lon, lat, z)
    # A short east-west segment around the sample GPX start.
    line = LineString((
        (lon - 0.001, lat),
        (lon + 0.001, lat),
    ))
    raw = render_gps_tile_png(MultiLineString([line]), z, x, y)
    img = Image.open(BytesIO(raw))
    assert img.size == (256, 256)
    alpha = img.getchannel('A')
    assert max(alpha.getdata()) > 0

from io import BytesIO

from PIL import Image, ImageDraw
from shapely import MultiLineString

from app.lib.geo.slippy import TILE_SIZE, lonlat_to_tile_pixels

# Matches the OSM.org public GPS traces overlay (magenta, semi-opaque).
_LINE_FILL = (226, 26, 140, 220)
_LINE_WIDTH = 2


def render_gps_tile_png(
    segments: MultiLineString,
    z: int,
    x: int,
    y: int,
    *,
    size: int = TILE_SIZE,
) -> bytes:
    """Rasterize trace segments that fall in slippy tile (z, x, y) to a PNG."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    if segments.is_empty:
        return _png_bytes(img)

    draw = ImageDraw.Draw(img, 'RGBA')
    geoms = segments.geoms if hasattr(segments, 'geoms') else (segments,)
    for line in geoms:
        coords = list(line.coords)
        if len(coords) < 2:
            continue
        pixels = [
            lonlat_to_tile_pixels(lon, lat, z, x, y, size=size)
            for lon, lat in coords
        ]
        draw.line(pixels, fill=_LINE_FILL, width=_LINE_WIDTH, joint='curve')
    return _png_bytes(img)


def empty_gps_tile_png(*, size: int = TILE_SIZE) -> bytes:
    return _png_bytes(Image.new('RGBA', (size, size), (0, 0, 0, 0)))


def _png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()

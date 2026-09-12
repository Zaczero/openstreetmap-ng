import math

from shapely import Polygon

TILE_SIZE = 256
MAX_ZOOM = 18


def tile_xyz_valid(z: int, x: int, y: int) -> bool:
    if z < 0 or z > MAX_ZOOM:
        return False
    n = 1 << z
    return 0 <= x < n and 0 <= y < n


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    """Return the slippy-map tile (x, y) containing lon/lat at zoom z."""
    n = 1 << z
    lat = min(max(lat, -85.05112878), 85.05112878)
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int(
        (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * n
    )
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def lonlat_to_tile_pixels(
    lon: float, lat: float, z: int, x: int, y: int, *, size: int = TILE_SIZE
) -> tuple[float, float]:
    """Pixel coordinates of lon/lat inside tile (z, x, y)."""
    n = float(1 << z)
    lat = min(max(lat, -85.05112878), 85.05112878)
    px = ((lon + 180.0) / 360.0 * n - x) * size
    lat_rad = math.radians(lat)
    py = (
        (
            1.0
            - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi
        )
        / 2.0
        * n
        - y
    ) * size
    return px, py


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) in WGS84 degrees for a slippy tile."""
    n = float(1 << z)
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
    south = math.degrees(
        math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y + 1) / n)))
    )
    return west, south, east, north


def tile_polygon(z: int, x: int, y: int) -> Polygon:
    west, south, east, north = tile_bounds(z, x, y)
    return Polygon((
        (west, south),
        (east, south),
        (east, north),
        (west, north),
        (west, south),
    ))

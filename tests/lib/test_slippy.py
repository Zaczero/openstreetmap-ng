import math

from app.lib.geo.slippy import (
    lonlat_to_tile,
    lonlat_to_tile_pixels,
    tile_bounds,
    tile_polygon,
    tile_xyz_valid,
)


def test_tile_xyz_valid():
    assert tile_xyz_valid(0, 0, 0)
    assert tile_xyz_valid(14, 9149, 5451)
    assert not tile_xyz_valid(-1, 0, 0)
    assert not tile_xyz_valid(19, 0, 0)
    assert not tile_xyz_valid(1, 2, 0)
    assert not tile_xyz_valid(1, 0, 2)


def test_lonlat_to_tile_null_island_z0():
    assert lonlat_to_tile(0, 0, 0) == (0, 0)


def test_lonlat_to_tile_sample_gpx():
    # tests/data/8473730.gpx starts near 20.8727E, 51.8584N
    x, y = lonlat_to_tile(20.8726996, 51.8583922, 14)
    west, south, east, north = tile_bounds(14, x, y)
    assert west <= 20.8726996 <= east
    assert south <= 51.8583922 <= north


def test_tile_bounds_z0_covers_world():
    west, south, east, north = tile_bounds(0, 0, 0)
    assert west == -180
    assert east == 180
    assert math.isclose(south, -85.05112878, abs_tol=1e-6)
    assert math.isclose(north, 85.05112878, abs_tol=1e-6)


def test_lonlat_to_tile_pixels_in_range():
    z, x, y = 14, *lonlat_to_tile(20.8726996, 51.8583922, 14)
    px, py = lonlat_to_tile_pixels(20.8726996, 51.8583922, z, x, y)
    assert 0 <= px <= 256
    assert 0 <= py <= 256


def test_tile_polygon_closed():
    poly = tile_polygon(8, 140, 85)
    assert poly.is_valid
    assert poly.area > 0
    assert poly.exterior.coords[0] == poly.exterior.coords[-1]

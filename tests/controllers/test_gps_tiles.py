from io import BytesIO
from pathlib import Path

from httpx import AsyncClient
from PIL import Image

from app.lib.geo.slippy import lonlat_to_tile
from app.models.proto.trace_pb2 import Metadata, UploadRequest, UploadResponse, Visibility

_GPX_BYTES = Path('tests/data/8473730.gpx').read_bytes()
_SAMPLE_LON = 20.8726996
_SAMPLE_LAT = 51.8583922


async def _upload_public_trace(client: AsyncClient) -> int:
    client.headers['Authorization'] = 'User user1'
    r = await client.post(
        '/rpc/trace.Service/Upload',
        headers={'Content-Type': 'application/proto'},
        content=UploadRequest(
            file=_GPX_BYTES,
            metadata=Metadata(
                name='gps-tile.gpx',
                description='Public GPS tile fixture',
                tags=['gps-tile'],
                visibility=Visibility.Value('identifiable'),
            ),
        ).SerializeToString(),
    )
    assert r.is_success, r.text
    client.headers.pop('Authorization', None)
    return int(UploadResponse.FromString(r.content).id)


async def test_gps_tile_rejects_out_of_range(client: AsyncClient):
    r = await client.get('/gps/lines/19/0/0.png')
    assert r.status_code == 400
    r = await client.get('/gps/lines/1/4/0')
    assert r.status_code == 400


async def test_gps_tile_empty_ocean_is_transparent_png(client: AsyncClient):
    # z=4 x=0 y=8 is over the South Pacific — no traces expected.
    r = await client.get('/gps/lines/4/0/8.png')
    assert r.is_success, r.text
    assert r.headers['content-type'].startswith('image/png')
    img = Image.open(BytesIO(r.content))
    assert img.size == (256, 256)
    assert img.getextrema()[3] == (0, 0)


async def test_gps_tile_renders_uploaded_public_trace(client: AsyncClient):
    await _upload_public_trace(client)
    z = 14
    x, y = lonlat_to_tile(_SAMPLE_LON, _SAMPLE_LAT, z)
    r = await client.get(f'/gps/lines/{z}/{x}/{y}.png')
    assert r.is_success, r.text
    assert r.headers['content-type'].startswith('image/png')
    img = Image.open(BytesIO(r.content))
    assert img.size == (256, 256)
    assert max(img.getchannel('A').getdata()) > 0

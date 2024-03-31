import pytest
from httpx import AsyncClient

from app.config import LEGACY_HIGH_PRECISION_TIME
from app.format06 import Format06
from app.lib.xmltodict import XMLToDict

pytestmark = pytest.mark.anyio


async def test_element_crud(client: AsyncClient):
    assert LEGACY_HIGH_PRECISION_TIME
    client.headers['Authorization'] = 'User user1'

    # create changeset
    r = await client.put(
        '/api/0.6/changeset/create',
        content=XMLToDict.unparse(
            {
                'osm': {
                    'changeset': {
                        'tag': [
                            {'@k': 'created_by', '@v': test_element_crud.__name__},
                        ]
                    }
                }
            }
        ),
    )
    assert r.is_success
    changeset_id = int(r.text)

    # read changeset
    r = await client.get(f'/api/0.6/changeset/{changeset_id}')
    assert r.is_success
    changeset: dict = XMLToDict.parse(r.content)['osm']['changeset']

    last_updated_at = changeset['@updated_at']

    # create node
    r = await client.put(
        '/api/0.6/node/create',
        content=XMLToDict.unparse(
            {
                'osm': {
                    'node': {
                        '@changeset': changeset_id,
                        '@lon': 1,
                        '@lat': 2,
                        'tag': [
                            {'@k': 'created_by', '@v': test_element_crud.__name__},
                            {'@k': 'update_me', '@v': 'update_me'},
                            {'@k': 'remove_me', '@v': 'remove_me'},
                        ],
                    }
                }
            }
        ),
    )
    assert r.is_success
    node_id = int(r.text)

    # read changeset
    r = await client.get(f'/api/0.6/changeset/{changeset_id}')
    assert r.is_success
    changeset: dict = XMLToDict.parse(r.content)['osm']['changeset']

    assert changeset['@updated_at'] > last_updated_at
    assert changeset['@min_lon'] == 1
    assert changeset['@max_lon'] == 1
    assert changeset['@min_lat'] == 2
    assert changeset['@max_lat'] == 2
    assert changeset['@changes_count'] == 1

    # read osmChange
    r = await client.get(f'/api/0.6/changeset/{changeset_id}/download')
    assert r.is_success
    action: tuple = XMLToDict.parse(r.content)['osmChange'][-1]
    assert action[0] == 'create'
    assert len(action[1]) == 1
    element: tuple = action[1][0]
    assert element[0] == 'node'
    node: dict = element[1]
    tags = Format06.decode_tags_and_validate(node['tag'])

    assert node['@id'] == node_id
    assert node['@visible'] is True
    assert node['@version'] == 1
    assert node['@changeset'] == changeset_id
    assert node['@timestamp'] == changeset['@updated_at']
    assert node['@lon'] == 1
    assert node['@lat'] == 2
    assert len(tags) == 3
    assert tags['update_me'] == 'update_me'
    assert tags['remove_me'] == 'remove_me'

    last_updated_at = changeset['@updated_at']

    # update node
    r = await client.put(
        f'/api/0.6/node/{node_id}',
        content=XMLToDict.unparse(
            {
                'osm': {
                    'node': {
                        '@changeset': changeset_id,
                        '@version': 1,
                        '@lon': 3,
                        '@lat': 4,
                        'tag': [
                            {'@k': 'created_by', '@v': test_element_crud.__name__},
                            {'@k': 'update_me', '@v': 'updated'},
                        ],
                    }
                }
            }
        ),
    )
    assert r.is_success
    version = int(r.text)

    assert version == 2

    # read changeset
    r = await client.get(f'/api/0.6/changeset/{changeset_id}')
    assert r.is_success
    changeset: dict = XMLToDict.parse(r.content)['osm']['changeset']

    assert changeset['@updated_at'] > last_updated_at
    assert changeset['@min_lon'] == 1
    assert changeset['@max_lon'] == 3
    assert changeset['@min_lat'] == 2
    assert changeset['@max_lat'] == 4
    assert changeset['@changes_count'] == 2

    # read osmChange
    r = await client.get(f'/api/0.6/changeset/{changeset_id}/download')
    assert r.is_success
    action: tuple = XMLToDict.parse(r.content)['osmChange'][-1]
    assert action[0] == 'modify'
    assert len(action[1]) == 1
    element: tuple = action[1][0]
    assert element[0] == 'node'
    node: dict = element[1]
    tags = Format06.decode_tags_and_validate(node['tag'])

    assert node['@id'] == node_id
    assert node['@visible'] is True
    assert node['@version'] == 2
    assert node['@changeset'] == changeset_id
    assert node['@timestamp'] == changeset['@updated_at']
    assert node['@lon'] == 3
    assert node['@lat'] == 4
    assert len(tags) == 2
    assert tags['update_me'] == 'updated'
    assert 'remove_me' not in tags

    last_updated_at = changeset['@updated_at']

    # delete node
    r = await client.request(
        'DELETE',
        f'/api/0.6/node/{node_id}',
        content=XMLToDict.unparse(
            {
                'osm': {
                    'node': {
                        '@changeset': changeset_id,
                        '@version': 2,
                        '@lon': 5,
                        '@lat': 6,
                        'tag': [
                            {'@k': 'created_by', '@v': test_element_crud.__name__},
                        ],
                    }
                }
            }
        ),
    )
    assert r.is_success
    version = int(r.text)

    assert version == 3

    # read changeset
    r = await client.get(f'/api/0.6/changeset/{changeset_id}')
    assert r.is_success
    changeset: dict = XMLToDict.parse(r.content)['osm']['changeset']

    assert changeset['@updated_at'] > last_updated_at
    assert changeset['@min_lon'] == 1
    assert changeset['@max_lon'] == 3
    assert changeset['@min_lat'] == 2
    assert changeset['@max_lat'] == 4
    assert changeset['@changes_count'] == 3

    # read osmChange
    r = await client.get(f'/api/0.6/changeset/{changeset_id}/download')
    assert r.is_success
    action: tuple = XMLToDict.parse(r.content)['osmChange'][-1]
    assert action[0] == 'delete'
    assert len(action[1]) == 1
    element: tuple = action[1][0]
    assert element[0] == 'node'
    node: dict = element[1]

    assert node['@id'] == node_id
    assert node['@visible'] is False
    assert node['@version'] == 3
    assert node['@changeset'] == changeset_id
    assert node['@timestamp'] == changeset['@updated_at']
    assert '@lon' not in node
    assert '@lat' not in node
    assert 'tag' not in node

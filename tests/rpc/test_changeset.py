from httpx import AsyncClient
from polyline_rs import encode_lonlat
from shapely import Point

from app.lib.io.xml_codec import XMLToDict
from app.models.db.element import ElementInit
from app.models.element import ElementId
from app.models.proto.changeset_pb2 import GetDiffRequest, GetDiffResponse
from app.models.types import ChangesetId
from app.services.optimistic_diff import OptimisticDiff
from speedup import element_id, typed_element_id


async def _create_changeset(client: AsyncClient) -> ChangesetId:
    client.headers['Authorization'] = 'User user1'
    response = await client.put(
        '/api/0.6/changeset/create',
        content=XMLToDict.unparse({
            'osm': {'changeset': {'tag': [{'@k': 'created_by', '@v': 'tests'}]}}
        }),
    )
    assert response.is_success, response.text
    return ChangesetId(int(response.text))


async def _get_diff(client: AsyncClient, changeset_id: ChangesetId):
    response = await client.post(
        '/rpc/changeset.Service/GetDiff',
        headers={'Content-Type': 'application/proto'},
        content=GetDiffRequest(id=changeset_id).SerializeToString(),
    )
    assert response.is_success, response.text
    return GetDiffResponse.FromString(response.content)


async def test_get_diff_collapses_multiple_versions(
    client: AsyncClient, changeset_id: ChangesetId
):
    node_ref = typed_element_id('node', ElementId(-1))
    nodes: list[ElementInit] = [
        {
            'changeset_id': changeset_id,
            'typed_id': node_ref,
            'version': version,
            'visible': True,
            'tags': {},
            'point': Point(version, version),
            'members': None,
            'members_roles': None,
        }
        for version in range(1, 4)
    ]
    assigned_ref_map = await OptimisticDiff.run(nodes)
    node_id = assigned_ref_map[node_ref][0]

    diff = await _get_diff(client, changeset_id)

    assert diff.num_elements == 1
    assert diff.num_truncated == 0
    assert not diff.context_truncated
    assert not diff.before.nodes
    assert not diff.before.ways
    assert not diff.after.ways
    assert len(diff.after.nodes) == 1
    assert diff.after.nodes[0].id == node_id
    assert diff.after.nodes[0].location.lon == 3
    assert diff.after.nodes[0].location.lat == 3


async def test_get_diff_uses_changeset_snapshot_for_way_members(
    client: AsyncClient, changeset_id: ChangesetId
):
    node1_ref = typed_element_id('node', ElementId(-1))
    node2_ref = typed_element_id('node', ElementId(-2))
    way_ref = typed_element_id('way', ElementId(-1))
    base_elements: list[ElementInit] = [
        {
            'changeset_id': changeset_id,
            'typed_id': node1_ref,
            'version': 1,
            'visible': True,
            'tags': {},
            'point': Point(0, 0),
            'members': None,
            'members_roles': None,
        },
        {
            'changeset_id': changeset_id,
            'typed_id': node2_ref,
            'version': 1,
            'visible': True,
            'tags': {},
            'point': Point(1, 0),
            'members': None,
            'members_roles': None,
        },
        {
            'changeset_id': changeset_id,
            'typed_id': way_ref,
            'version': 1,
            'visible': True,
            'tags': {'highway': 'residential'},
            'point': None,
            'members': [node1_ref, node2_ref],
            'members_roles': None,
        },
    ]
    assigned_ref_map = await OptimisticDiff.run(base_elements)
    node1_id = assigned_ref_map[node1_ref][0]
    node2_id = assigned_ref_map[node2_ref][0]
    way_id = assigned_ref_map[way_ref][0]

    move_changeset_id = await _create_changeset(client)
    await OptimisticDiff.run([
        {
            'changeset_id': move_changeset_id,
            'typed_id': node2_id,
            'version': 2,
            'visible': True,
            'tags': {},
            'point': Point(2, 0),
            'members': None,
            'members_roles': None,
        }
    ])

    target_changeset_id = await _create_changeset(client)
    await OptimisticDiff.run([
        {
            'changeset_id': target_changeset_id,
            'typed_id': way_id,
            'version': 2,
            'visible': True,
            'tags': {'highway': 'residential', 'surface': 'paved'},
            'point': None,
            'members': [node1_id, node2_id],
            'members_roles': None,
        }
    ])

    diff = await _get_diff(client, target_changeset_id)

    expected_line = encode_lonlat([[0, 0], [2, 0]], 6)
    assert diff.num_elements == 1
    assert [way.id for way in diff.before.ways] == [element_id(way_id)]
    assert [way.id for way in diff.after.ways] == [element_id(way_id)]
    assert diff.before.ways[0].line == expected_line
    assert diff.after.ways[0].line == expected_line


async def test_get_diff_create_then_delete_is_net_empty(
    client: AsyncClient, changeset_id: ChangesetId
):
    node_ref = typed_element_id('node', ElementId(-1))
    assigned_ref_map = await OptimisticDiff.run([
        {
            'changeset_id': changeset_id,
            'typed_id': node_ref,
            'version': 1,
            'visible': True,
            'tags': {},
            'point': Point(1, 2),
            'members': None,
            'members_roles': None,
        }
    ])
    node_id = assigned_ref_map[node_ref][0]
    await OptimisticDiff.run([
        {
            'changeset_id': changeset_id,
            'typed_id': node_id,
            'version': 2,
            'visible': False,
            'tags': None,
            'point': None,
            'members': None,
            'members_roles': None,
        }
    ])

    diff = await _get_diff(client, changeset_id)

    assert diff.num_elements == 1
    assert not diff.before.nodes
    assert not diff.before.ways
    assert not diff.after.nodes
    assert not diff.after.ways

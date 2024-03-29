import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_note_crud(client: AsyncClient):
    client.headers['Authorization'] = 'User user1'

    # create note
    r = await client.post(
        '/api/0.6/notes.json',
        params={'lon': 0, 'lat': 0, 'text': 'create'},
    )
    assert r.is_success
    props: dict = r.json()['properties']
    note_id: int = props['id']
    comments: list[dict] = props['comments']

    assert props['status'] == 'open'
    assert len(comments) == 1
    assert comments[0]['user'] == 'user1'
    assert comments[0]['action'] == 'opened'
    assert comments[0]['text'] == 'create'

    # read note
    r = await client.get(f'/api/0.6/notes/{note_id}.json')
    assert r.is_success
    assert r.json()['properties'] == props

    # comment note
    r = await client.post(
        f'/api/0.6/notes/{note_id}/comment.json',
        params={'text': 'comment'},
    )
    assert r.is_success
    props: dict = r.json()['properties']
    comments = props['comments']

    assert props['status'] == 'open'
    assert len(comments) == 2
    assert comments[0]['user'] == 'user1'
    assert comments[0]['action'] == 'commented'
    assert comments[0]['text'] == 'comment'

    # resolve note
    r = await client.post(
        f'/api/0.6/notes/{note_id}/close.json',
        params={'text': 'resolve'},
    )
    assert r.is_success
    props: dict = r.json()['properties']
    comments = props['comments']

    assert props['status'] == 'closed'
    assert len(comments) == 3
    assert comments[0]['user'] == 'user1'
    assert comments[0]['action'] == 'closed'
    assert comments[0]['text'] == 'resolve'

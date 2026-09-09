from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import note_service
from app.services.note_service import NoteService


@pytest.fixture
def storage(monkeypatch):
    conn = object()
    transaction_closed = False

    @asynccontextmanager
    async def database(write):
        nonlocal transaction_closed
        assert write is True
        yield conn
        transaction_closed = True

    async def notify(*_args):
        assert transaction_closed

    note = {
        'id': 7,
        'tags': {'source': 'survey', 'hashtags': '#old'},
        'hidden_at': None,
        'closed_at': None,
    }
    fetch = AsyncMock(return_value=note)
    insert = AsyncMock(return_value=(91, datetime.now(UTC)))
    update = AsyncMock()
    notifications = AsyncMock(side_effect=notify)
    monkeypatch.setattr(note_service, 'db', database)
    monkeypatch.setattr(note_service, 'db_fetchone', fetch)
    monkeypatch.setattr(note_service, 'db_insert', insert)
    monkeypatch.setattr(note_service, 'db_update', update)
    monkeypatch.setattr(note_service, 'audit', AsyncMock())
    monkeypatch.setattr(note_service, 'auth_user', lambda **_kwargs: {'id': 12})
    monkeypatch.setattr(note_service, 'auth_scopes', lambda: frozenset(('web_user',)))
    monkeypatch.setattr(note_service, 'user_is_moderator', lambda _user: False)
    monkeypatch.setattr(note_service, '_send_activity_email', notifications)
    monkeypatch.setattr(
        note_service, 'UserSubscriptionService', SimpleNamespace(subscribe=AsyncMock())
    )
    return conn, note, fetch, insert, update, notifications


async def test_new_hashtags_store_full_snapshot_in_locked_transaction(storage):
    conn, note, fetch, insert, update, notifications = storage
    await NoteService.comment(7, 'Checked #new', 'commented')
    values = insert.call_args.args[1]
    expected = {'source': 'survey', 'hashtags': '#new'}
    assert values['body'] == 'Checked'
    assert values['tags'] == expected
    assert update.call_args.args[1]['tags'] == expected
    assert insert.call_args.kwargs['conn'] is conn
    assert update.call_args.kwargs['conn'] is conn
    assert fetch.call_args.kwargs['conn'] is conn
    assert 'FOR UPDATE' in ''.join(fetch.call_args.args[1].strings)
    assert note['tags']['hashtags'] == '#old'
    notifications.assert_awaited_once()
    assert notifications.call_args.args[1]['tags'] == expected


@pytest.mark.parametrize('text', ['No change', 'Again #old', ''])
async def test_unchanged_tags_do_not_replace_note_or_create_snapshot(storage, text):
    _conn, _note, _fetch, insert, update, _notifications = storage
    await NoteService.comment(7, text, 'commented')
    assert insert.call_args.args[1]['tags'] is None
    assert insert.call_args.args[1]['body'] == text
    assert 'tags' not in update.call_args.args[1]


async def test_create_saves_hashtags_in_note_and_first_comment(storage, monkeypatch):
    _conn, _note, _fetch, insert, _update, _notifications = storage
    monkeypatch.setattr(note_service, 'validate_geometry', lambda point: point)
    await NoteService.create(0, 0, 'A road #survey')
    note_call, comment_call = insert.call_args_list
    assert note_call.args[0] == 'note'
    assert note_call.args[1]['tags'] == {'hashtags': '#survey'}
    assert comment_call.args[0] == 'note_comment'
    assert comment_call.args[1]['tags'] == {'hashtags': '#survey'}
    assert comment_call.args[1]['body'] == 'A road'

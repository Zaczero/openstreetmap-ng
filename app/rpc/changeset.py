from asyncio import TaskGroup
from datetime import date, datetime, time, timedelta
from typing import override

from connectrpc.request import RequestContext
from shapely import Point, get_coordinates, measurement, set_srid

from app.config import (
    CHANGESET_COMMENTS_PAGE_SIZE,
    CHANGESET_QUERY_WEB_LIMIT,
    NEARBY_USERS_RADIUS_METERS,
)
from app.exceptions.context import raise_for
from app.format import FormatRender
from app.format.element_list import FormatElementList
from app.lib.auth.context import require_web_user
from app.lib.geo.distance import meters_to_degrees
from app.lib.geo.parse import parse_bbox
from app.lib.render.rich_text import process_rich_text_plain
from app.lib.standard.feedback import StandardFeedback
from app.lib.standard.pagination import (
    StandardPaginationRequestLike,
    sp_paginate_table,
)
from app.lib.text.translation import t
from app.models.db.changeset_comment import (
    ChangesetComment,
    changeset_comments_resolve_rich_text,
)
from app.models.db.element import Element
from app.models.db.user import user_proto
from app.models.element import TypedElementId
from app.models.proto.changeset_connect import (
    Service,
    ServiceASGIApplication,
)
from app.models.proto.changeset_pb2 import (
    AddCommentRequest,
    AddCommentResponse,
    Data,
    GetCommentsRequest,
    GetCommentsResponse,
    GetDiffRequest,
    GetDiffResponse,
    GetMapRequest,
    GetMapResponse,
    GetRequest,
    GetResponse,
)
from app.models.proto.element_pb2 import RenderData
from app.models.types import ChangesetId, SequenceId
from app.queries.changeset_query import (
    ChangesetBoundsQuery,
    ChangesetCommentQuery,
    ChangesetQuery,
)
from app.queries.element_query import ElementQuery
from app.queries.user_follow_query import UserFollowQuery
from app.queries.user_query import UserQuery
from app.queries.user_subscription_query import UserSubscriptionQuery
from app.services.changeset_service import ChangesetCommentService
from app.validators.unicode import normalize_display_name
from speedup import element_type, split_typed_element_id

_CHANGESET_DIFF_ELEMENTS_LIMIT = 120
_CHANGESET_DIFF_CONTEXT_LIMIT = 50_000


class _Service(Service):
    @override
    async def get_map(self, request: GetMapRequest, ctx: RequestContext):
        geometry = parse_bbox(request.bbox) if request.HasField('bbox') else None
        scope = request.scope if request.HasField('scope') else None

        if request.HasField('display_name'):
            target_user = await UserQuery.find_by_display_name(
                normalize_display_name(request.display_name)
            )
            user_ids = [target_user['id']] if target_user is not None else []
        else:
            user_ids = None

        if scope is None:
            pass

        elif scope == GetMapRequest.Scope.nearby:
            current_user = require_web_user()
            home_point = current_user['home_point']
            if home_point is None:
                return GetMapResponse()

            home = set_srid(Point(home_point.x, home_point.y), 4326)
            nearby_area = home.buffer(meters_to_degrees(NEARBY_USERS_RADIUS_METERS), 4)
            geometry = (
                nearby_area if geometry is None else geometry.intersection(nearby_area)
            )
            if geometry.is_empty:
                return GetMapResponse()

        elif scope == GetMapRequest.Scope.friends:
            current_user = require_web_user()
            followee_ids = await UserFollowQuery.get_followee_ids(current_user['id'])
            if not followee_ids:
                return GetMapResponse()

            if user_ids is None:
                user_ids = followee_ids
            else:
                if len(user_ids) <= len(followee_ids):
                    set_ = set(followee_ids)
                    user_ids = [uid for uid in user_ids if uid in set_]
                else:
                    set_ = set(user_ids)
                    user_ids = [uid for uid in followee_ids if uid in set_]

                if not user_ids:
                    return GetMapResponse()

        if request.HasField('date'):
            try:
                date_ = date.fromisoformat(request.date)
            except ValueError as exc:
                StandardFeedback.raise_error('date', 'Invalid date format', exc=exc)

            dt = datetime.combine(date_, time(0, 0, 0))
            created_before = dt + timedelta(days=1)
            created_after = dt - timedelta(microseconds=1)
        else:
            created_before = None
            created_after = None

        changesets = await ChangesetQuery.find(
            changeset_id_before=(
                ChangesetId(request.before) if request.HasField('before') else None
            ),
            user_ids=user_ids,
            created_before=created_before,
            created_after=created_after,
            geometry=geometry,
            sort='desc',
            limit=CHANGESET_QUERY_WEB_LIMIT,
        )

        async with TaskGroup() as tg:
            tg.create_task(UserQuery.resolve_users(changesets))
            tg.create_task(ChangesetBoundsQuery.resolve_bounds(changesets))
            tg.create_task(ChangesetCommentQuery.resolve_num_comments(changesets))

        return FormatRender.encode_changesets(changesets)

    @override
    async def get(self, request: GetRequest, ctx: RequestContext):
        id = ChangesetId(request.id)
        return GetResponse(changeset=await _build_data(id))

    @override
    async def get_diff(self, request: GetDiffRequest, ctx: RequestContext):
        id = ChangesetId(request.id)
        if await ChangesetQuery.find_by_id(id) is None:
            raise_for.changeset_not_found(id)
        return await _build_diff(id)

    @override
    async def get_comments(self, request: GetCommentsRequest, ctx: RequestContext):
        id = ChangesetId(request.id)
        if await ChangesetQuery.find_by_id(id) is None:
            raise_for.changeset_not_found(id)

        return await _build_comments(id, request.state)

    @override
    async def add_comment(self, request: AddCommentRequest, ctx: RequestContext):
        require_web_user()

        id = ChangesetId(request.id)
        await ChangesetCommentService.comment(id, request.body)

        async with TaskGroup() as tg:
            changeset_t = tg.create_task(_build_data(id))
            comments_t = tg.create_task(_build_comments(id))

        return AddCommentResponse(
            changeset=changeset_t.result(),
            comments=comments_t.result(),
        )


service = _Service()
asgi_app_cls = ServiceASGIApplication


async def _build_data(changeset_id: ChangesetId):
    changeset = await ChangesetQuery.find_by_id(changeset_id)
    if changeset is None:
        raise_for.changeset_not_found(changeset_id)

    async def elements_task():
        return await FormatElementList.changeset_elements(
            await ElementQuery.find_by_changeset(changeset_id, sort_by='typed_id'),
        )

    async def adjacent_task():
        changeset_user_id = changeset['user_id']
        if changeset_user_id is None:
            return None, None
        return await ChangesetQuery.find_adjacent_ids(
            changeset_id, user_id=changeset_user_id
        )

    async with TaskGroup() as tg:
        items = [changeset]
        tg.create_task(UserQuery.resolve_users(items))
        tg.create_task(ChangesetBoundsQuery.resolve_bounds(items))
        elements_t = tg.create_task(elements_task())
        adjacent_t = tg.create_task(adjacent_task())
        is_subscribed_t = tg.create_task(
            UserSubscriptionQuery.is_subscribed('changeset', changeset_id)
        )

    elements = elements_t.result()
    prev_changeset_id, next_changeset_id = adjacent_t.result()

    tags = changeset['tags']
    comment_text = tags.pop('comment', None) or t('browse.no_comment')
    comment_html = process_rich_text_plain(comment_text)

    bboxes: list[list[float]] = (
        measurement.bounds(bounds.geoms).tolist()  # type: ignore
        if (bounds := changeset.get('bounds')) is not None
        else []
    )

    result = Data(
        id=changeset_id,
        created_at=int(changeset['created_at'].timestamp()),
        num_create=changeset['num_create'],
        num_modify=changeset['num_modify'],
        num_delete=changeset['num_delete'],
        comment_rich=comment_html,
        tags=tags,
        is_subscribed=is_subscribed_t.result(),
    )
    if (user := user_proto(changeset.get('user'))) is not None:
        result.user.CopyFrom(user)
    if changeset['closed_at']:
        result.closed_at = int(changeset['closed_at'].timestamp())
    for b in bboxes:
        bound = result.bounds.add()
        bound.min_lon = b[0]
        bound.min_lat = b[1]
        bound.max_lon = b[2]
        bound.max_lat = b[3]
    result.nodes.extend(elements['node'])
    result.ways.extend(elements['way'])
    result.relations.extend(elements['relation'])
    if prev_changeset_id is not None:
        result.prev_changeset_id = prev_changeset_id
    if next_changeset_id is not None:
        result.next_changeset_id = next_changeset_id
    return result


async def _build_diff(changeset_id: ChangesetId):
    """Build deterministic before/after snapshots for a changeset."""
    elements = await ElementQuery.find_by_changeset(changeset_id, sort_by='sequence_id')
    if not elements:
        return GetDiffResponse(before=RenderData(), after=RenderData())

    changed_typed_ids = sorted({element['typed_id'] for element in elements})
    selected_typed_ids = changed_typed_ids[:_CHANGESET_DIFF_ELEMENTS_LIMIT]
    first_sequence_id = SequenceId(elements[0]['sequence_id'] - 1)
    last_sequence_id = elements[-1]['sequence_id']

    async with TaskGroup() as tg:
        before_t = tg.create_task(
            _build_diff_render(selected_typed_ids, first_sequence_id)
        )
        after_t = tg.create_task(
            _build_diff_render(selected_typed_ids, last_sequence_id)
        )

    before, before_context_truncated = before_t.result()
    after, after_context_truncated = after_t.result()
    return GetDiffResponse(
        before=before,
        after=after,
        num_elements=len(selected_typed_ids),
        num_truncated=len(changed_typed_ids) - len(selected_typed_ids),
        context_truncated=before_context_truncated or after_context_truncated,
    )


async def _build_diff_render(
    changed_typed_ids: list[TypedElementId], at_sequence_id: SequenceId
) -> tuple[RenderData, bool]:
    """Render changed roots and their direct geometry context at a snapshot."""
    roots = await ElementQuery.find_by_refs(
        changed_typed_ids,
        at_sequence_id=at_sequence_id,
        sort_dir='asc',
        limit=None,
    )

    member_typed_ids = sorted({
        member
        for root in roots
        if root['visible']
        for member in (root['members'] or ())
    })
    context_truncated = len(member_typed_ids) > _CHANGESET_DIFF_CONTEXT_LIMIT
    member_typed_ids = member_typed_ids[: _CHANGESET_DIFF_CONTEXT_LIMIT + 1]
    members = await ElementQuery.find_by_refs(
        member_typed_ids,
        at_sequence_id=at_sequence_id,
        recurse_ways=True,
        sort_dir='asc',
        limit=_CHANGESET_DIFF_CONTEXT_LIMIT + 1,
    )
    if len(members) > _CHANGESET_DIFF_CONTEXT_LIMIT:
        context_truncated = True
        members = members[:_CHANGESET_DIFF_CONTEXT_LIMIT]

    # Roots win over relation/way context with the same identity.
    element_map: dict[TypedElementId, Element] = {
        element['typed_id']: element for element in roots
    }
    for element in members:
        element_map.setdefault(element['typed_id'], element)

    render = FormatRender.encode_elements(
        list(element_map.values()), detailed=True, areas=False
    )

    # A directly changed node must remain visible even when a changed/context way
    # also references it; detailed rendering normally hides untagged way members.
    rendered_node_ids = {node.id for node in render.nodes}
    for root in roots:
        if element_type(root['typed_id']) != 'node' or root['point'] is None:
            continue
        _, id = split_typed_element_id(root['typed_id'])
        if id in rendered_node_ids:
            continue
        lon, lat = get_coordinates(root['point'])[0].tolist()
        node = render.nodes.add()
        node.id = id
        node.location.lon = lon
        node.location.lat = lat
        rendered_node_ids.add(id)

    return render, context_truncated


async def _build_comments(
    changeset_id: ChangesetId, sp_state: StandardPaginationRequestLike = b''
):
    comments, state = await sp_paginate_table(
        ChangesetComment,
        sp_state,
        table='changeset_comment',
        where=t'changeset_id = {changeset_id}',
        page_size=CHANGESET_COMMENTS_PAGE_SIZE,
        order_dir='desc',
        display_dir='asc',
    )

    async with TaskGroup() as tg:
        tg.create_task(UserQuery.resolve_users(comments))
        tg.create_task(changeset_comments_resolve_rich_text(comments))

    page = GetCommentsResponse()
    page.state.CopyFrom(state)
    for c in comments:
        comment = page.comments.add()
        comment.user.CopyFrom(user_proto(c['user']))  # type: ignore
        comment.created_at = int(c['created_at'].timestamp())
        comment.body_rich = c['body_rich']  # type: ignore
    return page

# Mailbox selection, bulk read state and deletion

Incremental implementation of #165, which explicitly allows incremental work.

Delivered:
- Select individual inbox messages without opening them.
- Select/deselect all messages visible on the current page.
- Display the total selected count, including other pages.
- Keep selection while paging; clear it when switching mailbox or leaving the page.
- Mark selected messages read or unread using existing authenticated RPCs.
- Delete selected inbox messages after confirming the total across all pages.
- Remove completed deletions from the list and selection, closing an affected preview.
- Decrement the unread badge from the atomic server deletion result, including
  for off-page selections; repeated deletion does not decrement it again.
- Update the global unread badge only when the server reports an actual change.
- Stop on failure and retain the failed and unprocessed selections for retry.
- Stop remaining mutations after mailbox navigation; an already-sent RPC may finish.
- Search inbox senders, outbox recipients and subjects with case-insensitive literal
  substrings. Percent and underscore characters are not treated as wildcards.
- Filter by inclusive timestamps entered in local time. Filters apply on the server
  across the mailbox, preserve ownership restrictions, and are retained in the URL.
- Applying different filters resets pagination, preview and selection. Paging and
  opening or closing a preview retain the active filters.

Requests run sequentially. A second bulk operation and selection changes are disabled
while processing. The existing message service continues to enforce ownership.

Not included in this increment: age-based deletion presets. The issue's $30 label covers the overall issue; this contribution
does not claim full completion or any particular payment allocation.

Validation: production selection runner exercised for sequential completion,
partial failure and navigation invalidation. Changed TS/TSX files transpile with
esbuild and pass oxfmt. Full authenticated application integration requires the
project Nix environment and has not been run locally.

The RPC CRUD regression also checks the unread deletion flag and idempotent retry;
it requires the project database and generated protobuf bindings to run in CI.
The production mailbox component was also exercised with mocked RPC/pagination:
cancel confirmation, delete off-page selections, stop on partial failure, retry
only remaining selections, and update the unread badge. Local Cython conversion
of the modified message service passed.

Filter validation: compiled protobuf descriptors accept valid boundaries and reject
reversed dates, out-of-range timestamps, empty searches and oversized searches.
The component harness checks filter reset and selection clearing. Added database RPC
regressions for sender/recipient matching, literal characters, date ranges, mailbox
ownership and hidden messages; these require upstream CI. Ruff, buf lint/build,
TSX transpilation and local Cython conversion of the query/RPC modules passed.

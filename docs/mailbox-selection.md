# Mailbox selection and bulk read state

Incremental implementation of #165, which explicitly allows incremental work.

Delivered:
- Select individual inbox messages without opening them.
- Select/deselect all messages visible on the current page.
- Display the total selected count, including other pages.
- Keep selection while paging; clear it when switching mailbox or leaving the page.
- Mark selected messages read or unread using existing authenticated RPCs.
- Update the global unread badge only when the server reports an actual change.
- Stop on failure and retain the failed and unprocessed selections for retry.
- Stop remaining mutations after mailbox navigation; an already-sent RPC may finish.

Requests run sequentially. A second bulk operation and selection changes are disabled
while processing. The existing message service continues to enforce ownership.

Not included in this increment: search, date-range filters, bulk deletion and
age-based deletion. The issue's $30 label covers the overall issue; this contribution
does not claim full completion or any particular payment allocation.

Validation: production selection runner exercised for sequential completion,
partial failure and navigation invalidation. Changed TS/TSX files transpile with
esbuild and pass oxfmt. Full authenticated application integration requires the
project Nix environment and has not been run locally.

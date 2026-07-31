
### Migration

Run migrations `ffun migrate`.

- If `FFUN_DISPATCHER_DISPATCH_CHUNK` is configured, replace it with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE`; configure `FFUN_DISPATCHER_DISPATCH_CONCURRENCY` as needed or use its default.

### Changes

- ff-639 — Implemented `ffun.locks` module as a universal distributed lock manager for backend modules.
- ff-639 — Implemented `ffun.audit` module to record and query important operations in the backend.
- ff-639 — Implemented `ffun.entitlements` module to manage user entitlements.
  - Two entitlement types are introduced: `day_tokens`, `month_tokens`, `lifetime_tokens`.
  - Implemented CLI `ffun entitlements` to manage user entitlements.
  - `FFUN_DISPATCHER_DISPATCH_CHUNK` setting is replaced with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE` and `FFUN_DISPATCHER_DISPATCH_CONCURRENCY`.
- ff-639 — tokens now could be spend to tag a single news entry:
  - tagging one news entry will take a one token;
  - tokens are spent per user; i.e. if multiple users want to see tags to the same entry, each of them will spend 1 token.
  - tokens are spent in order: `day_tokens` first, `month_tokens` if there are no `day_tokens`, and `lifetime_tokens` if there are no `month_tokens`.

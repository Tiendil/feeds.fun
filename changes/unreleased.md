
### Migration

Run migrations `ffun migrate`.

- If `FFUN_DISPATCHER_DISPATCH_CHUNK` is configured, replace it with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE`; configure `FFUN_DISPATCHER_DISPATCH_CONCURRENCY` as needed or use its default.

### Changes

- ff-639 — Implemented `ffun.locks` module as a universal distributed lock manager for backend modules.
- ff-639 — Implemented `ffun.audit` module to record and query important operations in the backend.
- ff-639 — Implemented `ffun.entitlements` module to manage user entitlements.
  - Two entitlement types are introduced: `day_tokens` and `month_tokens`.
  - Implemented CLI `ffun entitlements` to manage user entitlements.
  - `FFUN_DISPATCHER_DISPATCH_CHUNK` setting is replaced with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE` and `FFUN_DISPATCHER_DISPATCH_CONCURRENCY`.

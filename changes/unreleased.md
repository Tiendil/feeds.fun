
### Migration

Run migrations `ffun migrate`.

- If `FFUN_DISPATCHER_DISPATCH_CHUNK` is configured, replace it with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE`; configure `FFUN_DISPATCHER_DISPATCH_CONCURRENCY` as needed or use its default.
- Set `FFUN_DISPATCHER_ENFORCE_ENTITLEMENTS=False` unless you want to manage entitlements (like token limits) for your users. The `False` value preserves the old behavior of the system, where all users can see all tagged news by default.

### Changes

- ff-639 — Implemented `ffun.locks` module as a universal distributed lock manager for backend modules.
- ff-639 — Implemented `ffun.audit` module to record and query important operations in the backend.
- ff-639 — Implemented `ffun.entitlements` module to manage user entitlements.
  - Three entitlement types are introduced: `day_tokens`, `month_tokens`, `lifetime_tokens`.
  - Implemented CLI `ffun entitlements` to manage user entitlements.
  - `FFUN_DISPATCHER_DISPATCH_CHUNK` setting is replaced with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE` and `FFUN_DISPATCHER_DISPATCH_CONCURRENCY`.
- ff-639 — Implemented `ffun.subscriptions`, `ffun.one_time_purchases`, and `ffun.benefits` modules to manage token one-time grants and subscriptions.
  - Implemented CLI `ffun benefits` to grant and revoke benefit packages to users.
  - Implemented CLI `ffun subscriptions` to list subscriptions.
  - Implemented CLI `ffun one-time-purchases` to list one-time purchases.
- ff-639 — tokens now could be spend to tag a single news entry:
  - tagging one news entry will take a one token;
  - tokens are spent per user; i.e. if multiple users want to see tags to the same entry, each of them will spend 1 token.
  - tokens are spent in order: `day_tokens` first, `month_tokens` if there are no `day_tokens`, and `lifetime_tokens` if there are no `month_tokens`.
- ff-639 — Display token and subscription information in the frontend.
- ff-639 — Improved styles of info panels and buttons in the frontend.

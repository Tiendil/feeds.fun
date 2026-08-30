
### Migration

- Run migrations `ffun migrate`.
- **Set `FFUN_DISPATCHER_ENFORCE_ENTITLEMENTS="False"`** for backend services unless you want to manage entitlements (like token limits) for your users. The `False` value preserves the old behavior of the system, where all users can see all tagged news by default.
- If `FFUN_DISPATCHER_DISPATCH_CHUNK` is configured, replace it with `FFUN_DISPATCHER_DISPATCH_BATCH_SIZE`; configure `FFUN_DISPATCHER_DISPATCH_CONCURRENCY` as needed or use its default.

### Changes

- ff-639 — Implemented "news tokens" as a replacement for user API keys. Right now both mechanisms are supported, but user API keys are considered legacy and will be removed in the future. To back up new tokens, entitlements are implemented as well as subscriptions and one-time purchases. However, no payment processing is implemented yet, so all operations on entitlements are CLI-only.
  - News tokens can be spent to tag a single news entry:
    - tagging one news entry takes one token;
    - tokens are spent per user; i.e., if multiple users want to see tags for the same entry, each of them will spend 1 token.
    - tokens are spent in order: `day_tokens` first, `month_tokens` if there are no `day_tokens`, and `lifetime_tokens` if there are no `month_tokens`.
  - Implemented `ffun.locks` module as a universal distributed lock manager for backend modules.
  - Implemented `ffun.audit` module to record and query important operations in the backend.
  - Implemented `ffun.entitlements` module to manage user entitlements.
  - Implemented `ffun.subscriptions`, `ffun.one_time_purchases`, and `ffun.benefits` modules to manage token one-time grants and subscriptions.
  - Three entitlement types are introduced: `day_tokens`, `month_tokens`, `lifetime_tokens`.
  - Implemented CLI `ffun benefits` to grant and revoke benefit packages to users.
  - Implemented CLI `ffun entitlements` to list user entitlements.
  - Implemented CLI `ffun subscriptions` to list subscriptions.
  - Implemented CLI `ffun one-time-purchases` to list one-time purchases.
  - Frontend updated to display information about tokens and subscriptions.
  - Improved styles of info panels and buttons.

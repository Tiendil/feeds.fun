# Entitlement token tracking for backend tag processing

## Goal of the document

This document describes how recurring and lifetime SaaS tokens should authorize backend LLM tag processing, how one token per entitlement-funded user and successful entry-processing attempt should be reserved and consumed, and how this access path should coexist with the current user API-key and LLM-usage tracking path.

## Scope

This design covers LLM-backed entry tag processing for user-linked feeds, three new resource kinds, per-user authorization, token-pool precedence, concurrency, accounting, route configuration, failures, observability, and required tests.

The design does not define product prices, payment-provider protocols, the UI for buying lifetime tokens, or a complete billing ledger. It does identify the lifetime-token contract that those systems must provide.

## Dictionary

- `SaaS token` — an internal Feeds Fun access unit. In the first implementation, one SaaS token authorizes one user to participate in one successful entry-processing attempt and see its produced tags.
- `LLM token` — a provider-reported input or output token used for API-key cost and usage tracking. It has no conversion to or effect on SaaS tokens.
- `recurring quota` — a SaaS-token allowance supplied by an active entitlement whose usage resets at a calendar boundary.
- `lifetime token` — a spendable SaaS token that does not reset at a day or month boundary and remains available until consumed or explicitly adjusted.
- `token pool` — one ordered source of SaaS capacity: daily quota, monthly overflow quota, or lifetime tokens.
- `API-key sponsor` — the one linked user whose API key is selected by the existing key-rotation logic to execute a shared entry-processing call.
- `entitlement-funded user` — a linked user whose own recurring quota or lifetime tokens are charged for access to the tags produced by a shared entry-processing call.
- `authorized user` — a linked user who may see the produced tags because the user is covered by the API-key path or has a successful token reservation and settlement.
- `reservation` — the configured per-user-attempt SaaS-token amount held in an aggregate resource row before processing so concurrent workers cannot overspend the pool. Its pool, interval, and amount are kept in the in-memory processing context.
- `settlement` — conversion of the in-memory reservation's amount into aggregate usage, or its release without usage.
- `configured API key` — an API key owned by the Feeds Fun operator and configured on a processor route.
- `user API key` — an API key stored in a user's settings and selected by the existing key-rotation logic.

## Current behavior and constraints

The current implementation has several properties that the integration must preserve or change deliberately:

1. Tag generation is entry-scoped, not user-scoped. An entry is processed once by a processor, and the resulting tags are attached to the shared entry. The existing user-key logic chooses one linked user as the API-key sponsor. This one-sponsor behavior is specific to API-key execution and must not be reused for entitlement accounting.
2. The dispatcher chooses one processor route based on whether an entry belongs to a collection or to user-linked feeds. The route then controls how the LLM processor obtains an API key.
3. A route with a configured API key currently uses that key immediately. A route without one searches linked users for a working user API key, applies the existing age and legacy monthly-cost checks, reserves the legacy `tokens_cost` resource, and selects one user.
4. Collection processing uses a configured key and intentionally cannot use a user key. An entry linked to a collection is treated as collection work even if it also has user links. This prevents a user from paying for collection processing.
5. `ffun.entitlements` already exposes a batch query for active `day_tokens`, `month_tokens`, and `lifetime_tokens` entitlements. Their values are limits; entitlement state does not track consumption.
6. `ffun.resources` stores aggregate `used` and `reserved` counters by `(kind, user, interval_started_at)`. Its current primitive is atomic for one resource row. The SaaS-token path should reuse this aggregate, in-memory-reservation model rather than add per-entry accounting records.
7. Provider responses expose LLM input and output token counts, and the existing API-key path derives cost usage from them. These provider units are separate from the SaaS-token resources introduced here.

Entitlement access is user-scoped. Every linked user who is not covered by the API-key path must reserve one of that user's SaaS tokens before processing and consume it after the processing attempt succeeds. The provider call is still performed once: if three entitlement-funded users are authorized, each consumes one SaaS token regardless of how many LLM tokens the call uses.

This first implementation intentionally provides the same durability level as the existing API-key resource accounting. Reservation metadata exists only in the running worker. Linked users are deduplicated within one processing attempt, but retries, multiple processors, or process crashes do not have a durable per-user-entry idempotency identity. A later successful attempt may therefore charge again, and a process crash may leave aggregate capacity reserved.

An entry may therefore have three sets of linked users after authorization:

- API-key-covered users, who may see the tags without spending the new token resources;
- entitlement-funded users, who may see the tags after their individual reservations are settled;
- unauthorized users, who must not see the tags because they had neither API-key coverage nor sufficient token capacity.

## Recommended accounting model

### Separate allowances from consumption

All three pools should use the same accounting convention:

```text
available = max(allowance - used - reserved, 0)
```

`used` and `reserved` are non-negative cumulative counters within a pool's interval. They must never mean “remaining balance.” The allowance comes from a separate source:

- daily allowance: the active `day_tokens` entitlement value;
- monthly overflow allowance: the active `month_tokens` entitlement value;
- lifetime allowance: the effective `lifetime_tokens` entitlement value, summed across active sources.

This convention fits the current resources table, provides consistent reservation and settlement operations, keeps historical usage visible, and handles an entitlement increase or decrease without rewriting consumption. If a limit decreases below already-used capacity, the remaining capacity becomes zero; recorded usage must not be erased or clamped.

The monthly pool is an overflow pool, not a cap on all activity during the month. For example, with a daily limit of 100 and a monthly limit of 1,000, accessing 130 new entries in one day records 100 against the daily pool and 30 against the monthly pool. The next day has a fresh daily 100, while the monthly pool still has 970.

### Resource kinds

Three stable resource kinds should be added. Names should describe what the resource row stores, rather than repeat the allowance name:

| Proposed resource kind | Stable value | Allowance source | Resource interval |
| --- | ---: | --- | --- |
| `day_token_usage` | 3 | active `day_tokens` entitlement | start of the current calendar day |
| `month_token_usage` | 4 | active `month_tokens` entitlement | start of the current calendar month |
| `lifetime_token_usage` | 5 | active `lifetime_tokens` entitlement | one non-rotating lifetime interval |

Value `1` should not be reused because it belonged to historical OpenAI-token tracking; the existing `tokens_cost = 2` must retain its stable value. Adding the enum values requires no database migration because `r_resources.kind` is an integer without a database registry. This implementation adds no per-user-entry reservation table.

All users and operations use UTC calendar boundaries. A daily interval starts at 00:00 UTC each day, and a monthly interval starts at 00:00 UTC on the first day of each month. One timestamp must be captured at authorization time and used to derive both interval starts. A call crossing midnight or a month boundary settles against the rows reserved at authorization time; it must not move usage into a newer interval during settlement.

## Proposed lifetime-token solution

### Model lifetime tokens as an entitlement

Add `lifetime_tokens` as an effectively infinite entitlement. “Infinite” is represented by one stable future expiration constant, such as `LIFETIME_ENTITLEMENT_EXPIRES_AT`, set approximately 100 years in the future. Every lifetime-token entitlement uses that fixed value; grant operations must not recompute `now + 100 years` and silently move the boundary.

The entitlement value is a cumulative maximum allowed usage, not a remaining balance. `lifetime_tokens` uses the `sum` merge policy so active sources contribute additively. Consumption never modifies entitlement state: `lifetime_token_usage` tracks `used` and `reserved` in one stable lifetime resource interval, exactly as day and month consumption are tracked in their respective resource intervals.

The resulting calculation is:

```text
lifetime available = max(effective lifetime_tokens - used - reserved, 0)
```

Reducing or revoking entitlement allowance does not rewrite historical usage and is allowed to reduce the effective maximum below `used + reserved`; availability then remains zero. A later grant provides capacity only after the summed entitlement maximum exceeds lifetime `used + reserved`. For example, after 80 tokens have been used, revoking the allowance and later granting 50 tokens still leaves zero available. This is the intended behavior.

Pros:

- gives all three token types the same allowance-in-entitlements and consumption-in-resources architecture;
- reuses the current batch entitlement lookup and lets sources contribute through a `sum` policy;
- unifies system, admin, support, and future purchase grants and revocations behind the entitlements domain;
- keeps high-frequency consumption out of entitlement state and audit events;
- makes aggregate allowance, usage, reservation, and availability reporting consistent across all three pools.

Cons:

- additive grants require callers to supply a distinct stable source transaction id, while retries of the same grant must reuse that id;
- consumption is pooled and cannot identify which individual grant or purchase funded a particular user-entry;
- a future purchase system still needs its own immutable financial transaction history and external idempotency ids, even though its effective allowance is represented by entitlements;
- the effectively infinite expiration remains an operational convention and must be centralized and monitored.

This is the proposed model for the first implementation. Granting and revoking lifetime capacity must use the public entitlements domain, while consumption, reservation, and release must use the resources domain.

## Funding and processing workflow

### Funding precedence

For a user-feed route, funding and access must be evaluated in this order:

1. Evaluate linked users with the existing API-key eligibility rules. Mark every passing user as API-key-covered, select at most one as sponsor using the existing rotation logic, and reserve only that sponsor's legacy `tokens_cost` resource.
2. For every remaining linked user, independently attempt to reserve `SAAS_TOKENS_PER_USER_ENTRY` from that user's daily, monthly, then lifetime pool.
3. If an API-key sponsor exists, use that user's key for the shared provider call. Otherwise, if at least one user has a successful token reservation, use the configured Feeds Fun API key.
4. If neither authorization path has a user, skip the entry with a funding-specific reason.
5. After successful entry processing, settle every entitlement-funded user's captured in-memory reservation amount as used and grant visibility only to successfully authorized users.

API-key precedence is applied per user for entitlement charging and once per call for credential selection. A user covered by the API-key path must not spend daily, monthly, or lifetime resources for that entry. Other linked users without API-key coverage must still be charged individually even when the shared provider call uses the sponsor's personal key.

A provider failure after a user key has been selected must not automatically fall back to a configured key in the same attempt, because doing so could issue duplicate LLM requests. It follows the common settlement policy for every entitlement-funded user whose reservation accompanied that attempt.

The existing filters on user keys—working-key status, entry-age preference, and legacy monthly cost protection—remain part of the old path. A user whose personal key is broken, over its provider quota, or over the legacy cost guard did not obtain usable API-key coverage and must be allowed to fall back to daily, monthly, or lifetime SaaS tokens.

Collection routes must keep their current guarantee: use a configured key without selecting or charging a user. Entitlement and lifetime-token funding applies only to user-feed routes.

### Route configuration

Entitlement enforcement should be configured independently on each processor route and disabled by default for
backward compatibility:

```toml
[[tag_processors.routes]]
id = "user-api-key"
allowed_for_users = true
api_key = ""
enforce_entitlements = false
```

When a user-feed route has `enforce_entitlements = false`:

- a user-feed route with a non-empty `route.api_key` retains the current configured-key-only behavior: the configured key processes the entry, all linked users may see its tags, and no SaaS-token entitlement, restriction, reservation, or usage tracking runs;
- a user-feed route with an empty `route.api_key` retains the current user-key-only behavior;
- collection routes retain their current configured-key behavior and global visibility.

This default preserves existing self-hosted deployments, where `route.api_key` commonly supplies the deployment's shared key and all users are expected to see processed tags.

When a user-feed route has `enforce_entitlements = true`, that route must define a non-empty `api_key`; startup
validation must reject the route configuration otherwise. The route follows the entitlement-aware workflow:

1. Evaluate eligible personal user API keys first and identify all API-key-covered users.
2. Select at most one covered user as the API-key sponsor with the existing rotation logic.
3. Independently reserve `SAAS_TOKENS_PER_USER_ENTRY` for every remaining eligible user.
4. Use the sponsor's personal key for the shared provider call when a sponsor exists.
5. Otherwise, use `route.api_key` as the fallback provider credential only when at least one entitlement-funded user has a successful reservation.
6. Grant visibility only to API-key-covered users and successfully settled entitlement-funded users.

In enabled mode, `route.api_key` supplies credentials only. Its presence does not authorize users, bypass entitlement checks, make tags globally visible, or consume a SaaS token on anyone's behalf. Collection processing remains outside entitlement enforcement and keeps its existing configured-key semantics.

Production must explicitly set `enforce_entitlements = true` on every user-feed route that should enforce access.
Because the backward-compatible route default is fail-open, startup should emit a prominent structured warning for
each user-feed route where it is disabled. Production deployment validation or health checks should assert that it is
enabled on every production user-feed route.

The LLM call context should represent the credential independently from per-user access authorizations. It should contain an explicit credential source and a collection of per-user authorizations; a collection call has no user authorizations.

### Per-user eligibility and reservation discovery

The entitlement path should perform these steps with one captured authorization time:

1. Resolve the unique users linked to all non-collection feeds for the entry.
2. Evaluate API-key coverage first and remove covered users from entitlement charging.
3. Apply user-level eligibility to every remaining user, especially the “process entries not older than” preference, unless product requirements deliberately remove it for entitlement-funded access.
4. Batch-load active `day_tokens`, `month_tokens`, and `lifetime_tokens` entitlements for all remaining user ids through `ffun.entitlements.domain`.
5. Batch-load existing daily, monthly, and lifetime usage without creating rows for every user. Missing usage rows mean zero.
6. For every user with at least `SAAS_TOKENS_PER_USER_ENTRY` available in one pool, atomically reserve that amount from the first available pool in priority order.
7. Treat each reservation result independently: a race or lack of capacity excludes only that user and must not prevent reservations for other users.

There is no entitlement-candidate ranking or one-user winner. Every eligible non-key user must be considered and every successful reservation becomes a separate per-user-attempt charge and visibility authorization. A user linked through multiple feeds is deduplicated and charged at most once within that processing attempt.

Discovery must not make one entitlement or resource read per user. The existing entitlement query is already batch-shaped. The resource boundary should gain a batch read that treats missing rows as zero without per-user initialization. The write boundary may reserve users one at a time or in bulk, but each user's ordered pool result is independently atomic and a bulk result must report success or failure per user.

A cross-module SQL join is not recommended because it would violate module ownership. Use batch domain calls followed by atomic aggregate resource reservations.

### Pool selection and switching

Every entitlement-funded reservation is exactly one indivisible SaaS token in the first implementation and belongs to exactly one pool. The reservation amount must come from a single backend constant:

```text
SAAS_TOKENS_PER_USER_ENTRY = 1
```

Eligibility checks, reservation, settlement, audit, and metrics must use this constant rather than hard-code `1`. The constant is not route or deployment configuration. The in-memory reservation context must capture the amount when it is created so a configuration-independent code change cannot alter settlement while that worker attempt is running. Reservations do not survive process restarts.

Select the first pool with at least `SAAS_TOKENS_PER_USER_ENTRY` available units in strict order:

1. daily quota;
2. monthly overflow quota;
3. lifetime tokens.

The selection rule is:

```text
required = SAAS_TOKENS_PER_USER_ENTRY

if daily available >= required: reserve required daily tokens
else if monthly available >= required: reserve required monthly tokens
else if lifetime available >= required: reserve required lifetime tokens
else: user is not authorized
```

No reservation is split, so failure in a later pool cannot leak a hold in an earlier pool: a failed conditional reservation must not mutate the earlier row. The resource domain should expose one operation that encapsulates the ordered selection so callers cannot change precedence accidentally. Its final availability check must include `used + reserved + required <= allowance`. A failure for one user must not roll back successful reservations for other users.

A user may spend `month_tokens` when `day_tokens` is absent, zero, or exhausted. In all three cases, daily availability is zero and ordered selection proceeds to the monthly pool.

### SaaS-token unit and LLM-usage separation

The SaaS reservation amount uses the business constant defined above:

```text
SaaS tokens reserved per entitlement-funded user-entry = SAAS_TOKENS_PER_USER_ENTRY
```

This constant is the single source of truth for new reservations. Changing token cost in a future release should require changing this value rather than modifying the authorization workflow.

Input-token estimates, output limits, provider-reported input/output tokens, model prices, request count, text length, and provider cost must not change this amount. There is no conversion rate between SaaS tokens and LLM tokens.

The existing API-key path must continue to collect provider-reported input and output LLM tokens, derive the API-key user's actual cost from them, and settle the legacy `tokens_cost` resource as it does today. If an API-key sponsor executes a call for entitlement-funded users, these two accounting paths run independently: the sponsor receives the existing LLM cost/usage update, while every entitlement-funded user consumes exactly one SaaS token. Configured-key provider usage may be recorded operationally, but it must not change any user's SaaS-token consumption.

### Settlement and failures

The existing resource operations provide the reservation and counter-conversion mechanics. SaaS-token processing adds the following business contract:

- settle each entitlement-funded user's in-memory reservation only after the tag result, including a valid empty result, and the processor's `processed` status are durably persisted;
- release reservations without increasing usage when the provider call, normalization, or persistence fails before that boundary;
- settle users independently and grant an entitlement-funded user visibility only after that user's settlement succeeds;
- use the amount, pool, and interval captured in the in-memory reservation context for settlement or release;
- follow the current API-key accounting durability model: a process crash can leave aggregate capacity reserved, and a retry or another processor can create a new reservation and charge;
- do not add a durable per-user-entry reservation identity or automatic stale-reservation cleanup in this implementation;
- keep legacy API-key LLM usage and cost accounting independent, including when a later processing failure releases SaaS reservations.

## Per-user authorization and visibility

Entitlement accounting is an access-control boundary. Producing tags on the shared entry must not make those tags visible to every linked user automatically.

For a successful shared call:

- every API-key-covered user receives access without spending the new token resources;
- every entitlement-funded user receives access only after that user's reservation is successfully settled;
- every other linked user remains unable to see the generated tags.

The current dispatcher marks user-feed tags globally visible before processing. That behavior must change before entitlement charging is enabled. User-feed visibility should use the existing user-scoped `can_see_tags` marker. Collection visibility may remain global.

Visibility remains idempotent for `(user, entry)` through the marker's existing uniqueness constraint and must not be granted merely because capacity was provisionally observed. The processing-attempt ordering is:

1. reserve all individually eligible users;
2. execute the one provider call when at least one user is authorized by either path;
3. persist the shared tags;
4. settle each entitlement-funded reservation;
5. grant or confirm visibility for API-key-covered users and successfully settled entitlement-funded users.

Tag persistence, settlement, and visibility cross module boundaries and are not one transaction. The implementation makes a best effort to complete them in that order but does not guarantee convergence after process termination. The visibility marker prevents duplicate visibility rows, but it is not a billing idempotency record; a retry or another processor may charge the user again.

No fairness or ranking policy is needed for entitlement users because the system does not choose one of them: it charges all independently eligible users. Ranking remains only inside the legacy API-key sponsor selection.

## Domain boundaries and required changes

### Entitlements

- Keep `day_tokens` and `month_tokens` as limit entitlements with their current `max` merge policy.
- Add `lifetime_tokens` as a limit entitlement with the `sum` merge policy and the shared `LIFETIME_ENTITLEMENT_EXPIRES_AT` future expiration constant.
- Use the public batch effective-entitlement query; processing code must not read entitlement tables or merge source entitlements itself.
- Grant and revoke lifetime capacity through the public entitlements domain and its audit path.
- Do not write any entitlement state during usage; token consumption belongs exclusively to resources.
- When purchases are introduced, keep immutable financial transactions with external idempotency ids and project their effects into `lifetime_tokens` entitlements.

### Resources

- Add the three stable resource kinds.
- Add batch read support for multiple users and token resource kinds without initializing missing rows.
- Add one public atomic operation that reserves `SAAS_TOKENS_PER_USER_ENTRY` from the first available pool for one user, plus an efficient way to invoke it for every eligible user and receive per-user results.
- Reuse the current aggregate counter-conversion operation for settlement and release; releasing converts the captured reserved amount with zero added usage.
- Capture one authorization timestamp and return the exact interval identifiers and amount in an in-memory reservation object so settlement in the same worker attempt cannot recompute them differently.
- Use one canonical lifetime interval identifier for every `lifetime_token_usage` row; it must not be derived from an individual entitlement's start or expiration.
- Do not add a database migration, per-user-entry reservation table, reservation cleanup index, or stale-reservation recovery workflow.

### LLM framework and tag processor

- Generalize LLM usage authorization so the API credential and funding source are distinct.
- Preserve user API-key selection as the first strategy on user-funded routes.
- Add independent one-SaaS-token reservation and settlement for every linked user not covered by the API-key path.
- Ensure no new token resources are spent for API-key-covered users or uncharged collection routes.
- Keep LLM token/cost estimation and settlement in the existing API-key usage path; do not pass those quantities into SaaS resource operations.
- Use the API-key sponsor's key when available; otherwise use the configured key when at least one entitlement-funded user is reserved.
- Keep user id, entry id, and processor id as diagnostic context in reservations, logs, and events. They do not form a durable charging identity, and a later processor attempt may create another charge.
- Use a funding-specific skip reason only when no user is authorized by either path. Partial user authorization still permits the shared entry call for the authorized subset.

### Processor routes and configuration

- Add `enforce_entitlements` to processor-route configuration with a backward-compatible default of `false`.
- Preserve existing configured-key-only and user-key-only behavior when entitlement enforcement is disabled.
- When enforcement is enabled, always evaluate personal user keys first and reinterpret `route.api_key` on user-feed routes as the fallback credential for entitlement-funded execution.
- Reject a route configuration when `allowed_for_users = true`, `enforce_entitlements = true`, and `api_key` is empty.
- Keep collection-route credential and visibility behavior independent of entitlement enforcement.
- Emit a structured warning for each user-feed route where entitlement enforcement is disabled so production can
  detect fail-open route configuration.
- Update fixture configurations, example configurations, and the configuration/change note for operators.

### Retroactive authorization and reprocessing

Automatically authorizing previously hidden tags, redispatching globally skipped entries, or backfilling access after a token purchase or grant is outside the initial implementation and this specification. It should be designed separately if required later.

## Concurrency, correctness, and durability

- Entitlement and lifetime-token allowances must be evaluated together with current usage at one logical authorization time.
- The database, not the Python prefilter, is authoritative for the final availability check.
- Each user's ordered reservation of `SAAS_TOKENS_PER_USER_ENTRY` and any resource-row initialization must be atomic. Different users' outcomes are independent.
- Pool attempts must preserve daily, monthly, lifetime order and, when multiple users share a transaction, deterministic user-id order.
- Each in-memory reservation must be settled or released once by its owning worker attempt. Duplicate settlement or release is a caller error and is not required to be idempotent.
- A reservation may be settled after its entitlement expires because authorization occurred while the entitlement was active; it uses the aggregate row and interval captured in memory at reservation time.
- Unlinking a user or feed after reservation does not invalidate work already authorized.
- A user linked through more than one feed must be deduplicated within one processing attempt and receive at most one reservation from that attempt.
- Separate processor attempts and retries do not share reservation identity. Each successful attempt may consume another SaaS token, and a process crash may leave its aggregate reservation unreleased.
- Lifetime-token grant operations must be concurrency-safe; future payment notifications require external idempotency keys.
- A lifetime allowance reduction may leave `used + reserved` above the effective entitlement. Availability is clamped to zero, and existing resource counters are not changed.
- Usage counters must not be reset when entitlements change.

## Audit, events, metrics, and privacy

The accounting path should emit a structured business event after settlement, with at least:

- charged user id and optional API-key sponsor id;
- entry id and diagnostic processor id;
- selected SaaS pool (`day_tokens`, `month_tokens`, or `lifetime_tokens`);
- reserved SaaS tokens (the in-memory reservation amount, initially `1`);
- used SaaS tokens (the captured amount for successful processing, otherwise `0`);
- settlement outcome and failure category.

The event should be emitted once per entitlement-funded user so per-user access and accounting can be reconstructed. The shared call may additionally emit one aggregate event with the number of API-key-covered, entitlement-funded, and unauthorized users.

Lifetime-token entitlement grants and adjustments should produce durable entitlement audit records containing actor, subject user, signed amount, and reason/source. When purchases are introduced, their separate immutable financial records must additionally contain the external transaction id. Routine resource reservations need not become entitlement audit events.

Metrics must keep SaaS-token consumption separate from LLM usage. They should count per-user authorization outcomes, selected SaaS pools, captured reservation amounts, reservation races, and failed settlement or release calls. There is no reliable stale-reservation metric because reservation identity is not persisted. Existing API-key metrics/events should continue to report provider/model usage and cost. API-key values must never appear in logs, events, in-memory reservation diagnostics, or error messages beyond the existing protected configuration/settings storage.

## Acceptance and test scenarios

At minimum, automated backend tests should cover:

1. With entitlement enforcement enabled, a usable API-key sponsor is selected with the existing logic, spends none of the three SaaS resources, and still has legacy LLM usage/cost tracked.
2. A shared call with one API-key-covered user and two entitlement-funded users executes once and charges exactly one SaaS token to each entitlement-funded user.
3. Varying input tokens, output tokens, model cost, request count, or actual provider usage never changes the one-unit SaaS charge.
4. With entitlement enforcement enabled, users whose personal keys are absent, broken, over provider quota, or over the legacy cost guard may fall back to SaaS tokens; when at least one has daily capacity, `route.api_key` executes the call and every such user is charged independently.
5. A user with daily capacity consumes the daily pool and no other pool.
6. A user with absent, zero, or exhausted daily capacity consumes one monthly token and no lifetime token.
7. A user with exhausted daily and monthly capacity consumes one lifetime token.
8. A user with no available pool is excluded from visibility without preventing other authorized users from processing.
9. When no linked user is covered by an API key or has a SaaS token, the entry is skipped and no reservation leaks.
10. Provider, normalization, or tag-persistence failure releases every SaaS reservation without increasing SaaS usage.
11. An API-key sponsor's actual LLM usage remains tracked when a post-provider failure causes SaaS reservations to be released.
12. A successfully processed entry with an empty tag set still consumes exactly one SaaS token per entitlement-funded user.
13. A collection entry remains globally visible as specified and never charges user SaaS resources.
14. Users linked through multiple feeds are batch-loaded and charged at most once each within one processing attempt.
15. Separate successful processor attempts or retries may charge a user again for the same entry; the implementation does not provide cross-attempt billing idempotency.
16. Concurrent workers cannot exceed any pool allowance, although separate workers processing the same user and entry may each obtain a reservation while capacity remains.
17. A pool race affects only that user; other user authorizations continue.
18. Daily intervals start at 00:00 UTC, monthly intervals start at 00:00 UTC on the first day of the month, and a call crossing either boundary settles the interval captured at authorization.
19. Entitlement increase, decrease, expiration, and revocation do not rewrite existing usage.
20. Visibility grants and lifetime-token grant ids remain idempotent; each in-memory SaaS reservation is settled or released exactly once by its owning worker attempt.
21. An abrupt worker termination may leave aggregate capacity reserved, matching the existing API-key accounting durability model; automatic stale-reservation recovery is outside this implementation.
22. Tags are visible to API-key-covered and successfully settled entitlement-funded users, but not to unauthorized or unsettled users.
23. Tags are not made globally visible for user-feed processing before per-user authorization.
24. With entitlement enforcement disabled and `route.api_key` present, configured-key processing remains unrestricted, all linked users may see tags, and no SaaS-token accounting runs.
25. With entitlement enforcement disabled and `route.api_key` absent, the existing user-key-only behavior is preserved.
26. Provider-reported input and output tokens from every request executed with a user API-key sponsor continue to feed that sponsor's existing LLM usage tracking only.
27. Active `lifetime_tokens` sources are combined with the `sum` policy, while consumption is recorded only in `lifetime_token_usage`.
28. Every lifetime-token entitlement uses the shared stable future expiration constant, and updating a grant does not move that expiration.
29. Reducing lifetime allowance below lifetime usage leaves usage unchanged and availability at zero; a later grant smaller than that historical usage does not restore capacity.
30. With entitlement enforcement enabled and both a personal-key sponsor and `route.api_key` available, the sponsor's key executes the call and `route.api_key` is not used.
31. With entitlement enforcement enabled and no personal-key sponsor, `route.api_key` executes the call only when at least one user has a successful SaaS-token reservation.
32. A route with `allowed_for_users = true`, `enforce_entitlements = true`, and an empty `api_key` fails validation at
    startup.
33. Collection routes keep their configured-key and global-visibility behavior whether entitlement enforcement is enabled or disabled.
34. Availability checks, reservation, settlement, audit, and metrics all derive the new-reservation amount from `SAAS_TOKENS_PER_USER_ENTRY`, whose initial value is `1`.
35. Settlement and release use the amount captured in the in-memory reservation object rather than rereading `SAAS_TOKENS_PER_USER_ENTRY` during the same worker attempt.

All development checks and tests must run through the project's Docker-backed scripts. Changes confined to this `.session` design document do not require runtime checks.

## Rollout considerations

- Additive resource kinds require no usage backfill; missing rows start at zero.
- Entitlement enforcement remains disabled by default on each route and should be enabled on production user-feed
  routes only after route fallback credentials, the `lifetime_tokens` entitlement, visibility enforcement, and
  observability are deployed.
- Keep the legacy `tokens_cost` resource and user-key guard unchanged during coexistence.
- Deploy `lifetime_tokens` entitlement support and its stable future expiration constant, and configure a non-empty
  `api_key` on each user-feed route before setting that route's `enforce_entitlements = true`.
- Treat leaked aggregate reservations after abrupt worker termination as the same accepted operational limitation as legacy API-key accounting; remediation is manual until a separate recovery design is introduced.
- Replace the temporary global visibility marker for user-feed entries with per-user authorization before enabling token charging.
- The per-route `enforce_entitlements` setting provides rollback without deleting accounting data; disabling it on a
  user-feed route restores unrestricted legacy behavior for that route and must therefore be treated as a security-
  and billing-sensitive operation in production.
- Before removal of user API keys, reevaluate configured-key capacity, API-key-covered access rules, and the legacy `tokens_cost` cleanup plan.

## Open question before implementation

The following decision affects reporting and future correction workflows:

1. **Pooled usage attribution:** `lifetime_token_usage` is shared across all grants and cannot identify which purchase or grant funded a user-entry. Is aggregate accounting sufficient, or will refunds, chargebacks, support corrections, or reporting require an attribution policy?

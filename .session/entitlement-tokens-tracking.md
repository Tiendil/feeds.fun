# Entitlement token tracking for backend tag processing

## Goal

The dispatcher owns entry authorization, SaaS-token reservation and consumption, and tag visibility. The librarian
continues to own tag processing and its legacy API-key cost tracking.

One dispatcher processing cycle costs one SaaS token for each linked user authorized through entitlements. The charge
does not depend on the number of tag processors, the number of provider requests, or provider-reported LLM tokens.

This is a transition design. Stored user API keys and the librarian's legacy `tokens_cost` accounting will be removed
after the application fully switches to entitlements and real payments.

## Scope

This design covers:

- dispatcher-level entry authorization;
- daily, monthly, and lifetime SaaS-token pools;
- reservation, settlement, and release;
- temporary coexistence with stored user API keys;
- global and per-user tag visibility;
- the existing route-level configured API key;
- processor fan-out and failure behavior.

It does not cover payment-provider protocols, prices, purchase UI, retroactive authorization, reprocessing after a
grant, durable per-entry billing identities, or stale-reservation recovery.

## Terms

- `SaaS token` — an internal access unit. One token authorizes one linked user for one dispatcher processing cycle.
- `LLM token` — provider-reported input or output usage. It remains part of legacy API-key cost tracking and has no
  conversion to SaaS tokens.
- `processing cycle` — one entry passing the dispatcher authorization gate and being offered to all configured tag
  processors.
- `reservation` — capacity atomically held for one user before processor fan-out.
- `settlement` — conversion of a reservation to used capacity after fan-out completes, or release with zero usage
  when fan-out fails.
- `global visibility` — a global `can_see_tags` marker that makes tags visible to every user.
- `per-user visibility` — a user-scoped `can_see_tags` marker created after that user's reservation settles.
- `configured API key` — the operator-owned key on a processor route.
- `stored user API key` — a user-owned provider key in user settings.

## Ownership

### Dispatcher

The dispatcher:

- discovers collection membership and users linked to an entry's source feeds;
- applies the one entry-level authorization gate;
- reserves and settles entitlement resources;
- decides which users may see tags;
- offers each authorized entry to every configured processor;
- acknowledges the source queue record after fan-out, settlement, and visibility updates.

Authorization is not repeated per processor. Processor-specific status, targeting, and route filters may decide that a
particular processor does not need an authorized entry, but those filters do not change authorization or accounting.

### Librarian

The librarian:

- processes entries already authorized and dispatched;
- selects the actual LLM credential;
- retains the old user API-key `tokens_cost` reservation and provider-usage accounting;
- uses the route's configured API key as the fallback when no eligible user key is found.

The temporary `llm_general._api_key_usage` order is:

1. For a collection entry, use the route's configured key. Route validation guarantees that it exists.
2. Otherwise, search for an eligible linked user key with the existing LLM-framework selection logic.
3. If no eligible user key is found, use the route's configured key.
4. If neither key exists, skip processing.

The collection lookup in `llm_general` is temporary. When legacy user-key consumption is removed,
`_api_key_usage` should be reduced to configured-key usage or removed.

### Entitlements and resources

Entitlements define allowances. Resources store aggregate `used` and `reserved` counters. Processing does not mutate
entitlement records.

## No new route flag

There is no `enforce_entitlements` flag and no top-level entitlement deployment setting.

The configured API key remains a route setting in the existing `[[tag_processors.routes]]` configuration. Its presence
provides a credential; dispatcher authorization follows the unified rules below regardless of route configuration.

## Resource model

All pools use:

```text
available = max(allowance - used - reserved, 0)
```

The resource kinds have stable integer values:

| Resource kind | Value | Allowance | Interval |
| --- | ---: | --- | --- |
| `tokens_cost` | 2 | legacy API-key cost limit | existing monthly interval |
| `day_token_usage` | 3 | effective `day_tokens` entitlement | current UTC day |
| `month_token_usage` | 4 | effective `month_tokens` entitlement | current UTC month |
| `lifetime_token_usage` | 5 | effective `lifetime_tokens` entitlement | stable lifetime interval |

Historical value `1` is not reused. The resource table stores integer kinds, so adding these values requires no
database migration.

The charge is defined once:

```text
SAAS_TOKENS_PER_USER_ENTRY = 1
```

Each user reservation selects the first pool with sufficient capacity:

1. daily;
2. monthly;
3. lifetime.

A reservation is never split across pools. The final capacity check is atomic in the database. One user's failure does
not prevent other linked users from reserving capacity.

Daily intervals begin at 00:00 UTC. Monthly intervals begin at 00:00 UTC on the first day of the month. Lifetime usage
uses the shared `LIFETIME_INTERVAL_START_MARKER`, while lifetime entitlements use the shared
`LIFETIME_INTERVAL_END_MARKER`. These timestamps are persistence markers for representing an unbounded interval, not
semantic lifetime boundaries. The dispatcher captures the resource interval marker in the reservation and uses the
captured value during settlement; it does not recompute the interval after fan-out.

`lifetime_tokens` remains an additive entitlement represented with the shared end marker. Its effective value is a
cumulative allowance, not a remaining balance. Revocation or reduction does not rewrite historical usage.

## Dispatcher workflow

For every pulled batch, `dispatch_entries` performs the following sequence:

1. Resolve collection membership and entry-to-feed links.
2. Resolve unique users linked to each entry's source feeds.
3. Batch-detect linked users that have any stored API key through the user-settings domain.
4. Authorize each entry:
   - if it is in a collection, authorize it globally without entitlement consumption;
   - otherwise, if any linked user has a stored API key, authorize it globally without entitlement consumption;
   - otherwise, batch-load token entitlements and independently reserve one SaaS token for every linked user with
     available capacity;
   - if no reservation succeeds, do not dispatch the entry.
5. Mark a rejected entry as `skipped_by_dispatcher` for each processor to which it applies.
6. Offer every authorized entry to all processors. `_dispatch_entries_to_processor` may still filter by processor
   target, processing status, and route.
7. If the full processor fan-out returns successfully, convert all captured reservations to used capacity.
8. If processor fan-out raises, release all captured reservations and leave the source queue records unacknowledged.
9. Grant visibility:
   - collection and stored-user-key authorization receives a global marker;
   - entitlement authorization receives one user marker for each successfully settled reservation;
   - users without a settled reservation receive no marker.
10. Acknowledge the pulled source queue records.

The stored-user-key check is intentionally independent of the librarian's later provider-specific key eligibility and
selection. This temporary shortcut preserves the old global-access behavior during migration. It must be removed
together with legacy user-key consumption.

## Processing and accounting contract

The gate is per entry processing cycle, not per processor.

- An authorized entry is offered to every processor or to none.
- The charge is one token per entitlement-authorized user for the cycle.
- Two processors receiving the same entry do not cause two charges.
- A processor filtering the entry because of status, targeting, or route does not cancel or reduce the charge.
- Per-processor queue results are not unioned to decide accounting.
- Once the complete fan-out call returns, the entry counts as processed for SaaS-token accounting. Later tag-processor
  behavior is the responsibility of those processors.
- Provider request counts, input/output tokens, provider cost, produced tag count, and empty tag results do not alter
  the SaaS-token charge.

Legacy API-key accounting remains independent. If the librarian selects a user key, it continues reserving and
settling `tokens_cost` from actual provider usage. The dispatcher does not inspect or modify that accounting.

## Visibility contract

Collection entries and entries linked to any stored-key user retain global tag visibility during the migration.

For entitlement-only entries, visibility is per linked user:

- successful reservation plus successful settlement grants `can_see_tags`;
- no capacity grants no visibility;
- settlement failure grants no visibility.

The existing marker uniqueness rules make repeated visibility writes idempotent. A visibility marker is not a billing
identity and does not prevent a later processing cycle from charging again.

## Concurrency and failure behavior

- Resource reservation is authoritative and atomic per user and pool.
- Linked users and duplicate entry ids are deduplicated within one authorization batch.
- The same user is charged once per entry, even when linked through multiple source feeds.
- Reservations are held before processor fan-out.
- A normal fan-out exception releases reservations.
- Successful fan-out settles reservations before visibility is granted.
- Settlement is independent per user; a failed conversion withholds only that user's visibility.
- Process termination can leave aggregate capacity reserved because reservation identity exists only in memory.
- Separate retries or processing cycles can charge the same user and entry again.
- Unlinking after reservation does not invalidate already-authorized work.

Processor fan-out currently consists of multiple database operations and is not atomic across processor subqueues.
A later processor failure can therefore occur after an earlier processor queue write. The dispatcher still releases
the cycle's reservations and leaves the source record unacknowledged. Cross-processor transactional fan-out and
durable billing idempotency are separate future work.

## Required module changes

### Product and shared time representation

- Add stable resource kinds `day_token_usage`, `month_token_usage`, and `lifetime_token_usage`.
- Add `SAAS_TOKENS_PER_USER_ENTRY`.
- Add the UTC day-start helper alongside the existing month-start helper.
- Define the universal `LIFETIME_INTERVAL_START_MARKER` and `LIFETIME_INTERVAL_END_MARKER` representation sentinels
  in `ffun.domain.datetime_intervals`.
- Mirror new product resource kinds in API-facing resource enums that convert internal kinds by value.

### User settings and LLM framework

- Detect stored-key presence with one read-only user-settings batch query over all supported API-key setting kinds.
- Keep provider-specific eligibility, selection, and legacy cost reservation in the existing LLM-framework call path.

### Dispatcher

- Add the entry authorization/reservation context.
- Batch-load links, stored-key presence, and effective token entitlements.
- Reserve daily, then monthly, then lifetime resources for each entitlement candidate.
- Gate the full processor fan-out once per entry.
- Settle or release reservations after fan-out.
- Write global or per-user visibility from the authorization result.
- Add dependencies on entitlements, feed links, and resources, plus temporary user-settings access for the stored-key
  migration bypass.

### Librarian

- Keep legacy user-key lookup and `tokens_cost` accounting.
- Keep the collection-first and configured-route-key fallback logic in `llm_general._api_key_usage`.
- Do not add entitlement handling, visibility handling, or SaaS-token resource handling.

## Tests

Automated backend tests must cover:

1. collection entries are globally authorized and consume no SaaS resources;
2. any linked stored-key user causes temporary global authorization and consumes no SaaS resources;
3. no stored-key user falls back to independent entitlement reservations for every linked user;
4. users without capacity do not prevent users with capacity from being authorized;
5. daily, monthly, and lifetime selection follows strict precedence;
6. exhausted daily capacity falls back to monthly capacity;
7. one user linked through multiple feeds is charged once per entry;
8. entries with no authorized user are not sent to processor queues, are marked skipped, and are acknowledged;
9. one entitlement-authorized entry is offered to every processor but charged once;
10. processor-specific filtering does not change the charge;
11. successful fan-out converts reserved capacity to used and grants only settled-user visibility;
12. fan-out failure releases reservations, grants no entitlement visibility, and leaves the source record queued;
13. daily and monthly interval starts are UTC calendar boundaries, and lifetime persistence uses the shared start and
    end representation markers;
14. stored-key detection covers every supported provider setting;
15. librarian collection, user-key, configured-key fallback, and no-key behavior remain covered.

All development checks run through the project's Docker-backed scripts.

## Removal after migration

After real payments and full entitlement adoption:

- remove the dispatcher stored-user-key global bypass;
- remove legacy user-key selection and `tokens_cost` accounting from `llm_general`;
- simplify `_api_key_usage` to route-configured credentials;
- remove the temporary librarian collection lookup once collection handling is fully guaranteed upstream;
- keep dispatcher entitlement authorization, settlement, and per-user visibility as the normal path.

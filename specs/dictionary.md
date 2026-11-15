# Feeds Fun dictionary

## Goal of the document

This document defines Feeds Fun terminology that is shared by multiple specifications and dependency metadata rules.

## Scope

The scope of this specification is limited to project-specific terminology.

Detailed behavior, implementation requirements, and configuration schemas are out of scope.

## Terms

Terms defined in this section are stable project vocabulary. Project artifacts MUST use these terms when referring to the corresponding concepts and MUST preserve them across behavioral, architectural, implementation, and storage changes while their definitions remain accurate. A dictionary term MAY be renamed only when its existing name or definition has become incorrect or ambiguous.

- `feed` - an RSS, Atom, or similar source of news entries.
- `entry` - one news article or item loaded from a feed.
- `tag` - semantic label assigned to an entry.
- `rule` - user-defined score expression based on tags.
- `collection` - curated feed collection configuration.
- `integration` - external source-specific behavior, such as YouTube or Reddit support.
- `benefit parameter` - one named normalized whole-number value accepted by a benefit package template at materialization time.
- `benefit package template` - the locally controlled definition from which one configured product benefit can be materialized.
- `benefit package` - one concrete set of entitlement guarantees produced by materializing a benefit package template with normalized benefit parameters.
- `package materialization` - deterministic validation and application of normalized benefit parameters to one configured benefit package template.
- `entitlement guarantee` - one entitlement kind and integer value promised by a benefit package or another entitlement-granting product concept.
- `purchase state` - the current provider-independent understanding of one purchase at one provider update time.
- `benefit transaction` - one immutable accepted operation that records and atomically applies one complete purchased state.
- `business state` - every field of a current-state snapshot except its provider update time.
- `provider update time` - the authoritative time associated with provider-reported purchased state and used to order competing versions of that state.
- `provider status` - the open-ended lifecycle description received from the external authority for provider-reported purchased state.
- `audit record` - append-only durable record of a business change or event, including its actor and subject entities.
- `architecture test` - a test that verifies cross-cutting structural rules or conventions defined by an architecture specification.

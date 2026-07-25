# ADR 0003 — `TEXT + CHECK` constraints instead of native Postgres enums

**Status:** Accepted

## Context

Several columns hold a fixed vocabulary (request status, agent type, recommendation
action, run status, debate outcome, user role). Postgres offers a native `ENUM` type,
but altering one — e.g. adding a recommendation tier — requires `ALTER TYPE ... ADD
VALUE`, which cannot run inside a transaction and is awkward to roll back in a migration.

## Decision

Store these columns as `TEXT` (or `VARCHAR`) guarded by a `CHECK` constraint listing the
allowed values. The canonical vocabulary lives in `aegis_shared.contracts.enums` as
`str`-based Python enums; the same values serialize to JSON and persist to the DB.

## Consequences

- **Positive:** adding/removing a value is an ordinary, transactional migration.
- **Positive:** the app-layer enum is the single source of truth; DB integrity is still enforced.
- **Negative:** no database-level enum type object; ordering is lexical, not definition-order.
- **Trade-off accepted:** we prioritize painless schema evolution over native-enum ergonomics.

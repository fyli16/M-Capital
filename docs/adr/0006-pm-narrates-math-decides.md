# ADR 0006 — Deterministic decision, LLM-authored narrative

**Status:** Accepted

## Context

The Portfolio Manager must issue a recommendation (Strong Buy … Strong Sell) with a
confidence and a rationale. Letting the LLM freely choose the numeric decision makes the
system non-reproducible, hard to test, and hard to audit — unacceptable for anything
resembling investment research.

## Decision

**Split the decision from the prose.** A deterministic aggregator computes the action and
confidence from the analysts' post-debate stances, weighted by their self-reported
confidence, mapped to an action via fixed thresholds. The LLM is then asked only to
**author the narrative** (rationale, key risks, supporting factors) around that
pre-computed decision — it never changes the number.

## Consequences

- **Positive:** the decision is transparent, reproducible, and auditable; the maths is unit-tested.
- **Positive:** clean separation lets the fake LLM produce valid narratives offline.
- **Positive:** the debate materially shifts stances, so it genuinely influences the outcome.
- **Negative:** the aggregation heuristic (weights, thresholds) is hand-tuned, not learned.
- **Future:** replace the heuristic with a model calibrated on the `performance_tracking` outcomes.

# ADR 0007 — Reward good dissent in agent scoring

**Status:** Accepted

## Context

The performance-worker grades each recommendation after the 90-day outcome window and
attributes correctness back to individual agents to power the leaderboard. A naive rule
— "the agent is correct if the recommendation it fed into was correct" — punishes the
adversarial Risk Officer for arguing against calls that later fail, which is exactly its
job. It would also reward analysts for agreeing with lucky-but-wrong-reasoned calls.

## Decision

Score a contribution by whether the agent's **stance agreed with the outcome**, not with
the herd:

```
was_correct = (agent_supported == recommendation_was_correct)
```

An agent that supported a correct call is correct; an agent that **dissented from a call
that turned out wrong is also correct** (good dissent); supporting a wrong call or
dissenting from a right one is incorrect.

## Consequences

- **Positive:** the Risk Officer and other contrarians are scored fairly.
- **Positive:** the leaderboard measures judgment, not conformity; calibration is meaningful.
- **Negative:** "correct" is directional vs. a benchmark; it ignores magnitude and risk-adjustment.
- **Future:** incorporate excess-return magnitude and risk-adjusted attribution.

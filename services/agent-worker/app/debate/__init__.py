"""Debate subsystem: conflict detection + bounded, convergence-gated rounds."""

from .conflict import ConflictReport, detect_conflict, stance_of
from .controller import ArgumentText, RoundResult, run_debate_round

__all__ = [
    "ConflictReport",
    "detect_conflict",
    "stance_of",
    "ArgumentText",
    "RoundResult",
    "run_debate_round",
]

"""Base agent abstractions.

An ``AnalystAgent`` turns a ``ToolContext`` into a validated, structured output via
the LLM. Validation failures trigger a single repair attempt before the caller
decides to abstain — this is the contract that keeps downstream synthesis safe.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ValidationError

from aegis_shared.contracts import AgentType, BaseAgentOutput

from ..llm import LLMClient, LLMError, Usage
from ..tools import ToolContext


class Agent(ABC):
    agent_type: AgentType
    output_model: type[BaseModel]

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def user_prompt(self, ctx: ToolContext) -> str: ...


class AnalystAgent(Agent):
    """Produces a structured ``BaseAgentOutput`` subclass from context."""

    output_model: type[BaseAgentOutput]

    async def analyze(
        self, ctx: ToolContext, llm: LLMClient, *, repair: bool = True
    ) -> tuple[BaseAgentOutput, Usage]:
        system = self.system_prompt()
        user = self.user_prompt(ctx)
        try:
            out, usage = await llm.structured(
                system=system, user=user, schema=self.output_model
            )
        except (ValidationError, LLMError):
            if not repair:
                raise
            # One repair attempt with an explicit correction instruction.
            out, usage = await llm.structured(
                system=system + "\nReturn ONLY valid JSON matching the schema exactly.",
                user=user,
                schema=self.output_model,
            )
        # Enforce the agent's identity regardless of what the model emitted.
        out.agent_type = self.agent_type
        return out, usage


def _memory_block(ctx: ToolContext) -> str:
    if not ctx.memory_hits:
        return "No relevant prior analyses on record."
    lines = [
        f"- ({h.get('created_at', 'unknown')}) {h.get('summary', '')}"
        for h in ctx.memory_hits[:3]
    ]
    return "Relevant prior analyses:\n" + "\n".join(lines)

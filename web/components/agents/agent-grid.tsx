import { AgentCard } from "@/components/agents/agent-card";
import type { AgentRunView } from "@/lib/types/contracts";

const ORDER = ["news", "financial", "quant", "macro", "risk"];

export function AgentGrid({ runs }: { runs: AgentRunView[] }) {
  const analysts = runs
    .filter((r) => r.agent_type !== "portfolio_manager")
    .sort((a, b) => ORDER.indexOf(a.agent_type) - ORDER.indexOf(b.agent_type));

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {analysts.map((run) => (
        <AgentCard key={run.id} run={run} />
      ))}
    </div>
  );
}

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatusBadge, ConfidenceMeter } from "@/components/common/badges";
import { agentLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AgentRunView, AgentType } from "@/lib/types/contracts";
import {
  Newspaper,
  Calculator,
  LineChart,
  Globe,
  ShieldAlert,
  Briefcase,
} from "lucide-react";

const ICONS: Record<AgentType, React.ComponentType<{ className?: string }>> = {
  news: Newspaper,
  financial: Calculator,
  quant: LineChart,
  macro: Globe,
  risk: ShieldAlert,
  portfolio_manager: Briefcase,
};

/** Renders one analyst's card with its distinctive output shape. */
export function AgentCard({ run }: { run: AgentRunView }) {
  const Icon = ICONS[run.agent_type] ?? Briefcase;
  const output = run.output ?? {};
  const adversarial = run.agent_type === "risk";

  return (
    <Card className={cn(adversarial && "border-bear/40")}>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Icon className={cn("h-4 w-4", adversarial ? "text-bear" : "text-primary")} />
          {agentLabel(run.agent_type)}
        </CardTitle>
        <StatusBadge status={run.status} />
      </CardHeader>
      <CardContent className="space-y-3">
        {typeof output.summary === "string" && (
          <p className="text-sm text-muted-foreground">{output.summary}</p>
        )}
        <AgentOutputDetails type={run.agent_type} output={output} />
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground">Confidence</span>
          <ConfidenceMeter value={run.confidence} />
        </div>
      </CardContent>
    </Card>
  );
}

function List({ title, items, tone }: { title: string; items?: unknown; tone: string }) {
  const arr = Array.isArray(items) ? (items as string[]) : [];
  if (arr.length === 0) return null;
  return (
    <div>
      <p className={cn("mb-1 text-xs font-medium", tone)}>{title}</p>
      <ul className="space-y-0.5 text-sm">
        {arr.slice(0, 4).map((it, i) => (
          <li key={i} className="text-muted-foreground">
            • {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AgentOutputDetails({
  type,
  output,
}: {
  type: AgentType;
  output: Record<string, unknown>;
}) {
  switch (type) {
    case "news":
      return (
        <div className="space-y-2">
          <List title="Bullish" items={output.bullish_points} tone="text-bull" />
          <List title="Bearish" items={output.bearish_points} tone="text-bear" />
        </div>
      );
    case "financial":
      return (
        <div className="space-y-2">
          <List title="Strengths" items={output.strengths} tone="text-bull" />
          <List title="Weaknesses" items={output.weaknesses} tone="text-bear" />
        </div>
      );
    case "quant":
      return <List title="Technical Signals" items={output.technical_signals} tone="text-primary" />;
    case "macro":
      return (
        <div className="space-y-2">
          <List title="Opportunities" items={output.opportunities} tone="text-bull" />
          <List title="Threats" items={output.threats} tone="text-bear" />
        </div>
      );
    case "risk":
      return (
        <div className="space-y-2">
          <List title="Dangers" items={output.dangers} tone="text-bear" />
          <List title="Stress Scenarios" items={output.stress_scenarios} tone="text-neutral" />
        </div>
      );
    default:
      return null;
  }
}

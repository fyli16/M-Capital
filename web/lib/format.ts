import type {
  AgentType,
  RecommendationAction,
  RequestStatus,
  RunStatus,
} from "@/lib/types/contracts";

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function signedPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  const s = value >= 0 ? "+" : "";
  return `${s}${(value * 100).toFixed(digits)}%`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

const ACTION_LABELS: Record<RecommendationAction, string> = {
  strong_buy: "Strong Buy",
  buy: "Buy",
  hold: "Hold",
  sell: "Sell",
  strong_sell: "Strong Sell",
};

export function actionLabel(action: RecommendationAction): string {
  return ACTION_LABELS[action] ?? action;
}

/** Tailwind classes for a recommendation action pill. */
export function actionClasses(action: RecommendationAction): string {
  switch (action) {
    case "strong_buy":
      return "bg-bull/20 text-bull border-bull/40";
    case "buy":
      return "bg-bull/10 text-bull border-bull/30";
    case "hold":
      return "bg-neutral/15 text-neutral border-neutral/40";
    case "sell":
      return "bg-bear/10 text-bear border-bear/30";
    case "strong_sell":
      return "bg-bear/20 text-bear border-bear/40";
  }
}

const AGENT_LABELS: Record<AgentType, string> = {
  news: "News Intelligence",
  financial: "Financial Analyst",
  quant: "Quantitative Analyst",
  macro: "Macro Analyst",
  risk: "Risk Officer",
  portfolio_manager: "Portfolio Manager",
};

export function agentLabel(agent: AgentType): string {
  return AGENT_LABELS[agent] ?? agent;
}

export function statusClasses(status: RequestStatus | RunStatus): string {
  switch (status) {
    case "complete":
      return "bg-bull/15 text-bull border-bull/30";
    case "failed":
      return "bg-bear/15 text-bear border-bear/30";
    case "abstained":
      return "bg-muted text-muted-foreground border-border";
    case "running":
    case "debating":
      return "bg-primary/15 text-primary border-primary/30";
    default:
      return "bg-secondary text-secondary-foreground border-border";
  }
}

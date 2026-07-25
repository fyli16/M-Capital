/**
 * Aegis Capital — shared contract types (frontend).
 *
 * Hand-authored mirror of `packages/aegis_shared/contracts`. Keep in sync with the
 * Python source of truth. In CI, `make export-schemas` emits JSON Schema which can
 * generate this file automatically (planned: `openapi-typescript`).
 */

// ---- Enums ------------------------------------------------------------------

export type UserRole = "viewer" | "analyst" | "admin";

export type RequestStatus =
  | "queued"
  | "running"
  | "debating"
  | "complete"
  | "failed";

export type AgentType =
  | "news"
  | "financial"
  | "quant"
  | "macro"
  | "risk"
  | "portfolio_manager";

export type RunStatus =
  | "pending"
  | "running"
  | "complete"
  | "failed"
  | "abstained";

export type RecommendationAction =
  | "strong_buy"
  | "buy"
  | "hold"
  | "sell"
  | "strong_sell";

export type DebateOutcome =
  | "no_conflict"
  | "consensus"
  | "converged"
  | "max_rounds";

// ---- Agent outputs ----------------------------------------------------------

export interface Evidence {
  claim: string;
  source: string;
  excerpt?: string | null;
}

export interface BaseAgentOutput {
  agent_type: AgentType;
  confidence: number;
  sources: Evidence[];
  summary: string;
}

export interface NewsAnalystOutput extends BaseAgentOutput {
  agent_type: "news";
  bullish_points: string[];
  bearish_points: string[];
  sentiment_score: number; // [-1, 1]
}

export interface FinancialAnalystOutput extends BaseAgentOutput {
  agent_type: "financial";
  fundamentals_score: number;
  valuation_score: number;
  strengths: string[];
  weaknesses: string[];
}

export interface QuantAnalystOutput extends BaseAgentOutput {
  agent_type: "quant";
  quant_score: number;
  technical_signals: string[];
  risk_metrics: Record<string, number>;
}

export interface MacroAnalystOutput extends BaseAgentOutput {
  agent_type: "macro";
  macro_score: number;
  opportunities: string[];
  threats: string[];
}

export interface RiskOfficerOutput extends BaseAgentOutput {
  agent_type: "risk";
  overall_risk_score: number;
  dangers: string[];
  stress_scenarios: string[];
}

export interface PortfolioManagerOutput {
  recommendation: RecommendationAction;
  confidence: number;
  rationale: string;
  key_risks: string[];
  supporting_factors: string[];
}

// ---- Debate -----------------------------------------------------------------

export interface DebateTurn {
  round: number;
  agent_type: AgentType;
  argument: string;
  rebuts?: AgentType | null;
}

export interface DebateTranscript {
  turns: DebateTurn[];
  rounds: number;
}

// ---- API DTOs ---------------------------------------------------------------

export interface CreateResearchRequest {
  ticker: string;
  enable_debate?: boolean;
  max_debate_rounds?: number;
}

export interface ResearchRequestAccepted {
  request_id: string;
  status: RequestStatus;
  stream_url: string;
}

export interface AgentRunView {
  id: string;
  agent_type: AgentType;
  status: RunStatus;
  confidence?: number | null;
  latency_ms?: number | null;
  tokens_in?: number | null;
  tokens_out?: number | null;
  output?: Record<string, unknown> | null;
}

export interface RecommendationView {
  id: string;
  ticker: string;
  action: RecommendationAction;
  confidence: number;
  rationale: string;
  key_risks: string[];
  supporting_factors: string[];
  created_at: string;
}

export interface ResearchResultView {
  request_id: string;
  ticker: string;
  status: RequestStatus;
  created_at: string;
  agent_runs: AgentRunView[];
  debate?: DebateTranscript | null;
  recommendation?: RecommendationView | null;
}

export interface AgentScorecard {
  agent_type: AgentType;
  total_contributions: number;
  accuracy: number;
  avg_confidence: number;
  calibration_gap: number;
}

export interface PerformanceLeaderboard {
  scorecards: AgentScorecard[];
  best_agent?: AgentType | null;
  worst_agent?: AgentType | null;
}

export interface MemorySearchRequest {
  query: string;
  ticker?: string | null;
  limit?: number;
}

export interface MemoryHit {
  memory_id: string;
  ticker: string;
  summary: string;
  created_at: string;
  similarity: number;
}

export interface MemorySearchResponse {
  query: string;
  hits: MemoryHit[];
}

export interface HealthResponse {
  status: string;
  database: boolean;
  redis: boolean;
  queue: boolean;
}

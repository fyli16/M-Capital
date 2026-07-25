"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/page-header";
import { ConfidenceMeter } from "@/components/common/badges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPerformance } from "@/lib/api/client";
import { agentLabel, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AgentScorecard, PerformanceLeaderboard } from "@/lib/types/contracts";

export default function ScorecardsPage() {
  const [board, setBoard] = useState<PerformanceLeaderboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPerformance()
      .then(setBoard)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  return (
    <div>
      <PageHeader
        title="Agent Scorecards"
        description="Per-agent track record and calibration — is the agent as right as it is confident?"
      />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      {!board ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      ) : board.scorecards.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No scored contributions yet.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {board.scorecards.map((s) => (
            <ScorecardCard
              key={s.agent_type}
              card={s}
              best={s.agent_type === board.best_agent}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ScorecardCard({ card, best }: { card: AgentScorecard; best: boolean }) {
  const overconfident = card.calibration_gap > 0.1;
  return (
    <Card className={cn(best && "border-bull/40")}>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm">{agentLabel(card.agent_type)}</CardTitle>
        {best && (
          <span className="rounded-full bg-bull/15 px-2 py-0.5 text-xs text-bull">
            Top
          </span>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <Metric label="Accuracy">
          <ConfidenceMeter value={card.accuracy} />
        </Metric>
        <Metric label="Avg confidence">
          <ConfidenceMeter value={card.avg_confidence} />
        </Metric>
        <div className="flex items-center justify-between border-t border-border pt-3 text-sm">
          <span className="text-muted-foreground">Calibration gap</span>
          <span
            className={cn(
              "font-mono",
              overconfident ? "text-bear" : "text-muted-foreground"
            )}
          >
            {card.calibration_gap >= 0 ? "+" : ""}
            {pct(card.calibration_gap, 0)}
            {overconfident && " (overconfident)"}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          {card.total_contributions} scored contribution
          {card.total_contributions === 1 ? "" : "s"}
        </p>
      </CardContent>
    </Card>
  );
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

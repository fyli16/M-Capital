"use client";

import { useEffect, useState } from "react";
import { Award, TrendingDown } from "lucide-react";

import { PageHeader } from "@/components/common/page-header";
import { ScorecardChart } from "@/components/charts/scorecard-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPerformance } from "@/lib/api/client";
import { agentLabel } from "@/lib/format";
import type { PerformanceLeaderboard } from "@/lib/types/contracts";

export default function PerformancePage() {
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
        title="Historical Performance"
        description="Realized agent accuracy after the 90-day outcome window closes."
      />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      {!board ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
          <Skeleton className="h-72" />
        </div>
      ) : board.scorecards.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No graded recommendations yet — performance appears once positions mature.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Highlight
              title="Top Performer"
              agent={board.best_agent}
              icon={<Award className="h-5 w-5 text-bull" />}
              tone="border-bull/40"
            />
            <Highlight
              title="Needs Attention"
              agent={board.worst_agent}
              icon={<TrendingDown className="h-5 w-5 text-bear" />}
              tone="border-bear/40"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Accuracy vs. Confidence by agent</CardTitle>
            </CardHeader>
            <CardContent>
              <ScorecardChart scorecards={board.scorecards} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function Highlight({
  title,
  agent,
  icon,
  tone,
}: {
  title: string;
  agent: string | null | undefined;
  icon: React.ReactNode;
  tone: string;
}) {
  return (
    <Card className={tone}>
      <CardContent className="flex items-center gap-4 py-6">
        {icon}
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {title}
          </p>
          <p className="text-lg font-semibold">
            {agent ? agentLabel(agent as never) : "—"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

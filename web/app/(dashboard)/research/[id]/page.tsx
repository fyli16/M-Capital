"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/badges";
import { AgentGrid } from "@/components/agents/agent-grid";
import { DebateViewer } from "@/components/agents/debate-viewer";
import { RecommendationCard } from "@/components/agents/recommendation-card";
import { AgentConfidenceChart } from "@/components/charts/agent-confidence-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { getResearch } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { RequestStatus, ResearchResultView } from "@/lib/types/contracts";

const TERMINAL: RequestStatus[] = ["complete", "failed"];
const STEPS: RequestStatus[] = ["queued", "running", "debating", "complete"];

export default function ResearchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<ResearchResultView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const r = await getResearch(id);
      setResult(r);
      return r.status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      return "failed" as RequestStatus;
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      const status = await poll();
      if (!active) return;
      if (!TERMINAL.includes(status)) timer = setTimeout(tick, 2000);
    };
    tick();

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [poll]);

  if (error) {
    return (
      <Card className="border-bear/40">
        <CardContent className="flex items-center gap-3 py-8 text-bear">
          <AlertTriangle className="h-5 w-5" /> {error}
        </CardContent>
      </Card>
    );
  }

  if (!result) return <DetailSkeleton />;

  const running = !TERMINAL.includes(result.status);

  return (
    <div>
      <PageHeader
        title={`${result.ticker}`}
        description={`Request ${result.request_id.slice(0, 8)}`}
        actions={
          <Link
            href="/research"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> New research
          </Link>
        }
      />

      <StatusStepper status={result.status} />

      {result.recommendation && (
        <div className="my-6">
          <RecommendationCard
            recommendation={result.recommendation}
            ticker={result.ticker}
          />
        </div>
      )}

      <Tabs defaultValue="agents" className="mt-6">
        <TabsList>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="debate">Debate</TabsTrigger>
          <TabsTrigger value="votes">Confidence</TabsTrigger>
        </TabsList>

        <TabsContent value="agents">
          {result.agent_runs.length === 0 ? (
            <RunningNotice running={running} />
          ) : (
            <AgentGrid runs={result.agent_runs} />
          )}
        </TabsContent>

        <TabsContent value="debate">
          <DebateViewer debate={result.debate} />
        </TabsContent>

        <TabsContent value="votes">
          <Card>
            <CardHeader>
              <CardTitle>Analyst confidence</CardTitle>
            </CardHeader>
            <CardContent>
              {result.agent_runs.length === 0 ? (
                <RunningNotice running={running} />
              ) : (
                <AgentConfidenceChart runs={result.agent_runs} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatusStepper({ status }: { status: RequestStatus }) {
  const activeIndex =
    status === "failed" ? -1 : STEPS.indexOf(status === "complete" ? "complete" : status);
  return (
    <div className="flex items-center gap-2">
      {STEPS.map((step, i) => {
        const done = activeIndex >= i && status !== "failed";
        return (
          <div key={step} className="flex items-center gap-2">
            <div
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-1 text-xs capitalize",
                done
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border text-muted-foreground"
              )}
            >
              {step === status && !TERMINAL.includes(status) && (
                <Loader2 className="h-3 w-3 animate-spin" />
              )}
              {step}
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn("h-px w-6", done ? "bg-primary/40" : "bg-border")} />
            )}
          </div>
        );
      })}
      {status === "failed" && <StatusBadge status="failed" />}
    </div>
  );
}

function RunningNotice({ running }: { running: boolean }) {
  return (
    <div className="flex items-center gap-3 py-10 text-muted-foreground">
      {running ? (
        <>
          <Loader2 className="h-5 w-5 animate-spin" /> Agents are working — results
          stream in as they complete.
        </>
      ) : (
        "No agent output was recorded."
      )}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-8 w-full max-w-md" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-48" />
        ))}
      </div>
    </div>
  );
}

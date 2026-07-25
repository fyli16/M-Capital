"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Loader2 } from "lucide-react";

import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { submitResearch } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { loadRecent, pushRecent, type RecentRequest } from "@/lib/recent";

export default function ResearchPage() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [debate, setDebate] = useState(true);
  const [rounds, setRounds] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<RecentRequest[]>([]);

  useEffect(() => setRecent(loadRecent()), []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const t = ticker.trim().toUpperCase();
      const res = await submitResearch({
        ticker: t,
        enable_debate: debate,
        max_debate_rounds: rounds,
      });
      pushRecent({ id: res.request_id, ticker: t, submittedAt: new Date().toISOString() });
      router.push(`/research/${res.request_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="New Research"
        description="Dispatch the analyst team to investigate a publicly traded stock."
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Analyze a stock</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <Label htmlFor="ticker">Ticker</Label>
                <Input
                  id="ticker"
                  placeholder="NVDA"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  required
                  pattern="[A-Za-z][A-Za-z0-9.\-]{0,9}"
                  className="uppercase"
                />
              </div>

              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={debate}
                  onChange={(e) => setDebate(e.target.checked)}
                  className="h-4 w-4 accent-[hsl(199,89%,48%)]"
                />
                Enable adversarial debate phase
              </label>

              <div className="space-y-1.5">
                <Label htmlFor="rounds">Max debate rounds</Label>
                <Input
                  id="rounds"
                  type="number"
                  min={0}
                  max={5}
                  value={rounds}
                  onChange={(e) => setRounds(Number(e.target.value))}
                  disabled={!debate}
                  className="w-24"
                />
              </div>

              {error && <p className="text-sm text-bear">{error}</p>}

              <Button type="submit" disabled={busy} className="w-full">
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Dispatching agents…
                  </>
                ) : (
                  <>
                    Run analysis <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent requests</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {recent.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Your submitted analyses will appear here.
              </p>
            )}
            {recent.map((r) => (
              <Link
                key={r.id}
                href={`/research/${r.id}`}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm transition-colors hover:bg-accent"
              >
                <span className="font-mono font-medium">{r.ticker}</span>
                <span className="text-xs text-muted-foreground">
                  {formatDate(r.submittedAt)}
                </span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

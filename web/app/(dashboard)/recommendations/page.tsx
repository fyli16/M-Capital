"use client";

import { useCallback, useEffect, useState } from "react";
import { Search } from "lucide-react";

import { PageHeader } from "@/components/common/page-header";
import { ActionBadge, ConfidenceMeter } from "@/components/common/badges";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listRecommendations } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import type { RecommendationView } from "@/lib/types/contracts";

export default function RecommendationsPage() {
  const [rows, setRows] = useState<RecommendationView[] | null>(null);
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (t?: string) => {
    setError(null);
    try {
      setRows(await listRecommendations({ ticker: t || undefined, limit: 50 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setRows([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <PageHeader
        title="Recommendations"
        description="Every decision the Portfolio Manager has issued."
        actions={
          <form
            onSubmit={(e) => {
              e.preventDefault();
              load(ticker.trim().toUpperCase());
            }}
            className="flex gap-2"
          >
            <Input
              placeholder="Filter ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="h-9 w-36 uppercase"
            />
            <Button type="submit" size="sm" variant="secondary">
              <Search className="h-4 w-4" />
            </Button>
          </form>
        }
      />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <Card>
        <CardContent className="p-0">
          {rows === null ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted-foreground">
              No recommendations yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Rationale</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono font-medium">{r.ticker}</TableCell>
                    <TableCell>
                      <ActionBadge action={r.action} />
                    </TableCell>
                    <TableCell>
                      <ConfidenceMeter value={r.confidence} />
                    </TableCell>
                    <TableCell className="max-w-md truncate text-muted-foreground">
                      {r.rationale}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {formatDate(r.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

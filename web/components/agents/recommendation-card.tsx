import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ActionBadge, ConfidenceMeter } from "@/components/common/badges";
import { actionClasses } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RecommendationView } from "@/lib/types/contracts";
import { ShieldAlert, TrendingUp } from "lucide-react";

export function RecommendationCard({
  recommendation,
  ticker,
}: {
  recommendation: RecommendationView;
  ticker?: string;
}) {
  return (
    <Card className={cn("border-2", actionClasses(recommendation.action))}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {ticker ? `${ticker} — ` : ""}Portfolio Manager Decision
          </CardTitle>
          <ActionBadge action={recommendation.action} className="text-sm" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Conviction</span>
          <ConfidenceMeter value={recommendation.confidence} />
        </div>

        <p className="text-sm leading-relaxed">{recommendation.rationale}</p>

        <div className="grid gap-4 sm:grid-cols-2">
          <Column
            title="Supporting Factors"
            icon={<TrendingUp className="h-4 w-4 text-bull" />}
            items={recommendation.supporting_factors}
            tone="text-bull"
          />
          <Column
            title="Key Risks"
            icon={<ShieldAlert className="h-4 w-4 text-bear" />}
            items={recommendation.key_risks}
            tone="text-bear"
          />
        </div>
      </CardContent>
    </Card>
  );
}

function Column({
  title,
  icon,
  items,
  tone,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  tone: string;
}) {
  return (
    <div>
      <p className={cn("mb-2 flex items-center gap-1.5 text-sm font-medium", tone)}>
        {icon}
        {title}
      </p>
      <ul className="space-y-1 text-sm text-muted-foreground">
        {items.length === 0 && <li>—</li>}
        {items.map((it, i) => (
          <li key={i}>• {it}</li>
        ))}
      </ul>
    </div>
  );
}

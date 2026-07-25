import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  actionClasses,
  actionLabel,
  pct,
  statusClasses,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  RecommendationAction,
  RequestStatus,
  RunStatus,
} from "@/lib/types/contracts";

export function StatusBadge({ status }: { status: RequestStatus | RunStatus }) {
  return (
    <Badge className={cn("capitalize", statusClasses(status))}>{status}</Badge>
  );
}

export function ActionBadge({
  action,
  className,
}: {
  action: RecommendationAction;
  className?: string;
}) {
  return (
    <Badge className={cn("font-semibold", actionClasses(action), className)}>
      {actionLabel(action)}
    </Badge>
  );
}

export function ConfidenceMeter({
  value,
  className,
}: {
  value: number | null | undefined;
  className?: string;
}) {
  const v = value ?? 0;
  const color =
    v >= 0.66 ? "bg-bull" : v >= 0.4 ? "bg-neutral" : "bg-bear";
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Progress value={v * 100} indicatorClassName={color} className="w-24" />
      <span className="w-10 text-right font-mono text-xs text-muted-foreground">
        {pct(value, 0)}
      </span>
    </div>
  );
}

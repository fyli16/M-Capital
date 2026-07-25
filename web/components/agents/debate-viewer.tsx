import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { agentLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { DebateTranscript } from "@/lib/types/contracts";
import { MessagesSquare, Swords } from "lucide-react";

export function DebateViewer({ debate }: { debate: DebateTranscript | null | undefined }) {
  if (!debate || debate.turns.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-8 text-muted-foreground">
          <MessagesSquare className="h-5 w-5" />
          No debate was triggered — the analysts were sufficiently aligned.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2">
          <Swords className="h-4 w-4 text-primary" />
          Debate Transcript
        </CardTitle>
        <span className="text-xs text-muted-foreground">
          {debate.rounds} round{debate.rounds === 1 ? "" : "s"}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        {debate.turns.map((turn, i) => {
          const bull = i % 2 === 0;
          return (
            <div
              key={i}
              className={cn("flex", bull ? "justify-start" : "justify-end")}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg border p-3 text-sm",
                  bull
                    ? "border-bull/30 bg-bull/5"
                    : "border-bear/30 bg-bear/5"
                )}
              >
                <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    {agentLabel(turn.agent_type)}
                  </span>
                  <span>Round {turn.round}</span>
                  {turn.rebuts && <span>· rebuts {agentLabel(turn.rebuts)}</span>}
                </div>
                <p>{turn.argument}</p>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

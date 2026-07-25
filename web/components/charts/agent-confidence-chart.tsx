"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { agentLabel } from "@/lib/format";
import type { AgentRunView } from "@/lib/types/contracts";

const ORDER = ["news", "financial", "quant", "macro", "risk"];

export function AgentConfidenceChart({ runs }: { runs: AgentRunView[] }) {
  const data = runs
    .filter((r) => r.agent_type !== "portfolio_manager" && r.confidence != null)
    .sort((a, b) => ORDER.indexOf(a.agent_type) - ORDER.indexOf(b.agent_type))
    .map((r) => ({
      agent: agentLabel(r.agent_type).split(" ")[0],
      confidence: Math.round((r.confidence ?? 0) * 100),
      adversarial: r.agent_type === "risk",
    }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <XAxis
          dataKey="agent"
          tick={{ fontSize: 12, fill: "hsl(215 20% 65%)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12, fill: "hsl(215 20% 65%)" }}
          axisLine={false}
          tickLine={false}
          unit="%"
        />
        <Tooltip
          cursor={{ fill: "hsl(217 33% 17% / 0.4)" }}
          contentStyle={{
            background: "hsl(222 44% 9%)",
            border: "1px solid hsl(217 33% 18%)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="confidence" radius={[4, 4, 0, 0]} unit="%">
          {data.map((d, i) => (
            <Cell
              key={i}
              fill={d.adversarial ? "hsl(0 72% 55%)" : "hsl(199 89% 48%)"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

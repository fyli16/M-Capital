"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { agentLabel } from "@/lib/format";
import type { AgentScorecard } from "@/lib/types/contracts";

export function ScorecardChart({ scorecards }: { scorecards: AgentScorecard[] }) {
  const data = scorecards.map((s) => ({
    agent: agentLabel(s.agent_type).split(" ")[0],
    Accuracy: Math.round(s.accuracy * 100),
    "Avg Confidence": Math.round(s.avg_confidence * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" vertical={false} />
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
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Accuracy" fill="hsl(152 69% 45%)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Avg Confidence" fill="hsl(199 89% 48%)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

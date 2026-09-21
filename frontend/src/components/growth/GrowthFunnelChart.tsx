import { ResponsiveContainer, FunnelChart, Funnel, LabelList, Tooltip, Cell } from "recharts";
import type { FunnelStageCounts } from "../../api/hubs/growth";
import { formatCount } from "../../lib/formatters";
import "./GrowthFunnelChart.css";

// Mirrors src/styles/tokens.css — literal hex for SVG rendering reliability,
// same reasoning as the Revenue charts.
const STAGE_FILLS = ["#1e3a8a", "#2d4ea3", "#3d63bd", "#5479c7", "#7b94d3", "#a3b3de"];

const STAGE_LABELS: Record<keyof FunnelStageCounts, string> = {
  registrations: "Registrations",
  kyc_started: "KYC Started",
  kyc_approved: "KYC Approved",
  activated: "Activated",
  first_transaction: "First Transaction",
  premium_upgrades: "Premium Upgrade",
};

export function GrowthFunnelChart({ stageCounts }: { stageCounts: FunnelStageCounts }) {
  const data = (Object.keys(STAGE_LABELS) as (keyof FunnelStageCounts)[]).map((key) => ({
    key,
    name: STAGE_LABELS[key],
    value: stageCounts[key],
  }));

  return (
    <div className="atlas-growth-funnel-chart">
      <ResponsiveContainer width="100%" height={280}>
        <FunnelChart margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
          <Tooltip formatter={(value) => (typeof value === "number" ? formatCount(value) : String(value))} />
          <Funnel dataKey="value" data={data} isAnimationActive={false}>
            <LabelList dataKey="name" position="right" fill="#10192e" fontSize={12} />
            <LabelList
              dataKey="value"
              position="center"
              fill="#ffffff"
              fontSize={12}
              formatter={(value) => (typeof value === "number" ? formatCount(value) : "")}
            />
            {data.map((entry, i) => (
              <Cell key={entry.key} fill={STAGE_FILLS[i % STAGE_FILLS.length]} />
            ))}
          </Funnel>
        </FunnelChart>
      </ResponsiveContainer>
    </div>
  );
}

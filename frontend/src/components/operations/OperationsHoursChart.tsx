import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { formatHours } from "../../lib/formatters";
import type { CategoryValueRow } from "./OperationsPercentChart";
import "./OperationsChart.css";

// Mirrors src/styles/tokens.css — literal hex, same reasoning as every other chart.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";

export function OperationsHoursChart({
  rows,
  seriesName,
}: {
  rows: CategoryValueRow[];
  seriesName: string;
}) {
  return (
    <div className="atlas-operations-chart">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COLOR_BORDER} vertical={false} />
          <XAxis
            dataKey="category"
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={{ stroke: COLOR_BORDER }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatHours}
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatHours(value) : String(value)
            }
          />
          <Bar dataKey="value" name={seriesName} fill={COLOR_ACCENT} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { ActivationTrendPoint } from "../../api/hubs/growth";
import { formatPercentPoints } from "../../lib/formatters";
import "./ActivationTrendChart.css";

// Mirrors src/styles/tokens.css — literal hex, same reasoning as the other charts.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";

export function ActivationTrendChart({ series }: { series: ActivationTrendPoint[] }) {
  return (
    <div className="atlas-activation-chart">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COLOR_BORDER} vertical={false} />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={{ stroke: COLOR_BORDER }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(value: number) => `${value}%`}
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatPercentPoints(value) : String(value)
            }
          />
          <Line
            type="monotone"
            dataKey="activation_rate"
            name="Activation rate"
            stroke={COLOR_ACCENT}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { RevenueTrendPoint } from "../../api/hubs/revenue";
import { formatCurrency, formatCurrencyCompact } from "../../lib/formatters";
import "./RevenueTrendChart.css";

// Recharts renders these as raw SVG presentation attributes, which don't
// reliably resolve CSS custom properties across browsers — so these
// mirror the literal values in src/styles/tokens.css rather than
// referencing var(--atlas-*) directly.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";

export function RevenueTrendChart({ series }: { series: RevenueTrendPoint[] }) {
  return (
    <div className="atlas-revenue-trend-chart">
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
            tickFormatter={formatCurrencyCompact}
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={64}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatCurrency(value) : String(value)
            }
            contentStyle={{
              fontSize: 12,
              fontFamily: "Inter, sans-serif",
              border: `1px solid ${COLOR_BORDER}`,
              borderRadius: "4px",
            }}
          />
          <Line
            type="monotone"
            dataKey="actual"
            name="Actual revenue"
            stroke={COLOR_ACCENT}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

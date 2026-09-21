import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { formatCurrency, formatCurrencyCompact } from "../../lib/formatters";
import "./SegmentRevenueChart.css";

// Mirrors src/styles/tokens.css — literal hex, same reasoning as the other charts.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";

interface SegmentRow {
  segment: string;
  revenue: number;
}

export function SegmentRevenueChart({ rows }: { rows: SegmentRow[] }) {
  return (
    <div className="atlas-segment-chart">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COLOR_BORDER} vertical={false} />
          <XAxis
            dataKey="segment"
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
          />
          <Bar dataKey="revenue" name="Net revenue" fill={COLOR_ACCENT} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

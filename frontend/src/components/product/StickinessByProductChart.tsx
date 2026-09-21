import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { formatRatioValue } from "../../lib/formatters";
import "./ProductBarChart.css";

// Mirrors src/styles/tokens.css — literal hex, same reasoning as every other chart.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";

interface Row {
  product: string;
  value: number;
}

export function StickinessByProductChart({ rows }: { rows: Row[] }) {
  return (
    <div className="atlas-product-bar-chart">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COLOR_BORDER} vertical={false} />
          <XAxis
            dataKey="product"
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={{ stroke: COLOR_BORDER }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatRatioValue}
            tick={{ fontSize: 11, fill: COLOR_INK_MUTED }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatRatioValue(value) : String(value)
            }
          />
          <Bar dataKey="value" name="DAU/MAU" fill={COLOR_ACCENT} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

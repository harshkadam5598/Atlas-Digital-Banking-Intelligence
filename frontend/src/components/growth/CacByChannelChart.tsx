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
import "./CacByChannelChart.css";

// Mirrors src/styles/tokens.css — literal hex, same reasoning as the other charts.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";

interface CacChartRow {
  channel: string;
  /** undefined (not 0) for channels with 0 converted customers — see
   * CacByChannelSection for why those are excluded rather than shown as
   * a misleading £0 bar. */
  cac?: number;
}

export function CacByChannelChart({ rows }: { rows: CacChartRow[] }) {
  return (
    <div className="atlas-cac-chart">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COLOR_BORDER} vertical={false} />
          <XAxis
            dataKey="channel"
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
          <Bar dataKey="cac" name="CAC" fill={COLOR_ACCENT} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

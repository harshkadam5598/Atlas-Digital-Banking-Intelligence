import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { RevenueForecastPoint, RevenueTrendPoint } from "../../api/hubs/revenue";
import { formatCurrency, formatCurrencyCompact } from "../../lib/formatters";
import "./RevenueForecastChart.css";

// Mirrors src/styles/tokens.css — see RevenueTrendChart.tsx for why these
// are literal hex rather than var(--atlas-*) references.
const COLOR_BORDER = "#e1e4ea";
const COLOR_INK_MUTED = "#5b6472";
const COLOR_ACCENT = "#1e3a8a";
const COLOR_CAUTION = "#92640a";
const COLOR_ACCENT_SOFT = "#eaeffb";

interface ChartRow {
  period: string;
  actual?: number;
  predicted?: number;
  band?: [number, number];
}

function buildChartData(
  historical: RevenueTrendPoint[],
  forecast: RevenueForecastPoint[],
): ChartRow[] {
  const historicalRows: ChartRow[] = historical.map((h) => ({
    period: h.period,
    actual: h.actual,
  }));
  const forecastRows: ChartRow[] = forecast.map((f) => ({
    period: f.period,
    predicted: f.predicted_value,
    band: [f.lower_bound, f.upper_bound],
  }));
  return [...historicalRows, ...forecastRows];
}

interface RevenueForecastChartProps {
  historical: RevenueTrendPoint[];
  forecast: RevenueForecastPoint[];
}

export function RevenueForecastChart({ historical, forecast }: RevenueForecastChartProps) {
  const data = buildChartData(historical, forecast);

  return (
    <div className="atlas-revenue-forecast-chart">
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area
            dataKey="band"
            name="Confidence range"
            stroke="none"
            fill={COLOR_ACCENT_SOFT}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="actual"
            name="Actual"
            stroke={COLOR_ACCENT}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            name="Forecast"
            stroke={COLOR_CAUTION}
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={{ r: 3 }}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { KpiSlot } from "../components/common/KpiSlot";
import { RevenueTrendSection } from "../components/revenue/RevenueTrendSection";
import { RevenueForecastSection } from "../components/revenue/RevenueForecastSection";
import { useRevenueSummary } from "../hooks/useRevenueSummary";
import { formatCurrency, formatSignedPercentPoints } from "../lib/formatters";
import "./RevenuePage.css";

const TREND_LABEL: Record<string, string> = { up: "Up", down: "Down", flat: "Flat" };

export function RevenuePage() {
  const { data, isLoading, error } = useRevenueSummary();

  // Same three-state pattern as ExecutivePage's KPI slots: loading, error,
  // or resolved (which may itself be a genuine backend null).
  const slot = (
    label: string,
    resolve: (summary: NonNullable<typeof data>) => string | null,
    unavailableCaption: string,
    okCaption: string,
  ) => {
    if (isLoading) {
      return { label, value: null, caption: "Loading…", tone: "default" as const };
    }
    if (error) {
      return { label, value: null, caption: "Unable to load", tone: "error" as const };
    }
    if (!data) {
      return { label, value: null, caption: "No data returned", tone: "error" as const };
    }
    const value = resolve(data);
    return {
      label,
      value,
      caption: value === null ? unavailableCaption : okCaption,
      tone: "default" as const,
    };
  };

  const kpiSlots = [
    slot(
      "Total Revenue",
      (d) => formatCurrency(d.value),
      "Not available",
      data?.period_label || `As of ${data?.as_of ?? ""}`,
    ),
    slot(
      "Change vs. Prior Period",
      (d) => (d.delta_pct === null ? null : formatSignedPercentPoints(d.delta_pct)),
      "No prior period available",
      "vs. prior period",
    ),
    slot(
      "Trend",
      (d) => (d.trend === null ? null : TREND_LABEL[d.trend]),
      "Not available",
      "vs. prior period",
    ),
  ];

  return (
    <div className="atlas-revenue-page">
      <PageHeader
        title="Revenue Intelligence"
        description="Revenue performance, trend, and forecast across Atlas."
      />

      <SectionCard
        title="Revenue Summary"
        description="Headline revenue figure for the current period, from /api/v1/revenue/summary."
      >
        <div className="atlas-revenue-page__kpi-grid">
          {kpiSlots.map((props) => (
            <KpiSlot key={props.label} {...props} />
          ))}
        </div>
        {data?.range_note && (
          <p className="atlas-revenue-page__note">{data.range_note}</p>
        )}
      </SectionCard>

      <SectionCard
        title="Revenue Trend"
        description="Monthly revenue history, from /api/v1/revenue/trend."
      >
        <RevenueTrendSection />
      </SectionCard>

      <SectionCard
        title="Revenue Forecast"
        description="3-month revenue forecast with confidence range, from /api/v1/revenue/forecast."
      >
        <RevenueForecastSection />
      </SectionCard>
    </div>
  );
}

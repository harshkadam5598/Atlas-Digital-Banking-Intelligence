import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { KpiSlot } from "../components/common/KpiSlot";
import { HealthScoreBreakdown } from "../components/executive/HealthScoreBreakdown";
import { NarrativePanel } from "../components/executive/NarrativePanel";
import { RiskAlertsPanel } from "../components/executive/RiskAlertsPanel";
import { useExecutiveKpis } from "../hooks/useExecutiveKpis";
import { formatPercent } from "./executiveFormatters";
import { formatCount, formatCurrency } from "../lib/formatters";
import "./ExecutivePage.css";

export function ExecutivePage() {
  const { data, isLoading, error } = useExecutiveKpis();

  // Every slot resolves through the same three states: loading, error,
  // or resolved (which itself may be a genuine backend null — never
  // coerced into 0 or a placeholder number).
  const slot = (
    label: string,
    resolve: (kpis: NonNullable<typeof data>) => string | null,
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
    slot("Monthly Active Users", (d) => formatCount(d.mau), "Not available", `As of ${data?.as_of_date ?? ""}`),
    slot(
      "MAU Growth",
      (d) => (d.mau_growth_mom === null ? null : formatPercent(d.mau_growth_mom)),
      "Not available this period",
      "Month over month",
    ),
    slot("Revenue", (d) => formatCurrency(d.revenue_mtd), "Not available", "Month to date"),
    slot(
      "Revenue Growth",
      (d) => formatPercent(d.revenue_growth_mom),
      "Not available",
      "Month over month",
    ),
    slot(
      "Premium Conversion",
      (d) => formatPercent(d.premium_conversion_rate),
      "Not available",
      "Current rate",
    ),
    slot(
      "Churn",
      (d) => formatPercent(d.churn_rate_monthly),
      "Not available",
      "Monthly",
    ),
  ];

  return (
    <div className="atlas-executive-page">
      <PageHeader
        title="Executive Command Center"
        description="Business health, risk, and opportunity across Atlas."
      />

      <SectionCard
        title="KPI Summary"
        description="Six top-line executive metrics from /api/v1/executive/kpis."
      >
        <div className="atlas-executive-page__kpi-grid">
          {kpiSlots.map((props) => (
            <KpiSlot key={props.label} {...props} />
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Main Analytics"
        description="Business health score components (composite score not yet available)."
      >
        <HealthScoreBreakdown />
      </SectionCard>

      <div className="atlas-executive-page__split">
        <SectionCard
          title="Narrative & Insights"
          description="Auto-generated executive summaries and observations."
        >
          <NarrativePanel />
        </SectionCard>

        <SectionCard
          title="Risk & Alerts"
          description="Active risk alerts, sorted by severity."
        >
          <RiskAlertsPanel />
        </SectionCard>
      </div>
    </div>
  );
}

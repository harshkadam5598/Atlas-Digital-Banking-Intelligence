import { useAllCustomerKpis } from "../../hooks/useAllCustomerKpis";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatCount, formatSignedPercentPoints } from "../../lib/formatters";
import "./ActivitySection.css";

const ACTIVITY_KEYS = [
  { key: "daily_active_users", label: "Daily Active Users" },
  { key: "weekly_active_users", label: "Weekly Active Users" },
  { key: "monthly_active_users", label: "Monthly Active Users" },
] as const;

export function ActivitySection() {
  const { data, isLoading, error } = useAllCustomerKpis();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading activity metrics…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load activity metrics from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No activity data was returned." />;
  }

  return (
    <div className="atlas-activity-grid">
      {ACTIVITY_KEYS.map(({ key, label }) => {
        const kpi = data.kpis[key];
        if (!kpi) {
          // Would only happen if the registry ever drops one of these
          // names — an honest gap, not a value to guess at.
          return (
            <KpiSlot key={key} label={label} value={null} caption="Not available" />
          );
        }
        let caption: string;
        if (kpi.delta_pct !== null) {
          caption = `${formatSignedPercentPoints(kpi.delta_pct)} vs. prior period`;
        } else if (kpi.delta !== null) {
          // delta_pct is null specifically when the prior period's value
          // was 0 (percentage undefined), not because there's no prior
          // period — delta itself is still real, so show that instead.
          const sign = kpi.delta > 0 ? "+" : "";
          caption = `${sign}${formatCount(kpi.delta)} vs. prior period`;
        } else {
          caption = "No prior period";
        }
        return (
          <KpiSlot key={key} label={label} value={formatCount(kpi.value)} caption={caption} />
        );
      })}
    </div>
  );
}

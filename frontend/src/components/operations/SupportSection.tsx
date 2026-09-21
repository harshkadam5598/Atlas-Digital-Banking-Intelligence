import { useSupport } from "../../hooks/useSupport";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { OperationsHoursChart } from "./OperationsHoursChart";
import { formatCount, formatHours, formatScoreOutOfFive } from "../../lib/formatters";
import "./OperationsSectionShared.css";

export function SupportSection() {
  const { data, isLoading, error } = useSupport();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading support data…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load support data from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No support data was returned." />;
  }

  const { support_resolution_time, csat } = data;
  const byPriority = support_resolution_time.breakdown.by_priority;
  const rows = byPriority
    ? Object.entries(byPriority).map(([category, value]) => ({ category, value }))
    : [];
  const targets = support_resolution_time.metadata.targets;
  const byTier = csat.breakdown.by_tier;

  return (
    <div>
      <div className="atlas-operations-two-col">
        <div>
          <KpiSlot
            label="Support Resolution Time"
            value={formatHours(support_resolution_time.value)}
            caption={`Average · ${support_resolution_time.period_label}`}
          />
          {targets && (
            <p className="atlas-operations-target">
              Targets: {Object.entries(targets).map(([tier, hrs]) => `${tier} < ${formatHours(hrs)}`).join(", ")}
              {support_resolution_time.metadata.resolved_tickets !== undefined &&
                ` · ${formatCount(support_resolution_time.metadata.resolved_tickets)} resolved tickets`}
            </p>
          )}
        </div>
        <div>
          <KpiSlot
            label="CSAT"
            value={formatScoreOutOfFive(csat.value)}
            caption={`${csat.metadata.scale ?? "1–5"} scale · ${csat.period_label}`}
          />
          {byTier && (
            <p className="atlas-operations-target">
              Premium: {formatScoreOutOfFive(byTier.premium)} · Free: {formatScoreOutOfFive(byTier.free)}
              {csat.metadata.rated_tickets !== undefined &&
                ` · ${formatCount(csat.metadata.rated_tickets)} rated tickets`}
            </p>
          )}
        </div>
      </div>

      {rows.length > 0 && (
        <>
          <h3 className="atlas-operations-anomalies-heading">Resolution Time by Priority</h3>
          <OperationsHoursChart rows={rows} seriesName="Resolution time" />
        </>
      )}
    </div>
  );
}

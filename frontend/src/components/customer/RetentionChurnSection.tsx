import { useRetention } from "../../hooks/useRetention";
import { useChurn } from "../../hooks/useChurn";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatCount, formatPercentPoints } from "../../lib/formatters";
import "./RetentionChurnSection.css";

function RetentionPanel() {
  const { data, isLoading, error } = useRetention();

  if (isLoading) return <StructuralPlaceholder message="Loading retention…" />;
  if (error) return <StructuralPlaceholder message="Unable to load retention from the API." />;
  if (!data) return <StructuralPlaceholder message="No retention data was returned." />;

  const { cohort_size, retained_count, cohort_month, period_months } = data.metadata;

  return (
    <div className="atlas-retention-panel">
      <KpiSlot
        label="Cohort Retention"
        value={formatPercentPoints(data.value)}
        caption={period_months ? `${data.period_label} (M+${period_months})` : data.period_label}
      />
      {cohort_size !== undefined && (
        <dl className="atlas-retention-panel__detail">
          <div>
            <dt>Cohort</dt>
            <dd>{cohort_month ?? "—"}</dd>
          </div>
          <div>
            <dt>Cohort size</dt>
            <dd>{formatCount(cohort_size)}</dd>
          </div>
          {retained_count !== undefined && (
            <div>
              <dt>Still active</dt>
              <dd>{formatCount(retained_count)}</dd>
            </div>
          )}
        </dl>
      )}
    </div>
  );
}

function ChurnPanel() {
  const { data, isLoading, error } = useChurn();

  if (isLoading) return <StructuralPlaceholder message="Loading churn…" />;
  if (error) return <StructuralPlaceholder message="Unable to load churn from the API." />;
  if (!data) return <StructuralPlaceholder message="No churn data was returned." />;

  const { churned_count, prior_active_base } = data.metadata;

  return (
    <div className="atlas-retention-panel">
      <KpiSlot label="Monthly Churn Rate" value={formatPercentPoints(data.value)} caption={data.period_label} />
      {prior_active_base !== undefined && (
        <dl className="atlas-retention-panel__detail">
          <div>
            <dt>Prior-month active base</dt>
            <dd>{formatCount(prior_active_base)}</dd>
          </div>
          {churned_count !== undefined && (
            <div>
              <dt>Churned</dt>
              <dd>{formatCount(churned_count)}</dd>
            </div>
          )}
        </dl>
      )}
    </div>
  );
}

export function RetentionChurnSection() {
  return (
    <div className="atlas-retention-churn-section">
      <RetentionPanel />
      <ChurnPanel />
    </div>
  );
}

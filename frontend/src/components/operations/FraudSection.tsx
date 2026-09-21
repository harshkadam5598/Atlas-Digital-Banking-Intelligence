import { useFraud } from "../../hooks/useFraud";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { AnomalyCard } from "../common/AnomalyCard";
import { formatCount, formatPercentPoints, formatPercentPointsPrecise } from "../../lib/formatters";
import "./OperationsSectionShared.css";

export function FraudSection() {
  const { data, isLoading, error } = useFraud();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading fraud data…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load fraud data from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No fraud data was returned." />;
  }

  const { fraud_rate, anomalies } = data;
  const m = fraud_rate.metadata;

  return (
    <div>
      <KpiSlot
        label="Fraud Rate"
        value={formatPercentPointsPrecise(fraud_rate.value)}
        caption={`Of completed transactions · ${fraud_rate.period_label}`}
      />
      {m.flagged_count !== undefined && (
        <p className="atlas-operations-target">
          {formatCount(m.flagged_count)} flagged · {formatCount(m.cleared_count ?? 0)} cleared
          {m.clear_ratio_pct !== undefined &&
            ` (${formatPercentPoints(m.clear_ratio_pct)} clear rate)`}
          {m.chargeback_count !== undefined && ` · ${formatCount(m.chargeback_count)} chargebacks`}
        </p>
      )}

      {anomalies.length > 0 && (
        <>
          <h3 className="atlas-operations-anomalies-heading">Fraud Anomalies</h3>
          {anomalies.map((a, i) => (
            <AnomalyCard key={`${a.metric}-${a.detected_at}-${i}`} anomaly={a} />
          ))}
        </>
      )}
    </div>
  );
}

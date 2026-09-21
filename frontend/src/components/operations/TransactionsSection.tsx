import { useTransactions } from "../../hooks/useTransactions";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { AnomalyCard } from "../common/AnomalyCard";
import { OperationsPercentChart } from "./OperationsPercentChart";
import { formatCount, formatPercentPoints } from "../../lib/formatters";
import "./OperationsSectionShared.css";

export function TransactionsSection() {
  const { data, isLoading, error } = useTransactions();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading transaction data…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load transaction data from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No transaction data was returned." />;
  }

  const { failed_transaction_rate, anomalies } = data;
  const byProduct = failed_transaction_rate.breakdown.by_product;
  const rows = byProduct
    ? Object.entries(byProduct).map(([category, value]) => ({ category, value }))
    : [];
  const m = failed_transaction_rate.metadata;

  return (
    <div>
      <KpiSlot
        label="Failed Transaction Rate"
        value={formatPercentPoints(failed_transaction_rate.value)}
        caption={failed_transaction_rate.period_label}
      />
      {m.alert_threshold !== undefined && (
        <p className="atlas-operations-target">
          Alert threshold: &gt; {formatPercentPoints(m.alert_threshold)}
          {m.failed_count !== undefined &&
            ` · ${formatCount(m.failed_count)} of ${formatCount(m.total_transactions ?? 0)} transactions failed`}
        </p>
      )}

      {rows.length > 0 && (
        <>
          <h3 className="atlas-operations-anomalies-heading">Failure Rate by Product</h3>
          <OperationsPercentChart rows={rows} seriesName="Failure rate" />
        </>
      )}

      {anomalies.length > 0 && (
        <>
          <h3 className="atlas-operations-anomalies-heading">Transaction Anomalies</h3>
          {anomalies.map((a, i) => (
            <AnomalyCard key={`${a.metric}-${a.detected_at}-${i}`} anomaly={a} />
          ))}
        </>
      )}
    </div>
  );
}

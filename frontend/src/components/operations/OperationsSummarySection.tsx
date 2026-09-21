import { useOperationsSummary } from "../../hooks/useOperationsSummary";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatHours, formatPercentPoints, formatPercentPointsPrecise, formatScoreOutOfFive } from "../../lib/formatters";
import "./OperationsSummarySection.css";

export function OperationsSummarySection() {
  const { data, isLoading, error } = useOperationsSummary();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading operations summary…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the operations summary from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No operations summary data was returned." />;
  }

  return (
    <div className="atlas-operations-summary-grid">
      <KpiSlot
        label="KYC Approval Rate"
        value={formatPercentPoints(data.kyc_approval_rate)}
        caption="This month"
      />
      <KpiSlot
        label="Fraud Rate"
        value={formatPercentPointsPrecise(data.fraud_rate)}
        caption="Of completed transactions"
      />
      <KpiSlot
        label="Support Resolution"
        value={formatHours(data.support_resolution_time)}
        caption="Average, all tickets"
      />
      <KpiSlot
        label="CSAT"
        value={formatScoreOutOfFive(data.csat)}
        caption="1–5 scale"
      />
      <KpiSlot
        label="Failed Transaction Rate"
        value={formatPercentPoints(data.failed_transaction_rate)}
        caption="This month"
      />
    </div>
  );
}

import { useKyc } from "../../hooks/useKyc";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { AnomalyCard } from "../common/AnomalyCard";
import { OperationsPercentChart } from "./OperationsPercentChart";
import { formatHours, formatPercentPoints } from "../../lib/formatters";
import "./OperationsSectionShared.css";

export function KycSection() {
  const { data, isLoading, error } = useKyc();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading KYC data…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load KYC data from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No KYC data was returned." />;
  }

  const { kyc_approval_rate, kyc_processing_time, anomalies } = data;
  const byCountry = kyc_approval_rate.breakdown.by_country;
  const rows = byCountry
    ? Object.entries(byCountry).map(([category, value]) => ({ category, value }))
    : [];

  return (
    <div>
      <div className="atlas-operations-two-col">
        <div>
          <KpiSlot
            label="KYC Approval Rate"
            value={formatPercentPoints(kyc_approval_rate.value)}
            caption={kyc_approval_rate.period_label}
          />
          {kyc_approval_rate.metadata.target !== undefined && (
            <p className="atlas-operations-target">
              Target: ≥ {formatPercentPoints(kyc_approval_rate.metadata.target)}
              {kyc_approval_rate.metadata.total_submissions !== undefined &&
                ` · ${kyc_approval_rate.metadata.approved ?? 0} of ${kyc_approval_rate.metadata.total_submissions} submissions approved`}
            </p>
          )}
        </div>
        <div>
          <KpiSlot
            label="KYC Processing Time"
            value={formatHours(kyc_processing_time.value)}
            caption={`Median · ${kyc_processing_time.period_label}`}
          />
          {kyc_processing_time.metadata.target_hours !== undefined && (
            <p className="atlas-operations-target">
              Target: &lt; {formatHours(kyc_processing_time.metadata.target_hours)}
              {kyc_processing_time.metadata.mean_hours !== undefined &&
                ` · mean ${formatHours(kyc_processing_time.metadata.mean_hours)}`}
            </p>
          )}
        </div>
      </div>

      {rows.length > 0 && (
        <>
          <h3 className="atlas-operations-anomalies-heading">Approval Rate by Country</h3>
          <OperationsPercentChart rows={rows} seriesName="Approval rate" />
        </>
      )}

      {anomalies.length > 0 && (
        <>
          <h3 className="atlas-operations-anomalies-heading">Delay Anomalies</h3>
          {anomalies.map((a, i) => (
            <AnomalyCard key={`${a.metric}-${a.detected_at}-${i}`} anomaly={a} />
          ))}
        </>
      )}
    </div>
  );
}

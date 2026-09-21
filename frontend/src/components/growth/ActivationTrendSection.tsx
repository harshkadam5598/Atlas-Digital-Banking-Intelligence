import { useActivationTrend } from "../../hooks/useActivationTrend";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { ActivationTrendChart } from "./ActivationTrendChart";
import { formatPercentPoints } from "../../lib/formatters";
import "./ActivationTrendSection.css";

export function ActivationTrendSection() {
  const { data, isLoading, error } = useActivationTrend();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading activation trend…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the activation trend from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No activation trend data was returned." />;
  }

  if (data.series.length === 0) {
    return <StructuralPlaceholder message="No activation data is available for this range." />;
  }

  const latest = data.series[data.series.length - 1];

  return (
    <div className="atlas-activation-section">
      <div className="atlas-activation-section__headline">
        <KpiSlot
          label="Activation Rate (Latest Month)"
          value={formatPercentPoints(latest.activation_rate)}
          caption={`Within 30 days · ${latest.period}`}
        />
      </div>
      <ActivationTrendChart series={data.series} />
      <p className="atlas-activation-section__note">
        Activation = first transaction within 30 days of registration, {data.series.length}-month
        trailing view.
      </p>
    </div>
  );
}

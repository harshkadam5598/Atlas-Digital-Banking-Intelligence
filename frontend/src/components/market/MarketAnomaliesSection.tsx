import { useMarketAnomalies } from "../../hooks/useMarketAnomalies";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { AnomalyCard } from "../common/AnomalyCard";
import "./MarketSectionShared.css";

export function MarketAnomaliesSection() {
  const { data, isLoading, error } = useMarketAnomalies();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading market anomalies…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load market anomalies from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No anomaly data was returned." />;
  }

  if (data.anomalies.length === 0) {
    return <p className="atlas-market-note">No country-level revenue anomalies detected.</p>;
  }

  return (
    <div>
      {data.anomalies.map((a, i) => (
        <AnomalyCard key={`${a.metric}-${a.detected_at}-${i}`} anomaly={a} />
      ))}
    </div>
  );
}

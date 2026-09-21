import { useRevenueForecast } from "../../hooks/useRevenueForecast";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { RevenueForecastChart } from "./RevenueForecastChart";
import "./RevenueForecastSection.css";

export function RevenueForecastSection() {
  const { data, isLoading, error } = useRevenueForecast();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading revenue forecast…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the revenue forecast from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No revenue forecast data was returned." />;
  }

  if (data.historical.length === 0 && data.forecast.length === 0) {
    return <StructuralPlaceholder message="No historical or forecast revenue data is available." />;
  }

  return (
    <div className="atlas-revenue-forecast-section">
      <RevenueForecastChart historical={data.historical} forecast={data.forecast} />
      <p className="atlas-revenue-forecast-section__note">{data.accuracy_note}</p>
      <p className="atlas-revenue-forecast-section__note">{data.horizon_note}</p>
    </div>
  );
}

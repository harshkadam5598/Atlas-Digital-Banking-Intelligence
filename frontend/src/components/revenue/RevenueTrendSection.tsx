import { useRevenueTrend } from "../../hooks/useRevenueTrend";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { RevenueTrendChart } from "./RevenueTrendChart";
import "./RevenueTrendSection.css";

export function RevenueTrendSection() {
  const { data, isLoading, error } = useRevenueTrend();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading revenue trend…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the revenue trend from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No revenue trend data was returned." />;
  }

  if (data.series.length === 0) {
    // Genuinely empty is possible and documented — e.g. a non-monthly
    // granularity has no backing series. Show the backend's own reason
    // rather than an unexplained blank chart.
    const reason = data.unavailable_fields?.series;
    return (
      <StructuralPlaceholder
        message={reason ?? "No revenue history is available for this granularity."}
      />
    );
  }

  return (
    <div className="atlas-revenue-trend-section">
      <RevenueTrendChart series={data.series} />
      <p className="atlas-revenue-trend-section__caption">
        Granularity: {data.granularity} — monthly is the only granularity
        with a backing series in the current analytics engine.
      </p>
    </div>
  );
}

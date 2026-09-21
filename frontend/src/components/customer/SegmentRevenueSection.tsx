import { useCustomerSegments } from "../../hooks/useCustomerSegments";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { SegmentRevenueChart } from "./SegmentRevenueChart";
import { formatCurrency } from "../../lib/formatters";
import "./SegmentRevenueSection.css";

export function SegmentRevenueSection() {
  const { data, isLoading, error } = useCustomerSegments();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading revenue by segment…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load revenue by segment from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No segment data was returned." />;
  }

  const bySegment = data.breakdown.by_segment;

  if (!bySegment || Object.keys(bySegment).length === 0) {
    return <StructuralPlaceholder message="No revenue was recorded by segment for this period." />;
  }

  const rows = Object.entries(bySegment).map(([segment, revenue]) => ({ segment, revenue }));

  return (
    <div className="atlas-segment-section">
      {/* The backend is explicit this is a revenue breakdown, not a
          customer-count/composition breakdown — no such KPI exists.
          Surfacing this ahead of the chart so it can't be misread. */}
      <p className="atlas-segment-section__gap-note">{data.gap_note}</p>
      <p className="atlas-segment-section__caption">
        Total: {formatCurrency(data.value)} · {data.period_label}
      </p>
      <SegmentRevenueChart rows={rows} />
    </div>
  );
}

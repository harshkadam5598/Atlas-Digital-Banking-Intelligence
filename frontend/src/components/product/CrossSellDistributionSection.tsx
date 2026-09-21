import { useCrossSellRate } from "../../hooks/useCrossSellRate";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { CrossSellDistributionChart } from "./CrossSellDistributionChart";
import { formatCount, formatPercentPoints } from "../../lib/formatters";
import "./ProductSectionNote.css";

export function CrossSellDistributionSection() {
  const { data, isLoading, error } = useCrossSellRate();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading cross-sell distribution…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load cross-sell distribution from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No cross-sell data was returned." />;
  }

  const distribution = data.breakdown.product_count_distribution;

  if (!distribution || Object.keys(distribution).length === 0) {
    return <StructuralPlaceholder message="No active customers were recorded for this period." />;
  }

  const rows = Object.entries(distribution)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([productCount, customers]) => ({ productCount, customers }));

  return (
    <div>
      <CrossSellDistributionChart rows={rows} />
      <p className="atlas-product-section-note">
        Cross-sell rate: {formatPercentPoints(data.value)}
        {data.metadata.active_base !== undefined &&
          ` (${formatCount(data.metadata.multi_product_count ?? 0)} of ${formatCount(data.metadata.active_base)} active customers hold ≥2 products)`}
      </p>
    </div>
  );
}

import { useProductSummary } from "../../hooks/useProductSummary";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatPercentPoints, formatRatioValue } from "../../lib/formatters";
import "./ProductSummarySection.css";

export function ProductSummarySection() {
  const { data, isLoading, error } = useProductSummary();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading product summary…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the product summary from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No product summary data was returned." />;
  }

  return (
    <div className="atlas-product-summary-grid">
      <KpiSlot
        label="Product Adoption"
        value={formatPercentPoints(data.product_adoption)}
        caption="Of active customers"
      />
      <KpiSlot
        label="Product Stickiness"
        value={formatRatioValue(data.product_stickiness)}
        caption="DAU / MAU, blended"
      />
      <KpiSlot
        label="Cross-Sell Rate"
        value={formatPercentPoints(data.cross_sell_rate)}
        caption="Holding ≥2 products"
      />
    </div>
  );
}

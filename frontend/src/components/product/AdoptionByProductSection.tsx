import { useProductAdoption } from "../../hooks/useProductAdoption";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { AdoptionByProductChart } from "./AdoptionByProductChart";
import { formatCount, formatPercentPoints } from "../../lib/formatters";
import "./ProductSectionNote.css";

export function AdoptionByProductSection() {
  const { data, isLoading, error } = useProductAdoption();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading adoption by product…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load adoption by product from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No adoption data was returned." />;
  }

  const byProduct = data.breakdown.by_product;

  if (!byProduct || Object.keys(byProduct).length === 0) {
    return <StructuralPlaceholder message="No product events were recorded for this period." />;
  }

  const rows = Object.entries(byProduct).map(([product, value]) => ({ product, value }));

  return (
    <div>
      <AdoptionByProductChart rows={rows} />
      <p className="atlas-product-section-note">
        Overall: {formatPercentPoints(data.value)} of active customers
        {data.metadata.active_customer_base !== undefined &&
          ` (base: ${formatCount(data.metadata.active_customer_base)})`}
      </p>
    </div>
  );
}

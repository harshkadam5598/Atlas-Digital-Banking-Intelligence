import { useProductStickiness } from "../../hooks/useProductStickiness";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { StickinessByProductChart } from "./StickinessByProductChart";
import { formatRatioValue } from "../../lib/formatters";
import "./ProductSectionNote.css";

export function StickinessByProductSection() {
  const { data, isLoading, error } = useProductStickiness();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading stickiness by product…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load stickiness by product from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No stickiness data was returned." />;
  }

  const byProduct = data.breakdown.by_product;

  if (!byProduct || Object.keys(byProduct).length === 0) {
    return <StructuralPlaceholder message="No product events were recorded for this period." />;
  }

  const rows = Object.entries(byProduct).map(([product, value]) => ({ product, value }));

  return (
    <div>
      <StickinessByProductChart rows={rows} />
      <p className="atlas-product-section-note">
        Blended: {formatRatioValue(data.value)}
        {data.metadata.benchmark && ` · ${data.metadata.benchmark}`}
      </p>
    </div>
  );
}

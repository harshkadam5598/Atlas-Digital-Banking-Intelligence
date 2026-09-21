import { useFeatureAdoption } from "../../hooks/useFeatureAdoption";
import { KpiSlot } from "../common/KpiSlot";
import { formatPercentPoints } from "../../lib/formatters";
import "./FeatureAdoptionSection.css";

// Real fact_product_events.event_type values — see
// etl/extractors/product_event_generator.py's event_map. Not guessed:
// these are the actual event types the data generator emits.
const FEATURES = [
  { eventType: "premium_purchased", label: "Premium" },
  { eventType: "crypto_activated", label: "Crypto" },
  { eventType: "investment_opened", label: "Investment" },
  { eventType: "fx_activated", label: "FX" },
];

function FeatureSlot({ eventType, label }: { eventType: string; label: string }) {
  const { data, isLoading, error } = useFeatureAdoption(eventType);

  if (isLoading) {
    return <KpiSlot label={label} value={null} caption="Loading…" />;
  }
  if (error) {
    return <KpiSlot label={label} value={null} caption="Unable to load" tone="error" />;
  }
  if (!data) {
    return <KpiSlot label={label} value={null} caption="No data returned" tone="error" />;
  }
  return (
    <KpiSlot
      label={label}
      value={formatPercentPoints(data.value)}
      caption="Of eligible customers"
    />
  );
}

export function FeatureAdoptionSection() {
  return (
    <div>
      <div className="atlas-feature-adoption-grid">
        {FEATURES.map((f) => (
          <FeatureSlot key={f.eventType} {...f} />
        ))}
      </div>
      <p className="atlas-product-section-note atlas-product-section-note--muted">
        Feature penetration rate = % of activated/reactivated/churned customers who
        have ever triggered the given product event.
      </p>
    </div>
  );
}

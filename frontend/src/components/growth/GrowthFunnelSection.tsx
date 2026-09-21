import { useFunnel } from "../../hooks/useFunnel";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { GrowthFunnelChart } from "./GrowthFunnelChart";
import { FunnelConversionRates } from "./FunnelConversionRates";
import { formatPercentPoints } from "../../lib/formatters";
import "./GrowthFunnelSection.css";

export function GrowthFunnelSection() {
  const { data, isLoading, error } = useFunnel();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading funnel data…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the funnel from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No funnel data was returned." />;
  }

  const { stage_counts, stage_conversion_rates } = data.breakdown;

  // funnel_conversion() returns an empty breakdown when there's no
  // dim_customer data or no registrations in the period — that's a real,
  // honest empty state (see metadata.note), not an error.
  if (!stage_counts) {
    return (
      <StructuralPlaceholder
        message={data.metadata.note ?? "No registrations were recorded for this period."}
      />
    );
  }

  return (
    <div className="atlas-growth-funnel-section">
      <div className="atlas-growth-funnel-section__headline">
        <KpiSlot
          label="Overall Conversion"
          value={formatPercentPoints(data.value)}
          caption={`Registration → First Transaction · ${data.period_label}`}
        />
      </div>
      <GrowthFunnelChart stageCounts={stage_counts} />
      {stage_conversion_rates && (
        <FunnelConversionRates rates={stage_conversion_rates} />
      )}
      {data.metadata.note && (
        <p className="atlas-growth-funnel-section__note">{data.metadata.note}</p>
      )}
    </div>
  );
}

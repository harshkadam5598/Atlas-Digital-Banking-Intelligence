import { useCacByChannel } from "../../hooks/useCacByChannel";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { CacByChannelChart } from "./CacByChannelChart";
import { formatCurrency } from "../../lib/formatters";
import "./CacByChannelSection.css";

export function CacByChannelSection() {
  const { data, isLoading, error } = useCacByChannel();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading CAC by channel…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load CAC by channel from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No CAC data was returned." />;
  }

  const { by_channel, converted_by_channel } = data.breakdown;

  if (!by_channel || Object.keys(by_channel).length === 0) {
    return (
      <StructuralPlaceholder
        message={data.metadata.note ?? "No marketing spend was recorded for this period."}
      />
    );
  }

  // A channel with 0 converted customers gets CAC 0.0 by safe-division
  // default in the backend — that's "not computable," not "free," per
  // the backend's own note. Derived from the real converted_by_channel
  // counts rather than parsed out of the free-text note.
  const notComputableChannels = Object.keys(by_channel).filter(
    (channel) => !converted_by_channel?.[channel],
  );

  const rows = Object.entries(by_channel).map(([channel, cac]) => ({
    channel,
    cac: notComputableChannels.includes(channel) ? undefined : cac,
  }));

  return (
    <div className="atlas-cac-section">
      <div className="atlas-cac-section__headline">
        <KpiSlot
          label="Blended CAC"
          value={formatCurrency(data.value)}
          caption={data.period_label}
        />
      </div>
      <CacByChannelChart rows={rows} />
      {notComputableChannels.length > 0 && (
        <p className="atlas-cac-section__note">
          Not computable this period (0 converted customers): {notComputableChannels.join(", ")}
        </p>
      )}
      {data.metadata.converted_definition && (
        <p className="atlas-cac-section__note">{data.metadata.converted_definition}</p>
      )}
    </div>
  );
}

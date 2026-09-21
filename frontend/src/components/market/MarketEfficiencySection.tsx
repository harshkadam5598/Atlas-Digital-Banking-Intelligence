import { useMarketEfficiency } from "../../hooks/useMarketEfficiency";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatRatio } from "../../lib/formatters";
import "./MarketSectionShared.css";

export function MarketEfficiencySection() {
  const { data, isLoading, error } = useMarketEfficiency();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading market efficiency…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load market efficiency from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No market efficiency data was returned." />;
  }

  // Same underlying ltv_cac_ratio() function as Customer's /value
  // endpoint: 0 converted customers means "not computable," not "zero."
  const notComputable = data.metadata.converted_customers === 0;

  return (
    <div>
      <KpiSlot
        label="Market Efficiency (proxy)"
        value={notComputable ? null : formatRatio(data.value)}
        caption={notComputable ? "Not computable — 0 converted customers" : data.period_label}
      />
      {data.metadata.benchmark && (
        <p className="atlas-market-note">{data.metadata.benchmark}</p>
      )}
      <p className="atlas-market-note">{data.proxy_note}</p>
    </div>
  );
}

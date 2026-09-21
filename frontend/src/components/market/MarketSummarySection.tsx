import { useMarketSummary } from "../../hooks/useMarketSummary";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatCurrency, formatRatio } from "../../lib/formatters";
import "./MarketSectionShared.css";

export function MarketSummarySection() {
  const { data, isLoading, error } = useMarketSummary();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading market summary…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the market summary from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No market summary data was returned." />;
  }

  const topCountries = Object.entries(data.top_countries_by_revenue).sort(
    ([, a], [, b]) => b - a,
  );

  return (
    <div>
      <div className="atlas-market-summary-grid">
        <KpiSlot
          label="Total Revenue"
          value={formatCurrency(data.total_revenue)}
          caption={data.as_of_date}
        />
        <KpiSlot
          label="LTV / CAC (proxy)"
          value={formatRatio(data.ltv_cac_ratio)}
          caption="Acquisition-efficiency proxy"
        />
      </div>
      {topCountries.length > 0 && (
        <dl className="atlas-market-country-list">
          {topCountries.map(([country, revenue]) => (
            <div key={country}>
              <dt>{country}</dt>
              <dd>{formatCurrency(revenue)}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="atlas-market-note">{data.efficiency_note}</p>
    </div>
  );
}

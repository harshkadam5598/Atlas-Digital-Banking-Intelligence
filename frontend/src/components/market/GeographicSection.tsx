import { useGeographic } from "../../hooks/useGeographic";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { GeographicRevenueChart } from "./GeographicRevenueChart";
import { CountryDetailTable } from "./CountryDetailTable";
import "./MarketSectionShared.css";

export function GeographicSection() {
  const { data, isLoading, error } = useGeographic();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading geographic data…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load geographic data from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No geographic data was returned." />;
  }

  const countries = Object.keys(data.revenue_by_country);

  if (countries.length === 0) {
    return <StructuralPlaceholder message="No revenue was recorded by country for this period." />;
  }

  const chartRows = countries
    .map((country) => ({ country, revenue: data.revenue_by_country[country] }))
    .sort((a, b) => b.revenue - a.revenue);

  // Union of every country appearing in either breakdown — matches the
  // backend's own union logic, so a country with a growth rate but no
  // revenue this period (or vice versa) isn't silently dropped.
  const allCountries = Array.from(
    new Set([...countries, ...Object.keys(data.country_customer_growth_rate_mom)]),
  ).sort();

  const tableRows = allCountries.map((country) => ({
    country,
    contributionPct: data.geographic_revenue_contribution_pct[country] ?? 0,
    growthMom: data.country_customer_growth_rate_mom[country] ?? null,
  }));

  return (
    <div>
      <GeographicRevenueChart rows={chartRows} />
      <h3 className="atlas-market-anomalies-heading">Contribution &amp; Growth by Country</h3>
      <CountryDetailTable rows={tableRows} />
      <p className="atlas-market-note">{data.note}</p>
    </div>
  );
}

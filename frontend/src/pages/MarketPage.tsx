import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { MarketSummarySection } from "../components/market/MarketSummarySection";
import { GeographicSection } from "../components/market/GeographicSection";
import { MarketEfficiencySection } from "../components/market/MarketEfficiencySection";
import { MarketAnomaliesSection } from "../components/market/MarketAnomaliesSection";

/**
 * Structure mirrors the four real Market endpoints in market_service.py.
 * No "Market Opportunity" or "Market Size" capability exists in the
 * backend — those Master Spec terms are not simulated here. Market
 * Efficiency is explicitly a proxy (ltv_cac_ratio), not an officially
 * defined KPI, per the backend's own documented caveat.
 */
export function MarketPage() {
  return (
    <div className="atlas-market-page">
      <PageHeader
        title="Market Intelligence"
        description="Geographic revenue, country-level growth, and acquisition-efficiency proxy."
      />

      <SectionCard title="Market Summary" description="From /api/v1/market/summary.">
        <MarketSummarySection />
      </SectionCard>

      <SectionCard
        title="Geographic Revenue & Growth"
        description="Revenue by country and country-level customer growth, from /api/v1/market/geographic."
      >
        <GeographicSection />
      </SectionCard>

      <SectionCard
        title="Market Efficiency (Proxy)"
        description="LTV/CAC exposed as the closest acquisition-efficiency proxy — not an officially defined Market Efficiency KPI. From /api/v1/market/efficiency."
      >
        <MarketEfficiencySection />
      </SectionCard>

      <SectionCard
        title="Market Anomalies"
        description="Country-level revenue anomalies, from /api/v1/market/anomalies."
      >
        <MarketAnomaliesSection />
      </SectionCard>
    </div>
  );
}

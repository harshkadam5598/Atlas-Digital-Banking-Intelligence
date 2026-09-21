import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { GrowthFunnelSection } from "../components/growth/GrowthFunnelSection";
import { CacByChannelSection } from "../components/growth/CacByChannelSection";
import { ActivationTrendSection } from "../components/growth/ActivationTrendSection";

/**
 * Structure mirrors the three approved Growth capabilities exactly (see
 * analytics/kpis/growth_kpis.py's module docstring) — no Visitor stage,
 * no metrics beyond funnel_conversion / cac_by_channel / activation_rate.
 */
export function GrowthPage() {
  return (
    <div className="atlas-growth-page">
      <PageHeader
        title="Growth Intelligence"
        description="Registration-to-transaction funnel, acquisition cost by channel, and activation trend."
      />

      <SectionCard
        title="Growth Funnel"
        description="Registration → first-transaction conversion, from /api/v1/growth/funnel. Visitor and pre-registration stages are not tracked in the current warehouse."
      >
        <GrowthFunnelSection />
      </SectionCard>

      <SectionCard
        title="CAC by Channel"
        description="Customer acquisition cost by marketing channel, from /api/v1/growth/cac-by-channel."
      >
        <CacByChannelSection />
      </SectionCard>

      <SectionCard
        title="Activation Trend"
        description="30-day activation rate, trailing 6 months, from /api/v1/growth/activation-trend."
      >
        <ActivationTrendSection />
      </SectionCard>
    </div>
  );
}

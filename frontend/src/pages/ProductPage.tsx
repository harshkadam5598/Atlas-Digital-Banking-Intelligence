import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { ProductSummarySection } from "../components/product/ProductSummarySection";
import { AdoptionByProductSection } from "../components/product/AdoptionByProductSection";
import { StickinessByProductSection } from "../components/product/StickinessByProductSection";
import { CrossSellDistributionSection } from "../components/product/CrossSellDistributionSection";
import { FeatureAdoptionSection } from "../components/product/FeatureAdoptionSection";

/**
 * Structure mirrors the 4 real Product KPIs in analytics/kpis/product_kpis.py:
 * product_adoption, product_stickiness, cross_sell_rate, feature_adoption.
 * No Master Spec capability beyond these four is simulated.
 */
export function ProductPage() {
  return (
    <div className="atlas-product-page">
      <PageHeader
        title="Product Intelligence"
        description="Product adoption, stickiness, cross-sell, and feature-level adoption."
      />

      <SectionCard
        title="Product Summary"
        description="From /api/v1/product/summary."
      >
        <ProductSummarySection />
      </SectionCard>

      <SectionCard
        title="Adoption by Product"
        description="Share of active customers who have used each product, from /api/v1/product/adoption."
      >
        <AdoptionByProductSection />
      </SectionCard>

      <SectionCard
        title="Stickiness by Product"
        description="Daily/Monthly active ratio per product, from /api/v1/product/stickiness."
      >
        <StickinessByProductSection />
      </SectionCard>

      <SectionCard
        title="Cross-Sell Distribution"
        description="Active customers by number of distinct products held, from /api/v1/product/cross-sell."
      >
        <CrossSellDistributionSection />
      </SectionCard>

      <SectionCard
        title="Feature Adoption"
        description="Adoption rate for specific product features, from /api/v1/product/feature-adoption."
      >
        <FeatureAdoptionSection />
      </SectionCard>
    </div>
  );
}

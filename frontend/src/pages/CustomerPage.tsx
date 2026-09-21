import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { CustomerSummarySection } from "../components/customer/CustomerSummarySection";
import { ActivitySection } from "../components/customer/ActivitySection";
import { CustomerValueSection } from "../components/customer/CustomerValueSection";
import { RetentionChurnSection } from "../components/customer/RetentionChurnSection";
import { SegmentRevenueSection } from "../components/customer/SegmentRevenueSection";

/**
 * Structure mirrors the real Customer Intelligence capabilities in
 * customer_service.py: summary (6 KPIs), the 3 activity KPIs the
 * summary omits (DAU/WAU/MAU, from the bulk /kpis endpoint), per-
 * customer value economics (ARPU/CLV/LTV-CAC, cross-domain but
 * genuinely customer metrics), retention + churn detail, and revenue
 * by segment (explicitly not a customer-count breakdown — no such KPI
 * exists in the Sprint 5 engine).
 */
export function CustomerPage() {
  return (
    <div className="atlas-customer-page">
      <PageHeader
        title="Customer Intelligence"
        description="Customer base health, activity, value economics, and retention."
      />

      <SectionCard
        title="Customer Summary"
        description="From /api/v1/customer/summary."
      >
        <CustomerSummarySection />
      </SectionCard>

      <SectionCard
        title="Activity"
        description="Daily / weekly / monthly active users, from /api/v1/customer/kpis."
      >
        <ActivitySection />
      </SectionCard>

      <SectionCard
        title="Customer Value"
        description="ARPU, CLV, and LTV/CAC ratio, from /api/v1/customer/value."
      >
        <CustomerValueSection />
      </SectionCard>

      <SectionCard
        title="Retention & Churn"
        description="Cohort retention and monthly churn, from /api/v1/customer/retention and /api/v1/customer/churn."
      >
        <RetentionChurnSection />
      </SectionCard>

      <SectionCard
        title="Revenue by Segment"
        description="Net revenue grouped by customer segment, from /api/v1/customer/segments."
      >
        <SegmentRevenueSection />
      </SectionCard>
    </div>
  );
}

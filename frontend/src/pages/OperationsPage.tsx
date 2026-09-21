import { PageHeader } from "../components/shell/PageHeader";
import { SectionCard } from "../components/common/SectionCard";
import { OperationsSummarySection } from "../components/operations/OperationsSummarySection";
import { KycSection } from "../components/operations/KycSection";
import { FraudSection } from "../components/operations/FraudSection";
import { SupportSection } from "../components/operations/SupportSection";
import { TransactionsSection } from "../components/operations/TransactionsSection";

/**
 * Structure mirrors the real Operations endpoint grouping in
 * operations_service.py exactly: summary, then the four domain
 * groupings (KYC, Fraud, Support, Transactions), each composing its
 * own KPIs plus anomaly_engine.py detections where the backend
 * provides them.
 */
export function OperationsPage() {
  return (
    <div className="atlas-operations-page">
      <PageHeader
        title="Operations Intelligence"
        description="KYC, fraud, support, and transaction health across the platform."
      />

      <SectionCard title="Operations Summary" description="From /api/v1/operations/summary.">
        <OperationsSummarySection />
      </SectionCard>

      <SectionCard
        title="KYC"
        description="Approval rate and processing time, from /api/v1/operations/kyc."
      >
        <KycSection />
      </SectionCard>

      <SectionCard
        title="Fraud"
        description="Fraud rate and detected anomalies, from /api/v1/operations/fraud."
      >
        <FraudSection />
      </SectionCard>

      <SectionCard
        title="Support"
        description="Resolution time and CSAT, from /api/v1/operations/support."
      >
        <SupportSection />
      </SectionCard>

      <SectionCard
        title="Transactions"
        description="Failed transaction rate and detected anomalies, from /api/v1/operations/transactions."
      >
        <TransactionsSection />
      </SectionCard>
    </div>
  );
}

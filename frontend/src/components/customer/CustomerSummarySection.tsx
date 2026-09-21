import { useCustomerSummary } from "../../hooks/useCustomerSummary";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatCount, formatPercentPoints } from "../../lib/formatters";
import "./CustomerSummarySection.css";

export function CustomerSummarySection() {
  const { data, isLoading, error } = useCustomerSummary();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading customer summary…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load the customer summary from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No customer summary data was returned." />;
  }

  const slots = [
    { label: "Active Customers", value: formatCount(data.active_customers), caption: "Point-in-time" },
    { label: "New Customers", value: formatCount(data.new_customers), caption: "This month" },
    { label: "Returning Customers", value: formatCount(data.returning_customers), caption: "This month" },
    { label: "Churn Rate", value: formatPercentPoints(data.churn_rate), caption: "Monthly" },
    { label: "Retention Rate", value: formatPercentPoints(data.retention_rate), caption: "Cohort, M+1" },
    {
      label: "Premium Conversion",
      value: formatPercentPoints(data.premium_conversion_rate),
      caption: "Of activated customers",
    },
  ];

  return (
    <div className="atlas-customer-summary-grid">
      {slots.map((slot) => (
        <KpiSlot key={slot.label} {...slot} />
      ))}
    </div>
  );
}

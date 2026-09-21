import { useCustomerValue } from "../../hooks/useCustomerValue";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { KpiSlot } from "../common/KpiSlot";
import { formatCurrency, formatRatio } from "../../lib/formatters";
import "./CustomerValueSection.css";

export function CustomerValueSection() {
  const { data, isLoading, error } = useCustomerValue();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading customer value metrics…" />;
  }

  if (error) {
    return <StructuralPlaceholder message="Unable to load customer value metrics from the API." />;
  }

  if (!data) {
    return <StructuralPlaceholder message="No customer value data was returned." />;
  }

  // ltv_cac_ratio.value is 0.0 both when the ratio is genuinely zero and
  // when it's not computable (no converted customers this month, so CAC
  // itself is undefined) — the backend distinguishes these via
  // converted_customers, so use that rather than showing a bare "0.0x"
  // that could be misread as a real, alarming ratio.
  const convertedCustomers = data.ltv_cac_ratio.metadata.converted_customers;
  const ltvCacComputable = !!convertedCustomers;

  return (
    <div className="atlas-customer-value-section">
      <div className="atlas-customer-value-section__grid">
        <KpiSlot label="ARPU" value={formatCurrency(data.arpu.value)} caption="Monthly, per active user" />
        <KpiSlot label="CLV" value={formatCurrency(data.clv.value)} caption="Estimated lifetime value" />
        <KpiSlot
          label="LTV / CAC Ratio"
          value={ltvCacComputable ? formatRatio(data.ltv_cac_ratio.value) : null}
          caption={
            ltvCacComputable
              ? (data.ltv_cac_ratio.metadata.benchmark ?? "This month")
              : "Not computable — no converted customers this month"
          }
        />
      </div>
      <p className="atlas-customer-value-section__note">{data.note}</p>
    </div>
  );
}

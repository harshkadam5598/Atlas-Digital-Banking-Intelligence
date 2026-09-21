import { formatPercentPointsPrecise, formatSignedPercentPointsPrecise } from "../../lib/formatters";
import "./CountryDetailTable.css";

interface CountryRow {
  country: string;
  contributionPct: number;
  growthMom: number | null;
}

export function CountryDetailTable({ rows }: { rows: CountryRow[] }) {
  return (
    <div className="atlas-country-table">
      <div className="atlas-country-table__header">
        <span>Country</span>
        <span>Revenue Contribution</span>
        <span>Customer Growth (MoM)</span>
      </div>
      {rows.map((row) => (
        <div className="atlas-country-table__row" key={row.country}>
          <span>{row.country}</span>
          <span>{formatPercentPointsPrecise(row.contributionPct)}</span>
          {row.growthMom === null ? (
            <span className="atlas-country-table__unavailable">No prior-month base</span>
          ) : (
            <span
              className={
                row.growthMom < 0
                  ? "atlas-country-table__growth atlas-country-table__growth--negative"
                  : "atlas-country-table__growth atlas-country-table__growth--positive"
              }
            >
              {formatSignedPercentPointsPrecise(row.growthMom)}
              {row.growthMom === -100 && " (fell to zero)"}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

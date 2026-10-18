import Link from "next/link";
import type { CompanySearchResult } from "../lib/api";

export default function CompanyCard({ company }: { company: CompanySearchResult }) {
  return (
    <Link className="company-card-link" href={`/company/${company.id}`}>
      <article className="company-card">
        <h2 className="company-name">{company.name}</h2>
        <dl className="company-identifiers">
          {company.ticker && (
            <div>
              <dt>Ticker</dt>
              <dd>{company.ticker}</dd>
            </div>
          )}
          {company.cik && (
            <div>
              <dt>CIK</dt>
              <dd>{company.cik}</dd>
            </div>
          )}
        </dl>
      </article>
    </Link>
  );
}

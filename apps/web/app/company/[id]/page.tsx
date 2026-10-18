"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  getCompany,
  getCompanyFacts,
  isApiError,
  type CompanyDetail,
  type CompanyFact
} from "../../../lib/api";
import { formatValue } from "../../../lib/format";

type LoadState = "idle" | "loading" | "ready" | "not-found" | "error";


export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const companyId = params.id;
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [facts, setFacts] = useState<CompanyFact[]>([]);

  useEffect(() => {
    let isActive = true;

    async function loadData() {
      setState("loading");
      setError(null);
      try {
        const detail = await getCompany(companyId);
        if (!isActive) {
          return;
        }

        setCompany(detail);

        const detailFacts = await getCompanyFacts(companyId);
        if (!isActive) {
          return;
        }

        setFacts(detailFacts);
        setState("ready");
      } catch (loadError) {
        if (!isActive) {
          return;
        }

        if (isApiError(loadError) && loadError.status === 404) {
          setState("not-found");
          return;
        }

        setState("error");
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Company data could not be loaded."
        );
      }
    }

    void loadData();

    return () => {
      isActive = false;
    };
  }, [companyId]);

  const factsByYear = useMemo(() => {
    const grouped = new Map<string, CompanyFact[]>();

    for (const fact of facts) {
      const yearLabel = fact.fiscal_year === null ? "Unknown fiscal year" : String(fact.fiscal_year);
      const bucket = grouped.get(yearLabel);
      if (bucket) {
        bucket.push(fact);
      } else {
        grouped.set(yearLabel, [fact]);
      }
    }

    return Array.from(grouped.entries())
      .sort(([left], [right]) => {
        const leftValue = Number(left);
        const rightValue = Number(right);
        if (Number.isNaN(leftValue)) {
          return 1;
        }
        if (Number.isNaN(rightValue)) {
          return -1;
        }
        return rightValue - leftValue;
      })
      .map(([year, yearFacts]) => ({
        year,
        facts: yearFacts.slice().sort((a, b) => {
          if (a.metric_key === b.metric_key) {
            const byPeriod = (b.period_end ?? "").localeCompare(a.period_end ?? "");
            return byPeriod !== 0
              ? byPeriod
              : (a.accession_number ?? "").localeCompare(b.accession_number ?? "");
          }
          return a.metric_key.localeCompare(b.metric_key);
        })
      }));
  }, [facts]);

  return (
    <main className="page-shell">
      <p className="eyebrow">Company detail</p>
      <h1>Company facts</h1>
      <p className="intro">
        Data is loaded directly from the backend SEC-ingested records.
      </p>
      <p className="detail-back-link">
        <Link href="/">← Back to search</Link>
      </p>

      {state === "loading" && <p className="status-message" role="status">Loading company data…</p>}

      {state === "not-found" && (
        <p className="status-message error-message" role="alert">
          Company not found for ID {companyId}.
        </p>
      )}

      {state === "error" && (
        <p className="status-message error-message" role="alert">
          {error ?? "Company data could not be loaded."}
        </p>
      )}

      {state === "ready" && company && (
        <>
          <section className="company-card detail-company-header" aria-label="Company overview">
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
            {company.cik === "0000320193" && (
              <p className="detail-back-link">
                <Link href={`/valuation/${company.id}`}>View reviewed valuation summary →</Link>
              </p>
            )}
          </section>

          <section className="facts-section" aria-label="Financial facts">
            <h2 className="facts-title">Financial facts ({facts.length})</h2>
            {factsByYear.map((group) => (
              <section key={group.year} className="facts-year-group">
                <h3 className="facts-year-heading">Fiscal year: {group.year}</h3>
                <p className="facts-note">
                  Fiscal year is the filing&apos;s fiscal year. A filing also reports prior-period
                  comparatives, so one metric can appear with several period end dates (newest first).
                </p>
                <div className="facts-table-wrap">
                  <table className="facts-table">
                    <thead>
                      <tr>
                        <th scope="col">Metric key</th>
                        <th scope="col">Period end</th>
                        <th scope="col">Value</th>
                        <th scope="col">Unit</th>
                        <th scope="col">Fiscal year</th>
                        <th scope="col">Accession number</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.facts.map((fact, index) => (
                        <tr key={`${group.year}-${fact.metric_key}-${fact.accession_number ?? "none"}-${index}`}>
                          <td>{fact.metric_key}</td>
                          <td className="facts-period">{fact.period_end ?? "Unknown"}</td>
                          <td className="facts-value" title={`Raw value: ${fact.value}`}>
                            {formatValue(fact.value)}
                          </td>
                          <td>{fact.unit}</td>
                          <td>{fact.fiscal_year ?? "Unknown"}</td>
                          <td>{fact.accession_number ?? "Unknown"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))}
          </section>
        </>
      )}
    </main>
  );
}

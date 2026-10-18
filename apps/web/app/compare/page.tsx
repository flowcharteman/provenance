"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import {
  getCompanyFacts,
  searchCompanies,
  type CompanyFact,
  type CompanySearchResult
} from "../../lib/api";
import { formatValue } from "../../lib/format";

// Metric keys exactly as they exist in the facts response; there is no "ebit" key.
const METRICS = [
  { key: "revenue", label: "Revenue" },
  { key: "operating_income", label: "Operating income (closest to EBIT)" },
  { key: "net_income", label: "Net income" },
  { key: "depreciation_depletion_and_amortization", label: "Depreciation, depletion & amortization" }
] as const;

type Column =
  | { ticker: string; status: "ok"; company: CompanySearchResult; facts: CompanyFact[] }
  | { ticker: string; status: "not-found" }
  | { ticker: string; status: "error"; message: string };

function latestFact(facts: CompanyFact[], metricKey: string): CompanyFact | null {
  let best: CompanyFact | null = null;
  for (const fact of facts) {
    if (fact.metric_key !== metricKey || fact.period_end === null) {
      continue;
    }
    if (best === null || fact.period_end > (best.period_end as string)) {
      best = fact;
    }
  }
  return best;
}

async function loadColumn(ticker: string): Promise<Column> {
  try {
    const results = await searchCompanies(ticker);
    const company = results.find((item) => item.ticker?.toUpperCase() === ticker);
    if (!company) {
      return { ticker, status: "not-found" };
    }
    const facts = await getCompanyFacts(company.id);
    return { ticker, status: "ok", company, facts };
  } catch (err) {
    return {
      ticker,
      status: "error",
      message: err instanceof Error ? err.message : "Lookup failed."
    };
  }
}

export default function ComparePage() {
  const [input, setInput] = useState("");
  const [columns, setColumns] = useState<Column[]>([]);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const tickers = Array.from(
      new Set(
        input
          .split(",")
          .map((part) => part.trim().toUpperCase())
          .filter(Boolean)
      )
    );
    if (tickers.length === 0) {
      return;
    }
    setLoading(true);
    setColumns(await Promise.all(tickers.map(loadColumn)));
    setLoading(false);
  }

  const available = columns.filter((column) => column.status === "ok");
  const unavailable = columns.filter((column) => column.status !== "ok");

  return (
    <main className="page-shell">
      <p className="eyebrow">Compare</p>
      <h1>Compare companies</h1>
      <p className="intro">
        Enter tickers separated by commas. Each value is the most recent annual period on record.
      </p>
      <p className="detail-back-link">
        <Link href="/">← Back to search</Link>
      </p>

      <form className="search-form" onSubmit={onSubmit}>
        <input
          className="search-input"
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="AAPL, GOOGL, AMZN"
          aria-label="Tickers, comma-separated"
        />
        <button className="search-button" type="submit" disabled={loading || !input.trim()}>
          {loading ? "Loading…" : "Compare"}
        </button>
      </form>

      {unavailable.map((column) => (
        <p key={column.ticker} className="status-message error-message" role="alert">
          {column.status === "not-found"
            ? `${column.ticker}: not available. This company has not been ingested yet.`
            : `${column.ticker}: ${column.status === "error" ? column.message : ""}`}
        </p>
      ))}

      {available.length > 0 && (
        <p className="compare-banner" role="note">
          <strong>Different reporting periods.</strong> These companies have different fiscal
          year-ends. Each figure is the company&apos;s most recent reported annual period, not the
          same calendar period, so the columns are not directly like-for-like.
        </p>
      )}

      {available.length > 0 && (
        <div className="facts-table-wrap">
          <table className="facts-table compare-table">
            <thead>
              <tr>
                <th scope="col">Metric</th>
                {available.map((column) =>
                  column.status === "ok" ? (
                    <th key={column.ticker} scope="col">
                      <Link href={`/company/${column.company.id}`}>{column.company.name}</Link>
                      <div className="compare-ticker">{column.ticker}</div>
                    </th>
                  ) : null
                )}
              </tr>
            </thead>
            <tbody>
              {METRICS.map((metric) => (
                <tr key={metric.key}>
                  <th scope="row">{metric.label}</th>
                  {available.map((column) => {
                    if (column.status !== "ok") {
                      return null;
                    }
                    const fact = latestFact(column.facts, metric.key);
                    return (
                      <td
                        key={column.ticker}
                        className="facts-value"
                        title={fact ? `Raw value: ${fact.value}; accession ${fact.accession_number}` : undefined}
                      >
                        {fact ? (
                          <>
                            {formatValue(fact.value)} {fact.unit}
                            <div className="compare-period">period end {fact.period_end}</div>
                          </>
                        ) : (
                          "Not available"
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

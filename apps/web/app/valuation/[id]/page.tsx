"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getCompany, isApiError, type CompanyDetail } from "../../../lib/api";

const APPLE_CIK = "0000320193";
const SOURCE = "docs/reports/valuation/README.md and apple-day3-day4-model.xlsx";

const FOOTBALL_FIELD = [
  { method: "DCF sensitivity", low: "88.53", high: "124.33", lowDiff: "-73.41%", highDiff: "-62.65%" },
  { method: "Comps: EV/EBITDA (Apple, Microsoft*, Alphabet)", low: "193.81", high: "323.77", lowDiff: "-41.78%", highDiff: "-2.74%" },
  { method: "Comps: EV/Revenue (Apple, Microsoft*, Alphabet)", low: "285.43", high: "324.63", lowDiff: "-14.26%", highDiff: "-2.48%" },
  { method: "Comps: Microsoft P/E (point estimate)", low: "219.32", high: "219.32", lowDiff: "-34.12%", highDiff: "-34.12%" },
  { method: "LBO ability-to-pay (point estimate)", low: "128.19", high: "128.19", lowDiff: "-61.49%", highDiff: "-61.49%" }
];

const SENSITIVITY = [
  { wacc: "9.51%", values: ["$111.63", "$117.53", "$124.33"] },
  { wacc: "10.51%", values: ["$98.72", "$103.11", "$108.09"] },
  { wacc: "11.51%", values: ["$88.53", "$91.90", "$95.67"] }
];

const DCF_ASSUMPTIONS: [string, string][] = [
  ["Risk-free rate", "5.27% (10-year US Treasury yield, Oct. 6, 2026; supplied external market input)"],
  ["Equity risk premium", "5.00% (supplied practitioner assumption; judgment call, not a sourced quote)"],
  ["Beta", "1.07 (five-year monthly levered equity beta; supplied external market input)"],
  ["Cost of equity", "10.62% (5.27% + 1.07 × 5.00%, arithmetic from the inputs above)"],
  ["Pretax cost of debt", "6.02% (risk-free rate + 0.75 pt spread; spread is a judgment call for review)"],
  ["Forward tax rate", "15.1646% (mean of FY2023 and FY2025 effective rates; FY2024's 24.0912% excluded for a one-time EU State Aid charge)"],
  ["Revenue growth, years 1–5", "4.5%, 4.0%, 3.5%, 3.0%, 2.5% (proposed, informed by historical growth)"],
  ["EBIT margin", "31.5% (proposed, informed by FY2023–FY2025)"],
  ["D&A / revenue", "2.9% (proposed, informed by FY2023–FY2025)"],
  ["Capex / revenue", "2.8% (proposed, informed by FY2023–FY2025)"],
  ["NWC / revenue", "-12.51% (FY2025 operating NWC / revenue held constant; proposed)"],
  ["Terminal growth", "2.5% nominal (judgment call, not a sourced forecast); sensitivity 2.00%–3.00%"],
  ["Discounting", "Annual year-end cash flows at t=1 through t=5 (simplifying convention)"],
  ["Market capitalization", "$4,858bn (supplied external input, Oct. 5, 2026; used for WACC weights)"]
];

const SEC_FACTS: [string, string][] = [
  ["Revenue", "$416.161bn"],
  ["EBIT", "$133.050bn"],
  ["Net income", "$112.010bn"],
  ["Combined D&A", "$11.698bn"],
  ["Capex", "$12.715bn"],
  ["Current debt", "$12.350bn"],
  ["Commercial paper", "$7.979bn"],
  ["Noncurrent long-term debt", "$78.328bn"],
  ["Cash", "$35.934bn"],
  ["Current marketable securities", "$18.763bn"],
  ["Noncurrent marketable securities", "$77.723bn"],
  ["Diluted weighted-average shares", "15.004697bn"]
];

const PEERS: { company: string; status: string; included: boolean }[] = [
  { company: "Apple", status: "Complete identified EV inputs (database-ingested).", included: true },
  { company: "Microsoft", status: "Re-included by a stated assumption: FY2026 commercial paper is missing, so it is assumed $0.000bn based on the FY2025 value (June 30, 2025, accession 0000950170-25-100235). This is an assumption, not an FY2026 fact (capture-only).", included: true },
  { company: "Alphabet", status: "Complete identified EV inputs; commercial paper reported as zero (database-ingested).", included: true },
  { company: "Amazon", status: "Commercial-paper fact missing, with no adjacent same-tag value (database-ingested but excluded).", included: false },
  { company: "Meta", status: "Current debt and commercial-paper facts missing, with no adjacent same-tag values (capture-only).", included: false },
  { company: "NVIDIA", status: "FY2026 current marketable securities missing; the FY2025 same-tag value of $34.621bn (Jan. 26, 2025, accession 0001045810-25-000023) is not low, so it is not carried forward (capture-only).", included: false },
  { company: "Tesla", status: "Commercial-paper fact missing, with no adjacent same-tag value (capture-only).", included: false }
];

const LBO_ASSUMPTIONS: [string, string][] = [
  ["Entry EV / EBITDA", "20.0x (proposed, informed by the trading-comp range)"],
  ["Exit EV / EBITDA", "19.0x (proposed one-turn de-rating from entry)"],
  ["Hold period", "5 years; no interim sponsor distributions"],
  ["Term Loan B", "3.5x EBITDA at risk-free + 2.50% = 7.77%; seven-year maturity, 1% annual amortization"],
  ["Senior notes", "1.5x EBITDA at risk-free + 3.25% = 8.52%; ten-year maturity, no scheduled amortization"],
  ["Total opening debt", "5.0x EBITDA"],
  ["Cash sweep", "100% of cash after interest, cash taxes and scheduled amortization repays TLB first, then notes"],
  ["Transaction fees", "1.0% of entry EV"],
  ["Interest", "On beginning-of-year balances; no minimum cash, refinancing or maturity payment modeled"],
  ["Ability-to-pay target", "20% five-year IRR (specified by the user)"]
];

export default function ValuationPage() {
  const params = useParams<{ id: string }>();
  const companyId = params.id;
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "not-found" | "unsupported" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    getCompany(companyId)
      .then((result) => {
        if (cancelled) return;
        setCompany(result);
        setState(result.cik === APPLE_CIK ? "ready" : "unsupported");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState(isApiError(err) && err.status === 404 ? "not-found" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  return (
    <main className="page-shell">
      <p className="eyebrow">Valuation</p>
      <h1>Apple valuation summary</h1>
      <p className="detail-back-link">
        <Link href={`/company/${companyId}`}>← Back to company</Link>
      </p>

      {state === "loading" && <p className="status-message" role="status">Loading…</p>}
      {state === "not-found" && (
        <p className="status-message error-message" role="alert">Company not found for ID {companyId}.</p>
      )}
      {state === "error" && (
        <p className="status-message error-message" role="alert">Company data could not be loaded.</p>
      )}
      {state === "unsupported" && (
        <p className="status-message error-message" role="alert">
          A reviewed valuation is only available for Apple (CIK {APPLE_CIK}).
          {company ? ` ${company.name} has none.` : ""}
        </p>
      )}

      {state === "ready" && (
        <>
          <p className="compare-banner" role="note">
            <strong>Pre-computed, reviewed results — not a live recalculation.</strong> Everything on this
            page is static content from {SOURCE}. Nothing is recalculated here. These are illustrative
            outputs, not a finalized valuation or investment recommendation.
          </p>

          <section className="valuation-section">
            <h2 className="facts-title">Football field</h2>
            <p className="valuation-note">
              Apple market price: <strong>$332.89</strong> per share (supplied external input, Oct. 5, 2026;
              not an SEC fact). Point estimates have equal low and high.
            </p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              className="valuation-chart"
              src="/valuation/football-field.svg"
              alt="Football field chart of implied share prices by method against the $332.89 market price"
            />
            <div className="facts-table-wrap">
              <table className="facts-table">
                <thead>
                  <tr>
                    <th scope="col">Method</th>
                    <th scope="col">Low ($/share)</th>
                    <th scope="col">High ($/share)</th>
                    <th scope="col">vs. $332.89 at low</th>
                    <th scope="col">vs. $332.89 at high</th>
                  </tr>
                </thead>
                <tbody>
                  {FOOTBALL_FIELD.map((row) => (
                    <tr key={row.method}>
                      <td>{row.method}</td>
                      <td className="facts-value">{row.low}</td>
                      <td className="facts-value">{row.high}</td>
                      <td className="facts-value">{row.lowDiff}</td>
                      <td className="facts-value">{row.highDiff}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="valuation-note">
              *Microsoft is re-included using a stated zero assumption for FY2026 commercial paper; it is not
              a strict-completeness pass.
            </p>
          </section>

          <section className="valuation-section">
            <h2 className="facts-title">DCF</h2>
            <p className="valuation-note">
              Sensitivity range: <strong>$88.53–$124.33</strong> per share. Center case (WACC 10.51%,
              terminal growth 2.50%): <strong>$103.11</strong>. Five-year UFCF, Gordon-growth terminal value,
              net-cash equity bridge, 15.004697bn diluted shares.
            </p>
            <div className="facts-table-wrap">
              <table className="facts-table">
                <thead>
                  <tr>
                    <th scope="col">WACC \ Terminal growth</th>
                    <th scope="col">2.00%</th>
                    <th scope="col">2.50%</th>
                    <th scope="col">3.00%</th>
                  </tr>
                </thead>
                <tbody>
                  {SENSITIVITY.map((row) => (
                    <tr key={row.wacc}>
                      <th scope="row">{row.wacc}</th>
                      {row.values.map((value, index) => (
                        <td key={index} className="facts-value">{value}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3 className="facts-year-heading">Assumptions (not SEC facts)</h3>
            <div className="facts-table-wrap">
              <table className="facts-table">
                <tbody>
                  {DCF_ASSUMPTIONS.map(([label, text]) => (
                    <tr key={label}>
                      <th scope="row">{label}</th>
                      <td>{text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3 className="facts-year-heading">Traced SEC facts (FY2025, accession 0000320193-25-000079)</h3>
            <div className="facts-table-wrap">
              <table className="facts-table">
                <tbody>
                  {SEC_FACTS.map(([label, text]) => (
                    <tr key={label}>
                      <th scope="row">{label}</th>
                      <td className="facts-value">{text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="valuation-note">
              Derived: debt $98.657bn, cash and investments $132.420bn, net debt -$33.763bn (net cash).
            </p>
          </section>

          <section className="valuation-section">
            <h2 className="facts-title">Trading comps</h2>
            <ul className="valuation-list">
              <li>
                <strong>EV/EBITDA:</strong> $193.81–$323.77 per share. Peer multiples applied to Apple FY2025
                EBITDA of $144.748bn (EBIT plus combined D&amp;A), bridged with Apple&apos;s net cash and
                divided by 15.004697bn shares. Microsoft contributes the low endpoint.
              </li>
              <li>
                <strong>EV/Revenue:</strong> $285.43–$324.63 per share. Applied to Apple FY2025 revenue of
                $416.161bn with the same bridge. Microsoft contributes the high endpoint.
              </li>
              <li>
                <strong>Microsoft P/E (equity multiple, not EV):</strong> 29.38x × Apple net income of
                $112.010bn = $3,290.854bn implied equity, ÷ 15.004697bn shares = $219.32 per share.
              </li>
            </ul>
            <div className="facts-table-wrap">
              <table className="facts-table">
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Football field</th>
                    <th scope="col">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {PEERS.map((peer) => (
                    <tr key={peer.company}>
                      <td>{peer.company}</td>
                      <td>{peer.included ? "Included" : "Excluded"}</td>
                      <td>{peer.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="valuation-note">
              EBITDA constructions differ by issuer and are not perfectly comparable. Market inputs (dated
              Oct. 5–8, 2026) are compared with FY2025/FY2026 balance sheets, a timing mismatch.
            </p>
          </section>

          <section className="valuation-section">
            <h2 className="facts-title">LBO (illustrative mechanics only)</h2>
            <p className="valuation-note">
              This is an illustrative LBO mechanics exercise on Apple&apos;s real financials, not a realistic
              deal thesis. A company this large would not be a practical leveraged-buyout target.
            </p>
            <div className="facts-table-wrap">
              <table className="facts-table">
                <tbody>
                  <tr>
                    <th scope="row">Entry case IRR (20.0x entry, 19.0x exit)</th>
                    <td>about 6.03%</td>
                  </tr>
                  <tr>
                    <th scope="row">Entry case MOIC</th>
                    <td>
                      about 1.34x (derived: 1.0603^5 from the stated IRR with no interim distributions; the
                      README does not state MOIC)
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Entry case sponsor equity</th>
                    <td>about $2.200 trillion (an unrealistic single-sponsor requirement)</td>
                  </tr>
                  <tr>
                    <th scope="row">Ability-to-pay target</th>
                    <td>20% five-year IRR</td>
                  </tr>
                  <tr>
                    <th scope="row">Maximum entry EV</th>
                    <td>$1,889.696bn</td>
                  </tr>
                  <tr>
                    <th scope="row">Maximum entry multiple</th>
                    <td>13.06x EBITDA</td>
                  </tr>
                  <tr>
                    <th scope="row">Implied share price at maximum entry</th>
                    <td>$128.19 = ($1,889.696bn − (−$33.763bn)) ÷ 15.004697bn shares</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <h3 className="facts-year-heading">Entry, exit and financing assumptions (not SEC facts)</h3>
            <div className="facts-table-wrap">
              <table className="facts-table">
                <tbody>
                  {LBO_ASSUMPTIONS.map(([label, text]) => (
                    <tr key={label}>
                      <th scope="row">{label}</th>
                      <td>{text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <p className="valuation-note">Source: {SOURCE}.</p>
        </>
      )}
    </main>
  );
}

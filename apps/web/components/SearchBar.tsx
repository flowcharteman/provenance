"use client";

import { useState, type FormEvent } from "react";
import { searchCompanies, type CompanySearchResult } from "../lib/api";
import CompanyCard from "./CompanyCard";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CompanySearchResult[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const ticker = query.trim();
    if (!ticker || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResults(null);
    try {
      setResults(await searchCompanies(ticker));
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : "Company search failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section aria-label="Company ticker search">
      <form className="search-form" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="ticker-search">
          Ticker symbol
        </label>
        <input
          className="search-input"
          id="ticker-search"
          autoComplete="off"
          placeholder="Enter a ticker, e.g. AAPL"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="search-button" type="submit" disabled={isLoading || !query.trim()}>
          {isLoading ? "Searching…" : "Search"}
        </button>
      </form>

      {isLoading && <p className="status-message" role="status">Searching companies…</p>}
      {error && <p className="status-message error-message" role="alert">{error}</p>}
      {results !== null && !isLoading && !error && (
        results.length > 0 ? (
          <div className="results" aria-live="polite">
            {results.map((company) => <CompanyCard key={company.id} company={company} />)}
          </div>
        ) : (
          <p className="status-message" role="status">
            No companies found for “{query.trim()}”. Check the ticker and try again.
          </p>
        )
      )}
    </section>
  );
}

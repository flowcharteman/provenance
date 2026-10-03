# SEC response fixtures

These excerpts preserve the JSON shape and selected records from official SEC
EDGAR endpoints. They are for deterministic offline parser tests only; they are
not seeded into PostgreSQL or treated as current company data.

- `company_tickers.json`: `https://www.sec.gov/files/company_tickers.json`
- `submissions.json`: `https://data.sec.gov/submissions/CIK0000320193.json`
- `companyfacts_excerpt.json`:
  `https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json`

The company-facts excerpt retains the SEC-reported US-GAAP records for Apple's
FY2023 revenue and year-end assets. The test suite reads the values from this
fixture rather than embedding separate financial values in test logic.

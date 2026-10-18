export interface CompanySearchResult {
  id: string;
  name: string;
  ticker: string | null;
  cik: string | null;
}

export interface CompanyDetail {
  id: string;
  name: string;
  ticker: string | null;
  cik: string | null;
}

export interface CompanyFact {
  metric_key: string;
  value: string;
  unit: string;
  fiscal_year: number | null;
  accession_number: string | null;
  period_end: string | null;
}

interface CompanySearchResponse {
  items: CompanySearchResult[];
}

interface CompanyFactsResponse {
  facts: CompanyFact[];
}

class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
  .replace(/\/+$/, "");

async function parseResponse<T>(response: Response, errorPrefix: string): Promise<T> {
  if (!response.ok) {
    throw new ApiError(response.status, `${errorPrefix} (${response.status}).`);
  }
  return (await response.json()) as T;
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

export async function searchCompanies(query: string): Promise<CompanySearchResult[]> {
  const params = new URLSearchParams({ q: query });
  const response = await fetch(`${apiBaseUrl}/api/companies/search?${params}`);
  const data = await parseResponse<CompanySearchResponse>(
    response,
    "Company search failed. Please try again"
  );
  return data.items;
}

export async function getCompany(id: string): Promise<CompanyDetail> {
  const response = await fetch(`${apiBaseUrl}/api/companies/${id}`);
  return parseResponse<CompanyDetail>(response, "Company lookup failed");
}

export async function getCompanyFacts(id: string): Promise<CompanyFact[]> {
  const response = await fetch(`${apiBaseUrl}/api/companies/${id}/facts`);
  const data = await parseResponse<CompanyFactsResponse>(response, "Fact lookup failed");
  return data.facts;
}

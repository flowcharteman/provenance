export interface CompanySearchResult {
  id: string;
  name: string;
  ticker: string | null;
  cik: string | null;
}

interface CompanySearchResponse {
  items: CompanySearchResult[];
}

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000")
  .replace(/\/+$/, "");

export async function searchCompanies(query: string): Promise<CompanySearchResult[]> {
  const params = new URLSearchParams({ q: query });
  const response = await fetch(`${apiBaseUrl}/api/companies/search?${params}`);

  if (!response.ok) {
    throw new Error(`Company search failed (${response.status}). Please try again.`);
  }

  const data = (await response.json()) as CompanySearchResponse;
  return data.items;
}

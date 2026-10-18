import Link from "next/link";
import SearchBar from "../components/SearchBar";

export default function HomePage() {
  return (
    <main className="page-shell">
      <p className="eyebrow">Company research</p>
      <h1>Find a company</h1>
      <p className="intro">
        Search by ticker to find companies with sourced SEC filing data.
      </p>
      <p className="detail-back-link">
        <Link href="/compare">Compare companies →</Link>
      </p>
      <SearchBar />
    </main>
  );
}

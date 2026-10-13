from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings
from app.db.sec_repository import SecPostgresRepository


app = FastAPI(
    title="ValuationLab API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    settings = Settings.from_env()
    app.state.settings = settings
    app.state.repo = await SecPostgresRepository.connect(settings.database_url)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    repo = getattr(app.state, "repo", None)
    if repo is not None:
        await repo.close()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/companies/search")
async def search_companies(
    q: str = Query(..., description="Ticker symbol, e.g. AAPL"),
) -> dict[str, Any]:
    repo: SecPostgresRepository = app.state.repo

    ticker = q.strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    company = await repo.find_company_by_ticker(ticker)
    if company is None:
        return {"items": []}

    return {
        "items": [{
            "id": str(company["id"]),
            "name": company.get("name") or company.get("display_name"),
            "ticker": company.get("ticker"),
            "cik": company.get("cik"),
            "sector": company.get("sector"),
            "industry": company.get("industry"),
        }]
    }


@app.get("/api/companies/{company_id}")
async def get_company(company_id: UUID) -> dict[str, Any]:
    repo: SecPostgresRepository = app.state.repo

    company = await repo.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "id": str(company["id"]),
        "name": company.get("name"),
        "ticker": company.get("ticker"),
        "cik": company.get("cik"),
        "sector": company.get("sector"),
        "industry": company.get("industry"),
    }


@app.get("/api/companies/{company_id}/facts")
async def get_company_facts(company_id: UUID) -> dict[str, Any]:
    repo: SecPostgresRepository = app.state.repo
    facts = await repo.get_financial_facts(company_id)
    return {"facts": facts}
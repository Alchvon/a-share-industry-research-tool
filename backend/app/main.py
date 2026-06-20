from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, company, data_source, health, industry, knowledge, llm, stock, valuation
from app.db import init_db


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(
        title="A股产业链龙头分析器 API",
        version="0.1.0",
        description="MVP backend for industry-chain stock research.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(analysis.router)
    app.include_router(company.router)
    app.include_router(data_source.router)
    app.include_router(industry.router)
    app.include_router(knowledge.router)
    app.include_router(llm.router)
    app.include_router(stock.router)
    app.include_router(valuation.router)

    return app


app = create_app()





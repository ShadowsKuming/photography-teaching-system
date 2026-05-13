"""
FastAPI application entry point.

Run with:
    conda activate photography-teaching
    uvicorn backend.api.app:app --reload --port 8000

Interactive docs available at:
    http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import interview, leaderboard, profiles, teaching
from backend.config import settings

app = FastAPI(
    title="Photography Teaching System",
    description="Personalised one-on-one photography teaching powered by AI.",
    version="0.1.0",
)

# allow_credentials=True is incompatible with allow_origins=["*"] per CORS spec
# (Starlette ≥ 0.36 raises ValueError at startup). Use explicit origins in prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router)
app.include_router(teaching.router)
app.include_router(profiles.router)
app.include_router(leaderboard.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "text_provider": settings.text_llm_provider,
        "text_model": settings.text_model,
        "vision_provider": settings.vision_llm_provider,
        "vision_model": settings.vision_model,
    }

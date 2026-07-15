"""
main.py
=======
FastAPI entry point for the Analysis Engine.

Endpoints:
    GET  /              — Health check
    POST /analyze       — Run full analysis pipeline on a ticker
    GET  /analysis/{id} — Retrieve a cached analysis result (future)
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title       = "Analysis Engine API",
    description = "Professional Multi-Timeframe Technical Analysis & Decision Support System",
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)


# ── Request / Response Models ─────────────────────────────────────────

class AnalysisRequest(BaseModel):
    ticker:       str   = "RELIANCE.NS"
    interval:     str   = "5m"
    period:       str   = "60d"
    account_size: float = 100_000.0
    risk_percent: float = 1.0


class AnalysisResponse(BaseModel):
    ticker:            str
    trend_direction:   str
    trend_strength:    float
    trend_confidence:  str
    mtf_tag:           str
    mtf_score:         float
    confluence_score:  float
    take_trade:        bool
    direction:         str
    confidence:        float
    entry:             float
    stop_loss:         float
    target:            float
    risk_reward:       float
    reasoning:         str


# ── Routes ────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Confirm the API is running."""
    return {
        "status":  "online",
        "service": "Analysis Engine",
        "version": "2.0.0",
    }


@app.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
def analyze(request: AnalysisRequest):
    """
    Run the full analysis pipeline on the requested ticker.

    Returns a structured trading recommendation with reasoning.
    """
    try:
        from backend.pipeline import run_pipeline

        ctx = run_pipeline(
            ticker       = request.ticker,
            interval     = request.interval,
            period       = request.period,
            account_size = request.account_size,
            risk_percent = request.risk_percent,
            show_chart   = False,
            verbose      = False,
        )

        t   = ctx.trend
        mtf = ctx.mtf_alignment
        c   = ctx.confluence
        s   = ctx.signal

        return AnalysisResponse(
            ticker           = request.ticker,
            trend_direction  = t.direction  if t   else "N/A",
            trend_strength   = t.strength   if t   else 0.0,
            trend_confidence = t.confidence if t   else "N/A",
            mtf_tag          = mtf.tag      if mtf else "N/A",
            mtf_score        = mtf.score    if mtf else 0.0,
            confluence_score = c.total      if c   else 0.0,
            take_trade       = s.take_trade if s   else False,
            direction        = s.direction  if s   else "No Trade",
            confidence       = s.confidence if s   else 0.0,
            entry            = s.entry      if s   else 0.0,
            stop_loss        = s.stop_loss  if s   else 0.0,
            target           = s.target     if s   else 0.0,
            risk_reward      = s.risk_reward if s  else 0.0,
            reasoning        = s.reasoning  if s   else "",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

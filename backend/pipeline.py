"""
pipeline.py
===========
Complete end-to-end execution pipeline for the Analysis Engine.

Run this script directly to perform a full analysis on any ticker:

    python pipeline.py
    python pipeline.py --ticker AAPL --period 60d --account 50000 --risk 1.5

Pipeline stages:
    1.  Download raw OHLCV data (Yahoo Finance)
    2.  Generate multi-timeframe data
    3.  Detect swings on primary timeframe
    4.  Build market structure
    5.  Run enhanced trend engine
    6.  Support & Resistance analysis
    7.  Supply & Demand zone detection
    8.  Momentum analysis
    9.  Volatility analysis
    10. MTF alignment
    11. Confluence scoring
    12. Trade planning
    13. Risk management + Signal
    14. Print report + optional chart
"""

from __future__ import annotations

import argparse

import pandas as pd

from backend.app.core.analysis_context import AnalysisContext
from backend.app.data.downloader       import DataDownloader
from backend.app.data.resampler        import MultiTimeframeGenerator
from backend.app.market_structure.swings    import SwingDetector
from backend.app.market_structure.structure import MarketStructure
from backend.app.market_structure.trend     import TrendEngine

from backend.app.analysis.support_resistance import SupportResistanceAnalyzer
from backend.app.analysis.supply_demand      import SupplyDemandAnalyzer
from backend.app.analysis.momentum          import MomentumAnalyzer
from backend.app.analysis.volatility        import VolatilityAnalyzer
from backend.app.analysis.mtf_alignment     import MTFAlignmentAnalyzer

from backend.app.decision.confluence    import ConfluenceCalculator
from backend.app.decision.trade_planner import TradePlanner
from backend.app.decision.risk_manager  import RiskManager
from backend.app.decision.signal_engine import SignalEngine


def run_pipeline(
    ticker:       str   = "RELIANCE.NS",
    interval:     str   = "5m",
    period:       str   = "60d",
    account_size: float = 100_000.0,
    risk_percent: float = 1.0,
    show_chart:   bool  = False,
    save_chart:   str   = "",
    verbose:      bool  = True,
) -> AnalysisContext:
    """
    Execute the full analysis pipeline.

    Args:
        ticker       : Yahoo Finance ticker symbol.
        interval     : Base data interval (default "5m").
        period       : Lookback period (default "60d").
        account_size : Account equity for risk calculation.
        risk_percent : Risk per trade in %.
        show_chart   : Display the full analysis chart.
        save_chart   : Path to save chart image (empty = don't save).
        verbose      : Print per-stage summaries.

    Returns:
        Populated AnalysisContext.
    """

    ctx = AnalysisContext(ticker=ticker, interval=interval)

    print(f"\n{'═'*55}")
    print(f"  Analysis Engine — {ticker}")
    print(f"  Interval: {interval}   Period: {period}")
    print(f"{'═'*55}\n")

    # ─────────────────────────────────────────────────────────────────
    # Stage 1 — Download
    # ─────────────────────────────────────────────────────────────────
    print("Stage 1/13  Download raw data...")
    downloader = DataDownloader(ticker=ticker, interval=interval, period=period)
    raw_df     = downloader.run()

    # ─────────────────────────────────────────────────────────────────
    # Stage 2 — Multi-Timeframe Resampling
    # ─────────────────────────────────────────────────────────────────
    print("Stage 2/13  Generate multi-timeframe data...")
    resampler           = MultiTimeframeGenerator(ticker=ticker)
    ctx.ohlc_by_timeframe = resampler.run(raw_df.set_index("Datetime"))

    # Primary timeframe = 1H
    primary_tf = "1h"
    if primary_tf not in ctx.ohlc_by_timeframe:
        primary_tf = list(ctx.ohlc_by_timeframe.keys())[0]

    ohlc = ctx.ohlc_by_timeframe[primary_tf].reset_index()
    ctx.ohlc = ohlc

    # ─────────────────────────────────────────────────────────────────
    # Stage 3 — Swing Detection
    # ─────────────────────────────────────────────────────────────────
    print("Stage 3/13  Detect swing points...")
    swing_det  = SwingDetector(window=2)
    ctx.swings = swing_det.run_on_df(ohlc)
    if verbose:
        n_sh = ctx.swings["Swing_High"].sum()
        n_sl = ctx.swings["Swing_Low"].sum()
        print(f"           {n_sh} swing highs, {n_sl} swing lows detected.")

    # ─────────────────────────────────────────────────────────────────
    # Stage 4 — Market Structure
    # ─────────────────────────────────────────────────────────────────
    print("Stage 4/13  Build market structure...")
    structure_points = []
    last_high = last_low = None
    swing_df  = ctx.swings

    for idx, row in swing_df.iterrows():
        if row["Swing_High"]:
            s = "SH" if last_high is None else ("HH" if row["High"] > last_high else "LH")
            last_high = row["High"]
            structure_points.append({
                "Index": idx,
                "Datetime": row.get("Datetime", idx),
                "Swing_Type": "High",
                "Price": row["High"],
                "Structure": s,
                "Swing_Strength": row.get("Swing_Strength", 50),
            })
        elif row["Swing_Low"]:
            s = "SL" if last_low is None else ("HL" if row["Low"] > last_low else "LL")
            last_low = row["Low"]
            structure_points.append({
                "Index": idx,
                "Datetime": row.get("Datetime", idx),
                "Swing_Type": "Low",
                "Price": row["Low"],
                "Structure": s,
                "Swing_Strength": row.get("Swing_Strength", 50),
            })

    ctx.structure = pd.DataFrame(structure_points)

    # ─────────────────────────────────────────────────────────────────
    # Stage 5 — Trend Engine
    # ─────────────────────────────────────────────────────────────────
    print("Stage 5/13  Analyse trend...")
    trend_engine  = TrendEngine(ctx.structure, ctx.swings)
    ctx.trend, _  = trend_engine.run()

    if verbose:
        t = ctx.trend
        print(f"           {t.direction}  strength={t.strength:.0f}/100  confidence={t.confidence}")

    # ─────────────────────────────────────────────────────────────────
    # Stage 6 — Support & Resistance
    # ─────────────────────────────────────────────────────────────────
    print("Stage 6/13  Support & Resistance...")
    sr_analyzer = SupportResistanceAnalyzer()
    ctx = sr_analyzer.analyze(ctx)
    if verbose:
        sr_analyzer.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 7 — Supply & Demand
    # ─────────────────────────────────────────────────────────────────
    print("Stage 7/13  Supply & Demand zones...")
    sd_analyzer = SupplyDemandAnalyzer()
    ctx = sd_analyzer.analyze(ctx)
    if verbose:
        sd_analyzer.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 8 — Momentum
    # ─────────────────────────────────────────────────────────────────
    print("Stage 8/13  Momentum analysis...")
    mom_analyzer = MomentumAnalyzer()
    ctx = mom_analyzer.analyze(ctx)
    if verbose:
        mom_analyzer.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 9 — Volatility
    # ─────────────────────────────────────────────────────────────────
    print("Stage 9/13  Volatility analysis...")
    vol_analyzer = VolatilityAnalyzer()
    ctx = vol_analyzer.analyze(ctx)
    if verbose:
        vol_analyzer.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 10 — MTF Alignment
    # ─────────────────────────────────────────────────────────────────
    print("Stage 10/13 MTF alignment...")
    mtf_analyzer = MTFAlignmentAnalyzer()
    ctx = mtf_analyzer.analyze(ctx)
    if verbose:
        mtf_analyzer.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 11 — Confluence
    # ─────────────────────────────────────────────────────────────────
    print("Stage 11/13 Confluence scoring...")
    confluence = ConfluenceCalculator()
    ctx = confluence.analyze(ctx)
    if verbose:
        confluence.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 12 — Trade Plan
    # ─────────────────────────────────────────────────────────────────
    print("Stage 12/13 Trade planning...")
    planner = TradePlanner()
    ctx     = planner.analyze(ctx)
    if verbose:
        planner.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Stage 13 — Risk + Signal
    # ─────────────────────────────────────────────────────────────────
    print("Stage 13/13 Risk management + Signal...")
    risk_mgr  = RiskManager(account_size=account_size, risk_percent=risk_percent)
    signal_eng = SignalEngine(risk_manager=risk_mgr)
    ctx        = signal_eng.analyze(ctx)
    signal_eng.summary(ctx)

    # ─────────────────────────────────────────────────────────────────
    # Final Summary
    # ─────────────────────────────────────────────────────────────────
    ctx.summary()

    # ─────────────────────────────────────────────────────────────────
    # Optional Chart
    # ─────────────────────────────────────────────────────────────────
    if show_chart or save_chart:
        from backend.app.visualization.chart_full import AnalysisChart
        chart = AnalysisChart(
            context   = ctx,
            save_path = save_chart if save_chart else None,
        )
        chart.plot()

    return ctx


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Analysis Engine Pipeline")
    parser.add_argument("--ticker",   default="RELIANCE.NS",    help="Yahoo Finance ticker")
    parser.add_argument("--interval", default="5m",             help="Base interval (e.g. 5m, 1h)")
    parser.add_argument("--period",   default="60d",            help="Data period (e.g. 30d, 90d)")
    parser.add_argument("--account",  default=100_000, type=float, help="Account size")
    parser.add_argument("--risk",     default=1.0,    type=float, help="Risk % per trade")
    parser.add_argument("--chart",    action="store_true",       help="Show analysis chart")
    parser.add_argument("--save",     default="",               help="Save chart to this path")

    args = parser.parse_args()

    run_pipeline(
        ticker       = args.ticker,
        interval     = args.interval,
        period       = args.period,
        account_size = args.account,
        risk_percent = args.risk,
        show_chart   = args.chart,
        save_chart   = args.save,
        verbose      = True,
    )

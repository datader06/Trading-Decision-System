"""
chart_full.py
=============
Full analysis chart that renders all layers on a single figure:

    Panel 1 (main):
        Candlesticks, swing points, supply/demand zones,
        support/resistance levels, trade entry / SL / TP lines.

    Panel 2:
        RSI with overbought (70) and oversold (30) lines.

    Panel 3:
        MACD histogram.

    Panel 4:
        ATR with volatility regime background shading.

Usage:
    from backend.app.visualization.chart_full import AnalysisChart
    chart = AnalysisChart(context)
    chart.plot()
"""

from __future__ import annotations
from typing import Optional

import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class AnalysisChart:
    """
    Renders the full multi-layer analysis chart from an AnalysisContext.

    Args:
        context   : Populated AnalysisContext object.
        max_bars  : Number of recent bars to display (default 120).
        style     : mplfinance style string (default "charles").
        save_path : If provided, saves chart to this file instead of showing.
    """

    def __init__(
        self,
        context,
        max_bars:  int            = 120,
        style:     str            = "charles",
        save_path: Optional[str]  = None,
    ) -> None:
        self.context   = context
        self.max_bars  = max_bars
        self.style     = style
        self.save_path = save_path

    # ─────────────────────────────────────────────────────────────────
    def _prepare_df(self) -> pd.DataFrame:
        df = self.context.ohlc
        if df is None:
            raise ValueError("AnalysisContext.ohlc is None — run the pipeline first.")

        # Ensure datetime index
        if "Datetime" in df.columns:
            df = df.set_index("Datetime")
        df.index = pd.to_datetime(df.index)

        # Trim to last N bars
        df = df.tail(self.max_bars).copy()
        return df

    # ─────────────────────────────────────────────────────────────────
    def _compute_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
        rs    = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _compute_macd_hist(self, close: pd.Series) -> pd.Series:
        macd   = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd - signal

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"].shift(1)
        tr = pd.concat(
            [high - low, (high - close).abs(), (low - close).abs()], axis=1
        ).max(axis=1)
        return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    # ─────────────────────────────────────────────────────────────────
    def plot(self) -> None:
        ctx = self.context
        df  = self._prepare_df()

        close = df["Close"]
        rsi   = self._compute_rsi(close)
        macd  = self._compute_macd_hist(close)
        atr   = self._compute_atr(df)

        # ── Swing markers ─────────────────────────────────────────
        swing_df = ctx.swings
        add_plots = []

        if swing_df is not None:
            if "Datetime" in swing_df.columns:
                swing_df = swing_df.set_index("Datetime")
            swing_df.index = pd.to_datetime(swing_df.index)
            swing_df       = swing_df[swing_df.index.isin(df.index)]

            sh_series = df["High"].where(swing_df.get("Swing_High", pd.Series(dtype=bool)).reindex(df.index))
            sl_series = df["Low"].where(swing_df.get("Swing_Low",  pd.Series(dtype=bool)).reindex(df.index))

            if sh_series.notna().any():
                add_plots.append(mpf.make_addplot(
                    sh_series, type="scatter", markersize=60,
                    marker="^", color="lime", panel=0,
                ))
            if sl_series.notna().any():
                add_plots.append(mpf.make_addplot(
                    sl_series, type="scatter", markersize=60,
                    marker="v", color="red", panel=0,
                ))

        # ── RSI ───────────────────────────────────────────────────
        rsi_aligned = rsi.reindex(df.index)
        add_plots.append(mpf.make_addplot(
            rsi_aligned, panel=1, color="purple", ylabel="RSI", ylim=(0, 100),
        ))
        ob_line = pd.Series(70, index=df.index)
        os_line = pd.Series(30, index=df.index)
        add_plots.append(mpf.make_addplot(ob_line, panel=1, color="red",   linestyle="--", width=0.7))
        add_plots.append(mpf.make_addplot(os_line, panel=1, color="green", linestyle="--", width=0.7))

        # ── MACD Histogram ────────────────────────────────────────
        macd_aligned = macd.reindex(df.index)
        macd_colors  = ["#26a69a" if v >= 0 else "#ef5350" for v in macd_aligned.fillna(0)]
        add_plots.append(mpf.make_addplot(
            macd_aligned, type="bar", panel=2, color=macd_colors, ylabel="MACD",
        ))

        # ── ATR ───────────────────────────────────────────────────
        atr_aligned = atr.reindex(df.index)
        add_plots.append(mpf.make_addplot(
            atr_aligned, panel=3, color="orange", ylabel="ATR",
        ))

        # ── Build figure ──────────────────────────────────────────
        ticker = ctx.ticker or "Chart"
        trend  = ctx.trend
        title  = (
            f"{ticker} — "
            f"Trend: {trend.direction} ({trend.confidence}) | "
            f"Strength: {trend.strength:.0f}/100"
            if trend
            else f"{ticker} — Full Analysis Chart"
        )

        fig, axes = mpf.plot(
            df,
            type       = "candle",
            style      = self.style,
            title      = title,
            volume     = False,
            addplot    = add_plots,
            panel_ratios = (4, 1.5, 1, 1),
            figsize    = (18, 12),
            returnfig  = True,
        )

        main_ax = axes[0]

        # ── Supply Zones ─────────────────────────────────────────
        for z in ctx.supply_zones:
            main_ax.axhspan(
                z.bottom, z.top,
                alpha=0.15, color="red",
                label=f"Supply {z.bottom:.2f}–{z.top:.2f}",
            )

        # ── Demand Zones ──────────────────────────────────────────
        for z in ctx.demand_zones:
            main_ax.axhspan(
                z.bottom, z.top,
                alpha=0.15, color="green",
                label=f"Demand {z.bottom:.2f}–{z.top:.2f}",
            )

        # ── S/R Levels ────────────────────────────────────────────
        for r in ctx.resistance_levels:
            main_ax.axhline(y=r.price, color="red",   linestyle=":", linewidth=1, alpha=0.7)
        for s in ctx.support_levels:
            main_ax.axhline(y=s.price, color="green", linestyle=":", linewidth=1, alpha=0.7)

        # ── Trade Levels ──────────────────────────────────────────
        signal = ctx.signal
        if signal and signal.take_trade and signal.entry > 0:
            main_ax.axhline(y=signal.entry,     color="white",  linestyle="-",  linewidth=1.5, label="Entry")
            main_ax.axhline(y=signal.stop_loss, color="#ef5350",linestyle="--", linewidth=1.5, label="Stop Loss")
            main_ax.axhline(y=signal.target,    color="#26a69a",linestyle="--", linewidth=1.5, label="Target 1")
            if signal.trade_plan:
                main_ax.axhline(
                    y=signal.trade_plan.target_2,
                    color="#00bcd4", linestyle="--", linewidth=1.0, label="Target 2",
                )

        # ── Legend ────────────────────────────────────────────────
        patches = [
            mpatches.Patch(color="lime",    alpha=0.8, label="Swing High"),
            mpatches.Patch(color="red",     alpha=0.8, label="Swing Low"),
            mpatches.Patch(color="red",     alpha=0.3, label="Supply Zone"),
            mpatches.Patch(color="green",   alpha=0.3, label="Demand Zone"),
        ]
        main_ax.legend(handles=patches, loc="upper left", fontsize=8)

        plt.tight_layout()

        if self.save_path:
            fig.savefig(self.save_path, dpi=150, bbox_inches="tight")
            print(f"Chart saved to: {self.save_path}")
        else:
            plt.show()

"""
Technical Engine - تحليل فني احترافي
يشمل: EMA, RSI, MACD, ATR, ADX
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class TechAnalysis:
    ema_fast: float
    ema_slow: float
    ema_200: float
    ema_trend: str       # BULLISH / BEARISH / NEUTRAL
    rsi: float
    rsi_signal: str      # OVERSOLD / OVERBOUGHT / NEUTRAL
    macd: float
    macd_signal: float
    macd_hist: float
    macd_cross: str      # BULLISH / BEARISH / NONE
    atr: float
    atr_pct: float       # ATR كنسبة من السعر
    adx: float
    adx_trend: str       # STRONG / MODERATE / WEAK
    plus_di: float
    minus_di: float
    tech_score: float    # 0-100
    confirmed: bool      # هل التحليل الفني يؤكد الإشارة؟


class TechEngine:
    """محرك التحليل الفني"""

    def __init__(
        self,
        ema_fast: int = 21,
        ema_slow: int = 50,
        ema_trend: int = 200,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        atr_period: int = 14,
        adx_period: int = 14,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal_period = macd_signal
        self.atr_period = atr_period
        self.adx_period = adx_period

    # ─────────────────────────────── EMA ───────────────────────────────────

    def calc_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def get_ema(self, df: pd.DataFrame) -> dict:
        close = df["close"]
        fast = self.calc_ema(close, self.ema_fast).iloc[-1]
        slow = self.calc_ema(close, self.ema_slow).iloc[-1]
        trend_ema = self.calc_ema(close, self.ema_trend).iloc[-1]
        current = close.iloc[-1]

        if fast > slow > trend_ema:
            trend = "BULLISH"
        elif fast < slow < trend_ema:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        return {
            "fast": fast,
            "slow": slow,
            "trend_200": trend_ema,
            "current": current,
            "trend": trend,
            "above_200": current > trend_ema,
        }

    # ─────────────────────────────── RSI ───────────────────────────────────

    def calc_rsi(self, df: pd.DataFrame) -> float:
        close = df["close"]
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=self.rsi_period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=self.rsi_period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def get_rsi_signal(self, rsi: float, bias: str = "NEUTRAL") -> str:
        """
        النطاق المثالي للإشارة: 40-60
        فوق 70: OVERBOUGHT, تحت 30: OVERSOLD
        """
        if rsi < 30:
            return "OVERSOLD"
        elif rsi > 70:
            return "OVERBOUGHT"
        elif 40 <= rsi <= 60:
            return "NEUTRAL_IDEAL"
        elif rsi < 40:
            return "WEAK"
        else:
            return "STRONG"

    # ─────────────────────────────── MACD ──────────────────────────────────

    def calc_macd(self, df: pd.DataFrame) -> dict:
        close = df["close"]
        ema_fast = self.calc_ema(close, self.macd_fast)
        ema_slow = self.calc_ema(close, self.macd_slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.calc_ema(macd_line, self.macd_signal_period)
        histogram = macd_line - signal_line

        # كشف التقاطع
        cross = "NONE"
        if len(histogram) >= 2:
            if histogram.iloc[-2] < 0 <= histogram.iloc[-1]:
                cross = "BULLISH"
            elif histogram.iloc[-2] > 0 >= histogram.iloc[-1]:
                cross = "BEARISH"

        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
            "cross": cross,
            "bullish": macd_line.iloc[-1] > signal_line.iloc[-1],
        }

    # ─────────────────────────────── ATR ───────────────────────────────────

    def calc_atr(self, df: pd.DataFrame) -> dict:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)

        atr = tr.ewm(com=self.atr_period - 1, adjust=False).mean().iloc[-1]
        current_price = close.iloc[-1]

        return {
            "atr": float(atr),
            "atr_pct": float(atr / current_price * 100),
        }

    # ─────────────────────────────── ADX ───────────────────────────────────

    def calc_adx(self, df: pd.DataFrame) -> dict:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        period = self.adx_period

        # True Range
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)

        # Directional Movement
        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        # Smooth
        atr_s = tr.ewm(com=period - 1, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(com=period - 1, adjust=False).mean() / atr_s
        minus_di = 100 * minus_dm.ewm(com=period - 1, adjust=False).mean() / atr_s

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(com=period - 1, adjust=False).mean()

        adx_val = float(adx.iloc[-1])
        pdi = float(plus_di.iloc[-1])
        mdi = float(minus_di.iloc[-1])

        if adx_val >= 25:
            trend_strength = "STRONG"
        elif adx_val >= 15:
            trend_strength = "MODERATE"
        else:
            trend_strength = "WEAK"

        return {
            "adx": adx_val,
            "plus_di": pdi,
            "minus_di": mdi,
            "trend_strength": trend_strength,
            "bullish_di": pdi > mdi,
        }

    # ─────────────────────────────── Master Analysis ───────────────────────

    def analyze(self, df: pd.DataFrame, ict_bias: str = "NEUTRAL") -> TechAnalysis:
        """التحليل الفني الكامل"""
        min_candles = max(self.ema_trend, self.macd_slow + self.macd_signal_period) + 10
        if len(df) < min_candles:
            raise ValueError(f"يجب توفير على الأقل {min_candles} شمعة")

        ema = self.get_ema(df)
        rsi = self.calc_rsi(df)
        rsi_sig = self.get_rsi_signal(rsi, ict_bias)
        macd = self.calc_macd(df)
        atr = self.calc_atr(df)
        adx = self.calc_adx(df)

        # حساب درجة التحليل الفني
        score = 0.0
        bullish_signals = 0
        bearish_signals = 0

        # EMA
        if ema["trend"] == "BULLISH":
            bullish_signals += 1
            score += 20
        elif ema["trend"] == "BEARISH":
            bearish_signals += 1
            score += 20

        # RSI (الشرط: 40-60)
        if rsi_sig == "NEUTRAL_IDEAL":
            score += 25
            if ict_bias == "BULLISH":
                bullish_signals += 1
            elif ict_bias == "BEARISH":
                bearish_signals += 1

        # MACD
        if macd["bullish"]:
            bullish_signals += 1
            score += 15
        else:
            bearish_signals += 1
            score += 15

        if macd["cross"] != "NONE":
            score += 10  # تقاطع إضافي

        # ADX
        if adx["trend_strength"] == "STRONG":
            score += 20
        elif adx["trend_strength"] == "MODERATE":
            score += 10

        # تأكيد مع bias من ICT
        confirmed = (
            ict_bias == "BULLISH" and
            ema["trend"] in ["BULLISH", "NEUTRAL"] and
            rsi_sig == "NEUTRAL_IDEAL" and
            macd["bullish"] and
            adx["trend_strength"] != "WEAK"
        ) or (
            ict_bias == "BEARISH" and
            ema["trend"] in ["BEARISH", "NEUTRAL"] and
            rsi_sig == "NEUTRAL_IDEAL" and
            not macd["bullish"] and
            adx["trend_strength"] != "WEAK"
        )

        return TechAnalysis(
            ema_fast=ema["fast"],
            ema_slow=ema["slow"],
            ema_200=ema["trend_200"],
            ema_trend=ema["trend"],
            rsi=rsi,
            rsi_signal=rsi_sig,
            macd=macd["macd"],
            macd_signal=macd["signal"],
            macd_hist=macd["histogram"],
            macd_cross=macd["cross"],
            atr=atr["atr"],
            atr_pct=atr["atr_pct"],
            adx=adx["adx"],
            adx_trend=adx["trend_strength"],
            plus_di=adx["plus_di"],
            minus_di=adx["minus_di"],
            tech_score=min(score, 100.0),
            confirmed=confirmed,
        )

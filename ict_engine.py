"""
ICT Engine - تحليل ICT الاحترافي
يشمل: Killzone, FVG, Order Blocks, BOS/CHoCH, Liquidity Sweeps
"""

from datetime import datetime, time
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
import pytz


@dataclass
class ICTAnalysis:
    killzone_active: bool
    killzone_name: str
    fvg: Optional[dict]
    order_block: Optional[dict]
    bos_choch: Optional[dict]
    liquidity_sweep: Optional[dict]
    bias: str  # BULLISH / BEARISH / NEUTRAL
    ict_score: float  # 0-100


class ICTEngine:
    """محرك تحليل ICT الكامل"""

    KILLZONES = {
        "Asian":    (time(0, 0),  time(4, 0)),
        "London":   (time(7, 0),  time(10, 0)),
        "New York": (time(12, 0), time(15, 0)),
        "NY Close": (time(19, 0), time(21, 0)),
    }

    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol
        self.tz = pytz.UTC

    # ─────────────────────────────── Killzone ──────────────────────────────

    def get_killzone(self, dt: Optional[datetime] = None) -> tuple[bool, str]:
        """هل نحن داخل Killzone نشط؟"""
        dt = dt or datetime.now(self.tz)
        current = dt.time()
        for name, (start, end) in self.KILLZONES.items():
            if start <= current <= end:
                return True, name
        return False, "None"

    # ─────────────────────────────── FVG ───────────────────────────────────

    def detect_fvg(self, df: pd.DataFrame, lookback: int = 50) -> Optional[dict]:
        """
        Fair Value Gap: فجوة بين شمعتين غير متداخلتين مع شمعة وسيطة
        Bullish FVG: low[i+2] > high[i]
        Bearish FVG: high[i+2] < low[i]
        """
        df = df.tail(lookback).reset_index(drop=True)
        fvgs = []

        for i in range(len(df) - 2):
            c0, c1, c2 = df.iloc[i], df.iloc[i + 1], df.iloc[i + 2]

            # Bullish FVG
            if c2["low"] > c0["high"]:
                fvgs.append({
                    "type": "BULLISH",
                    "top": c2["low"],
                    "bottom": c0["high"],
                    "midpoint": (c2["low"] + c0["high"]) / 2,
                    "index": i + 1,
                    "timestamp": c1.get("timestamp", i + 1),
                    "filled": False,
                })

            # Bearish FVG
            elif c2["high"] < c0["low"]:
                fvgs.append({
                    "type": "BEARISH",
                    "top": c0["low"],
                    "bottom": c2["high"],
                    "midpoint": (c0["low"] + c2["high"]) / 2,
                    "index": i + 1,
                    "timestamp": c1.get("timestamp", i + 1),
                    "filled": False,
                })

        # أحدث FVG غير مملوء
        current_price = df.iloc[-1]["close"]
        for fvg in reversed(fvgs):
            if fvg["type"] == "BULLISH" and current_price >= fvg["bottom"]:
                fvg["distance_pct"] = abs(current_price - fvg["midpoint"]) / current_price * 100
                return fvg
            elif fvg["type"] == "BEARISH" and current_price <= fvg["top"]:
                fvg["distance_pct"] = abs(current_price - fvg["midpoint"]) / current_price * 100
                return fvg

        return None

    # ─────────────────────────────── Order Block ───────────────────────────

    def detect_order_block(self, df: pd.DataFrame, lookback: int = 100) -> Optional[dict]:
        """
        Order Block: آخر شمعة عكسية قبل حركة قوية
        Bullish OB: شمعة هابطة قبل ارتفاع قوي
        Bearish OB: شمعة صاعدة قبل هبوط قوي
        """
        df = df.tail(lookback).reset_index(drop=True)
        obs = []

        for i in range(1, len(df) - 1):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            nxt = df.iloc[i + 1]

            body_size = abs(curr["close"] - curr["open"])
            next_move = abs(nxt["close"] - nxt["open"])

            # Bullish OB: شمعة حمراء قبل شمعة خضراء قوية
            if (curr["close"] < curr["open"] and
                    nxt["close"] > nxt["open"] and
                    next_move > body_size * 1.5):
                obs.append({
                    "type": "BULLISH",
                    "top": curr["high"],
                    "bottom": curr["low"],
                    "open": curr["open"],
                    "close": curr["close"],
                    "index": i,
                    "strength": next_move / body_size if body_size > 0 else 1,
                })

            # Bearish OB: شمعة خضراء قبل شمعة حمراء قوية
            elif (curr["close"] > curr["open"] and
                  nxt["close"] < nxt["open"] and
                  next_move > body_size * 1.5):
                obs.append({
                    "type": "BEARISH",
                    "top": curr["high"],
                    "bottom": curr["low"],
                    "open": curr["open"],
                    "close": curr["close"],
                    "index": i,
                    "strength": next_move / body_size if body_size > 0 else 1,
                })

        if not obs:
            return None

        # أقوى OB
        best_ob = max(obs, key=lambda x: x["strength"])
        current_price = df.iloc[-1]["close"]
        best_ob["distance_pct"] = abs(current_price - (best_ob["top"] + best_ob["bottom"]) / 2) / current_price * 100
        return best_ob

    # ─────────────────────────────── BOS / CHoCH ───────────────────────────

    def detect_bos_choch(self, df: pd.DataFrame, lookback: int = 50) -> Optional[dict]:
        """
        BOS: Break of Structure - كسر هيكل في نفس الاتجاه
        CHoCH: Change of Character - تغيير في الاتجاه
        """
        df = df.tail(lookback).reset_index(drop=True)

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        # إيجاد القمم والقيعان المحلية
        swing_highs = []
        swing_lows = []

        for i in range(2, len(df) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append((i, highs[i]))
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append((i, lows[i]))

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None

        last_high = swing_highs[-1]
        prev_high = swing_highs[-2]
        last_low = swing_lows[-1]
        prev_low = swing_lows[-2]

        current_price = closes[-1]
        result = None

        # BOS صاعد: كسر قمة سابقة
        if current_price > prev_high[1] and last_high[1] > prev_high[1]:
            result = {
                "type": "BOS",
                "direction": "BULLISH",
                "level": prev_high[1],
                "broken_at": last_high[1],
                "strength": (last_high[1] - prev_high[1]) / prev_high[1] * 100,
            }

        # BOS هابط: كسر قاع سابق
        elif current_price < prev_low[1] and last_low[1] < prev_low[1]:
            result = {
                "type": "BOS",
                "direction": "BEARISH",
                "level": prev_low[1],
                "broken_at": last_low[1],
                "strength": (prev_low[1] - last_low[1]) / prev_low[1] * 100,
            }

        # CHoCH: تغيير الاتجاه
        elif (last_high[1] < prev_high[1] and last_low[1] > prev_low[1]):
            result = {
                "type": "CHoCH",
                "direction": "BULLISH",
                "level": prev_low[1],
                "note": "Consolidation → possible reversal up",
                "strength": 50.0,
            }
        elif (last_high[1] > prev_high[1] and last_low[1] < prev_low[1]):
            result = {
                "type": "CHoCH",
                "direction": "BEARISH",
                "level": prev_high[1],
                "note": "Consolidation → possible reversal down",
                "strength": 50.0,
            }

        return result

    # ─────────────────────────────── Liquidity Sweep ───────────────────────

    def detect_liquidity_sweep(self, df: pd.DataFrame, lookback: int = 30) -> Optional[dict]:
        """
        Liquidity Sweep: اختراق مستوى سيولة ثم عودة سريعة
        يشير إلى تلاعب المؤسسات
        """
        df = df.tail(lookback).reset_index(drop=True)

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        # أعلى قمة وأدنى قاع
        recent_high = np.max(highs[:-3])
        recent_low = np.min(lows[:-3])

        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        # Bearish sweep: اختراق القمة ثم إغلاق تحتها
        if (last_candle["high"] > recent_high and
                last_candle["close"] < recent_high):
            return {
                "type": "BEARISH_SWEEP",
                "level": recent_high,
                "high": last_candle["high"],
                "close": last_candle["close"],
                "implication": "BEARISH - institutions took buy stops",
                "wick_size": last_candle["high"] - last_candle["close"],
            }

        # Bullish sweep: اختراق القاع ثم إغلاق فوقه
        if (last_candle["low"] < recent_low and
                last_candle["close"] > recent_low):
            return {
                "type": "BULLISH_SWEEP",
                "level": recent_low,
                "low": last_candle["low"],
                "close": last_candle["close"],
                "implication": "BULLISH - institutions took sell stops",
                "wick_size": last_candle["close"] - last_candle["low"],
            }

        return None

    # ─────────────────────────────── Master Analysis ───────────────────────

    def analyze(self, df: pd.DataFrame, dt: Optional[datetime] = None) -> ICTAnalysis:
        """التحليل الكامل وإرجاع ICTAnalysis"""

        kz_active, kz_name = self.get_killzone(dt)
        fvg = self.detect_fvg(df)
        ob = self.detect_order_block(df)
        bos = self.detect_bos_choch(df)
        liq = self.detect_liquidity_sweep(df)

        # تحديد الاتجاه العام
        bias_votes = {"BULLISH": 0, "BEARISH": 0}

        if fvg:
            bias_votes[fvg["type"]] += 1
        if ob:
            bias_votes[ob["type"]] += 1
        if bos:
            bias_votes[bos["direction"]] += 2  # BOS أهم
        if liq:
            if "BULLISH" in liq["type"]:
                bias_votes["BULLISH"] += 1
            else:
                bias_votes["BEARISH"] += 1

        if bias_votes["BULLISH"] > bias_votes["BEARISH"]:
            bias = "BULLISH"
        elif bias_votes["BEARISH"] > bias_votes["BULLISH"]:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        # حساب درجة ICT
        score = 0.0
        if kz_active:
            score += 25
        if fvg:
            score += 20
        if ob:
            score += 20
        if bos:
            score += 25 if bos["type"] == "BOS" else 15
        if liq:
            score += 10

        return ICTAnalysis(
            killzone_active=kz_active,
            killzone_name=kz_name,
            fvg=fvg,
            order_block=ob,
            bos_choch=bos,
            liquidity_sweep=liq,
            bias=bias,
            ict_score=min(score, 100.0),
        )

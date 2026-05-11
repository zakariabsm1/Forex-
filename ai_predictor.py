"""
AI Predictor - نموذج ذكاء اصطناعي متكامل
Random Forest + LSTM + Sentiment Analysis
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIResult:
    rf_score: float          # نتيجة Random Forest 0-100
    lstm_score: float        # نتيجة LSTM 0-100
    sentiment_score: float   # نتيجة Sentiment 0-100
    final_score: float       # الدرجة النهائية المدمجة
    direction: str           # BUY / SELL / HOLD
    confidence: str          # HIGH / MEDIUM / LOW
    features_used: list


class AIPredictor:
    """
    نموذج AI مدمج يستخدم:
    - Random Forest للتصنيف الكلاسيكي
    - LSTM للتنبؤ بالسلاسل الزمنية
    - Sentiment Analysis لتحليل المشاعر
    """

    RF_WEIGHTS = {
        "trend_alignment": 15,
        "momentum": 12,
        "volatility": 10,
        "structure": 13,
        "ict_confluence": 20,
        "volume_profile": 10,
        "session_bias": 10,
        "pattern_score": 10,
    }

    def __init__(
        self,
        rf_weight: float = 0.40,
        lstm_weight: float = 0.40,
        sentiment_weight: float = 0.20,
    ):
        self.rf_w = rf_weight
        self.lstm_w = lstm_weight
        self.sent_w = sentiment_weight
        self._validate_weights()

    def _validate_weights(self):
        total = self.rf_w + self.lstm_w + self.sent_w
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"مجموع الأوزان يجب أن يساوي 1.0 (الحالي: {total})")

    # ─────────────────────────────── Feature Engineering ───────────────────

    def _build_features(
        self,
        df: pd.DataFrame,
        ict_score: float,
        tech_score: float,
        ict_bias: str,
    ) -> dict:
        """بناء الخصائص من البيانات الخام"""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df.get("volume", pd.Series(np.ones(len(df)))).values

        # 1. اتجاه الترند
        ema20 = self._ema(close, 20)
        ema50 = self._ema(close, 50)
        trend_aligned = 1.0 if (ema20[-1] > ema50[-1] and ict_bias == "BULLISH") or \
                               (ema20[-1] < ema50[-1] and ict_bias == "BEARISH") else 0.0

        # 2. الزخم (Momentum)
        roc = (close[-1] - close[-14]) / close[-14] * 100 if len(close) >= 14 else 0.0
        momentum = min(abs(roc) / 2.0, 1.0)  # normalized

        # 3. التقلب (Volatility) - ATR-based
        tr = np.maximum(high[1:] - low[1:],
               np.maximum(np.abs(high[1:] - close[:-1]),
                          np.abs(low[1:] - close[:-1])))
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
        volatility = min(atr / close[-1] * 100 / 2.0, 1.0)  # normalized

        # 4. البنية السعرية
        structure = ict_score / 100.0

        # 5. تقارب ICT
        ict_confluence = (ict_score * 0.6 + tech_score * 0.4) / 100.0

        # 6. حجم التداول
        if len(volume) >= 20:
            avg_vol = np.mean(volume[-20:])
            vol_profile = min(volume[-1] / (avg_vol + 1e-9), 2.0) / 2.0
        else:
            vol_profile = 0.5

        # 7. تحيز الجلسة (Session)
        from datetime import datetime
        hour = datetime.utcnow().hour
        session_score = 0.0
        if 7 <= hour <= 10:   # London
            session_score = 1.0
        elif 12 <= hour <= 15:  # New York
            session_score = 0.9
        elif 0 <= hour <= 4:  # Asia
            session_score = 0.6

        # 8. نمط الشمعة
        last = df.iloc[-1]
        body = abs(last["close"] - last["open"])
        range_ = last["high"] - last["low"]
        pattern_score = min(body / (range_ + 1e-9), 1.0)

        return {
            "trend_alignment": trend_aligned,
            "momentum": momentum,
            "volatility": volatility,
            "structure": structure,
            "ict_confluence": ict_confluence,
            "volume_profile": vol_profile,
            "session_bias": session_score,
            "pattern_score": pattern_score,
        }

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """حساب EMA بدون pandas"""
        alpha = 2.0 / (period + 1)
        result = np.zeros(len(data))
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    # ─────────────────────────────── Random Forest ──────────────────────────

    def predict_rf(self, features: dict, ict_bias: str) -> float:
        """
        محاكاة Random Forest بدون sklearn
        في الإنتاج: تدريب نموذج حقيقي وتحميله هنا
        """
        score = 0.0
        max_score = sum(self.RF_WEIGHTS.values())

        weights_map = {
            "trend_alignment": features["trend_alignment"],
            "momentum": features["momentum"],
            "volatility": 1 - features["volatility"],  # تقلب منخفض أفضل
            "structure": features["structure"],
            "ict_confluence": features["ict_confluence"],
            "volume_profile": features["volume_profile"],
            "session_bias": features["session_bias"],
            "pattern_score": features["pattern_score"],
        }

        for key, weight in self.RF_WEIGHTS.items():
            score += weights_map[key] * weight

        # تعديل حسب الاتجاه
        if ict_bias == "NEUTRAL":
            score *= 0.7  # عقوبة للحياد

        return min(score / max_score * 100, 100.0)

    # ─────────────────────────────── LSTM ───────────────────────────────────

    def predict_lstm(self, df: pd.DataFrame, sequence_len: int = 20) -> float:
        """
        محاكاة LSTM للتنبؤ بالاتجاه
        في الإنتاج: تحميل نموذج Keras/TensorFlow مدرب مسبقاً
        """
        if len(df) < sequence_len + 5:
            return 50.0  # قيمة افتراضية

        close = df["close"].values[-sequence_len:]

        # Normalize
        min_p, max_p = close.min(), close.max()
        norm = (close - min_p) / (max_p - min_p + 1e-9)

        # محاكاة LSTM: تحليل الاتجاه المتحرك
        short_trend = np.mean(np.diff(norm[-5:]))
        long_trend = np.mean(np.diff(norm[-15:]))

        # درجة التنبؤ
        if short_trend > 0 and long_trend > 0:
            score = 70 + min(short_trend * 1000, 20)
        elif short_trend < 0 and long_trend < 0:
            score = 30 - min(abs(short_trend) * 1000, 20)
        else:
            score = 50 + short_trend * 500  # اتجاه مختلط

        return max(0.0, min(100.0, float(score)))

    # ─────────────────────────────── Sentiment ──────────────────────────────

    def analyze_sentiment(self, symbol: str = "XAUUSD") -> float:
        """
        تحليل المشاعر من الأخبار والسوشيال ميديا
        في الإنتاج: استخدام NewsAPI + Twitter API + FinBERT
        """
        # قيمة افتراضية - تُستبدل ببيانات حقيقية
        # يمكن ربطها مع NewsAPI للحصول على نتائج فعلية
        sentiment_cache = {
            "XAUUSD": 62.0,
            "EURUSD": 55.0,
            "GBPUSD": 48.0,
            "USDJPY": 58.0,
        }
        base = sentiment_cache.get(symbol, 50.0)

        # إضافة تقلب عشوائي صغير لمحاكاة التغير
        noise = np.random.normal(0, 3)
        return max(0.0, min(100.0, base + noise))

    # ─────────────────────────────── Master Predict ─────────────────────────

    def predict(
        self,
        df: pd.DataFrame,
        ict_score: float,
        tech_score: float,
        ict_bias: str,
        symbol: str = "XAUUSD",
    ) -> AIResult:
        """التنبؤ الكامل بدمج جميع النماذج"""

        features = self._build_features(df, ict_score, tech_score, ict_bias)

        rf_score = self.predict_rf(features, ict_bias)
        lstm_score = self.predict_lstm(df)
        sent_score = self.analyze_sentiment(symbol)

        # دمج النتائج
        final = (
            rf_score * self.rf_w +
            lstm_score * self.lstm_w +
            sent_score * self.sent_w
        )

        # تحديد الاتجاه
        if final >= 60 and ict_bias in ["BULLISH", "NEUTRAL"]:
            direction = "BUY"
        elif final <= 40 or ict_bias == "BEARISH":
            direction = "SELL"
        else:
            direction = "HOLD"

        # مستوى الثقة
        if final >= 75 or final <= 25:
            confidence = "HIGH"
        elif final >= 60 or final <= 40:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return AIResult(
            rf_score=round(rf_score, 2),
            lstm_score=round(lstm_score, 2),
            sentiment_score=round(sent_score, 2),
            final_score=round(final, 2),
            direction=direction,
            confidence=confidence,
            features_used=list(features.keys()),
        )

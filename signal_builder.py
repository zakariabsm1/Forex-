"""
Signal Builder - بناء إشارات Forex الاحترافية
يدمج: ICT + Technical + AI + Risk Management
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd
import logging

from ict_engine import ICTEngine, ICTAnalysis
from tech_engine import TechEngine, TechAnalysis
from ai_predictor import AIPredictor, AIResult
from risk_manager import RiskManager, RiskParams, AccountInfo

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """إشارة تداول كاملة"""
    id: str
    symbol: str
    direction: str            # BUY / SELL
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    lot_size: float
    risk_reward: float
    risk_amount_usd: float

    # درجات التحليل
    ict_score: float
    tech_score: float
    ai_score: float
    total_score: float

    # تفاصيل ICT
    killzone: str
    fvg_type: Optional[str]
    ob_type: Optional[str]
    bos_choch: Optional[str]
    ict_bias: str

    # تفاصيل فنية
    ema_trend: str
    rsi: float
    macd_cross: str
    adx_strength: str

    # معلومات إضافية
    timeframe: str
    timestamp: datetime
    confidence: str           # HIGH / MEDIUM / LOW
    valid: bool
    rejection_reason: Optional[str]

    trailing_activation: float = 0.0
    trailing_distance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry": self.entry,
            "sl": self.stop_loss,
            "tp1": self.take_profit_1,
            "tp2": self.take_profit_2,
            "tp3": self.take_profit_3,
            "lot": self.lot_size,
            "rr": self.risk_reward,
            "risk_usd": self.risk_amount_usd,
            "ict_score": self.ict_score,
            "tech_score": self.tech_score,
            "ai_score": self.ai_score,
            "total_score": self.total_score,
            "killzone": self.killzone,
            "bias": self.ict_bias,
            "rsi": self.rsi,
            "confidence": self.confidence,
            "valid": self.valid,
            "rejection": self.rejection_reason,
            "timestamp": self.timestamp.isoformat(),
        }

    def format_telegram(self) -> str:
        """تنسيق الإشارة لـ Telegram"""
        emoji = "🟢" if self.direction == "BUY" else "🔴"
        conf_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "⚠️"}.get(self.confidence, "")

        return f"""
{emoji} <b>{self.direction} {self.symbol}</b> {conf_emoji}

📍 <b>Entry:</b> {self.entry}
🛑 <b>SL:</b> {self.stop_loss} ({self.risk_manager_data.get('sl_pips', '?')} pips)
🎯 <b>TP1:</b> {self.take_profit_1}
🎯 <b>TP2:</b> {self.take_profit_2}
🎯 <b>TP3:</b> {self.take_profit_3}

📊 <b>Lot:</b> {self.lot_size} | <b>Risk:</b> ${self.risk_amount_usd} | <b>RR:</b> 1:{self.risk_reward}

🕐 <b>Session:</b> {self.killzone}
📈 <b>ICT Score:</b> {self.ict_score:.0f}% | <b>Tech:</b> {self.tech_score:.0f}% | <b>AI:</b> {self.ai_score:.0f}%
🏆 <b>Total Score:</b> {self.total_score:.0f}%

🔍 <b>Setup:</b>
• Bias: {self.ict_bias}
• FVG: {self.fvg_type or 'None'}
• OB: {self.ob_type or 'None'}
• {self.bos_choch or 'No BOS/CHoCH'}
• EMA: {self.ema_trend}
• RSI: {self.rsi:.1f}
• ADX: {self.adx_strength}

⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}
"""


# ─────────────────────────────── Signal Builder ─────────────────────────────

class SignalBuilder:
    """
    مولّد الإشارات الرئيسي - يدمج كل المحركات

    شروط الإشارة الصارمة:
    ✅ Killzone نشط
    ✅ FVG موجود
    ✅ Order Block يتوافق
    ✅ BOS أو CHoCH مؤكد
    ✅ EMA يؤكد الاتجاه
    ✅ RSI بين 40-60
    ✅ AI Score > 65%
    """

    REQUIRED_CONDITIONS = [
        "killzone_active",
        "fvg_exists",
        "ob_exists",
        "bos_choch_exists",
        "ema_confirms",
        "rsi_ideal",
        "ai_score_ok",
    ]

    def __init__(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "H1",
        min_ai_score: float = 65.0,
        min_ict_score: float = 60.0,
        risk_pct: float = 1.0,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.min_ai_score = min_ai_score
        self.min_ict_score = min_ict_score

        self.ict = ICTEngine(symbol)
        self.tech = TechEngine()
        self.ai = AIPredictor()
        self.risk = RiskManager(risk_pct=risk_pct)

    def _check_conditions(
        self,
        ict: ICTAnalysis,
        tech: TechAnalysis,
        ai: AIResult,
    ) -> tuple[bool, list[str], list[str]]:
        """
        التحقق من جميع الشروط
        يرجع: (valid, met_conditions, failed_conditions)
        """
        met = []
        failed = []

        # 1. Killzone
        if ict.killzone_active:
            met.append(f"✅ Killzone: {ict.killzone_name}")
        else:
            failed.append(f"❌ Killzone: غير نشط")

        # 2. FVG
        if ict.fvg:
            met.append(f"✅ FVG: {ict.fvg['type']}")
        else:
            failed.append("❌ FVG: غير موجود")

        # 3. Order Block
        if ict.order_block:
            met.append(f"✅ OB: {ict.order_block['type']}")
        else:
            failed.append("❌ Order Block: غير موجود")

        # 4. BOS/CHoCH
        if ict.bos_choch:
            met.append(f"✅ {ict.bos_choch['type']}: {ict.bos_choch['direction']}")
        else:
            failed.append("❌ BOS/CHoCH: لا يوجد")

        # 5. EMA
        ema_ok = tech.ema_trend in ["BULLISH", "BEARISH"] and tech.ema_trend != "NEUTRAL"
        if ema_ok:
            met.append(f"✅ EMA: {tech.ema_trend}")
        else:
            failed.append(f"❌ EMA: {tech.ema_trend} - لا يؤكد")

        # 6. RSI 40-60
        rsi_ok = tech.rsi_signal == "NEUTRAL_IDEAL"
        if rsi_ok:
            met.append(f"✅ RSI: {tech.rsi:.1f} (نطاق مثالي)")
        else:
            failed.append(f"❌ RSI: {tech.rsi:.1f} ({tech.rsi_signal})")

        # 7. AI Score
        if ai.final_score >= self.min_ai_score:
            met.append(f"✅ AI Score: {ai.final_score:.1f}%")
        else:
            failed.append(f"❌ AI Score: {ai.final_score:.1f}% < {self.min_ai_score}%")

        all_met = len(failed) == 0
        return all_met, met, failed

    def _determine_direction(self, ict: ICTAnalysis, tech: TechAnalysis, ai: AIResult) -> str:
        """تحديد اتجاه الصفقة"""
        votes = {"BUY": 0, "SELL": 0}

        if ict.bias == "BULLISH":
            votes["BUY"] += 3
        elif ict.bias == "BEARISH":
            votes["SELL"] += 3

        if tech.ema_trend == "BULLISH":
            votes["BUY"] += 2
        elif tech.ema_trend == "BEARISH":
            votes["SELL"] += 2

        if ai.direction == "BUY":
            votes["BUY"] += 2
        elif ai.direction == "SELL":
            votes["SELL"] += 2

        if tech.plus_di > tech.minus_di:
            votes["BUY"] += 1
        else:
            votes["SELL"] += 1

        return "BUY" if votes["BUY"] >= votes["SELL"] else "SELL"

    def build(
        self,
        df: pd.DataFrame,
        account: AccountInfo,
        dt: Optional[datetime] = None,
    ) -> Signal:
        """بناء الإشارة الكاملة"""

        dt = dt or datetime.utcnow()
        entry_price = float(df.iloc[-1]["close"])

        # تشغيل جميع المحركات
        ict_result = self.ict.analyze(df, dt)
        tech_result = self.tech.analyze(df, ict_result.bias)
        ai_result = self.ai.predict(
            df,
            ict_result.ict_score,
            tech_result.tech_score,
            ict_result.bias,
            self.symbol,
        )

        # التحقق من الشروط
        valid, met, failed = self._check_conditions(ict_result, tech_result, ai_result)
        rejection = None if valid else f"الشروط الفاشلة: {'; '.join(failed)}"

        # تحديد الاتجاه
        direction = self._determine_direction(ict_result, tech_result, ai_result)

        # الدرجة الإجمالية
        total_score = (
            ict_result.ict_score * 0.35 +
            tech_result.tech_score * 0.30 +
            ai_result.final_score * 0.35
        )

        # إدارة المخاطر
        ob_level = None
        if ict_result.order_block:
            ob_level = (ict_result.order_block["top"] + ict_result.order_block["bottom"]) / 2

        risk_params = self.risk.calculate(
            account=account,
            entry=entry_price,
            direction=direction,
            atr=tech_result.atr,
            symbol=self.symbol,
            signal_score=total_score,
            ob_level=ob_level,
        )

        # معرّف فريد
        signal_id = f"{self.symbol}_{direction}_{dt.strftime('%Y%m%d%H%M%S')}"

        signal = Signal(
            id=signal_id,
            symbol=self.symbol,
            direction=direction,
            entry=entry_price,
            stop_loss=risk_params.stop_loss,
            take_profit_1=risk_params.take_profit_1,
            take_profit_2=risk_params.take_profit_2,
            take_profit_3=risk_params.take_profit_3,
            lot_size=risk_params.lot_size,
            risk_reward=risk_params.risk_reward,
            risk_amount_usd=risk_params.risk_amount_usd,
            ict_score=ict_result.ict_score,
            tech_score=tech_result.tech_score,
            ai_score=ai_result.final_score,
            total_score=total_score,
            killzone=ict_result.killzone_name,
            fvg_type=ict_result.fvg["type"] if ict_result.fvg else None,
            ob_type=ict_result.order_block["type"] if ict_result.order_block else None,
            bos_choch=f"{ict_result.bos_choch['type']} {ict_result.bos_choch['direction']}" if ict_result.bos_choch else None,
            ict_bias=ict_result.bias,
            ema_trend=tech_result.ema_trend,
            rsi=tech_result.rsi,
            macd_cross=tech_result.macd_cross,
            adx_strength=tech_result.adx_trend,
            timeframe=self.timeframe,
            timestamp=dt,
            confidence=ai_result.confidence,
            valid=valid,
            rejection_reason=rejection,
            trailing_activation=risk_params.trailing_activation,
            trailing_distance=risk_params.trailing_distance,
        )

        # حفظ بيانات risk للـ Telegram format
        signal.risk_manager_data = {
            "sl_pips": risk_params.sl_pips,
        }

        if valid:
            logger.info(f"✅ إشارة صالحة: {signal_id} | Score: {total_score:.1f}%")
        else:
            logger.info(f"⛔ إشارة مرفوضة: {signal_id} | {rejection}")

        return signal

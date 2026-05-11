"""
Risk Manager - إدارة المخاطر الذكية
حساب لوت تلقائي، SL/TP، Trailing Stop
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class RiskParams:
    lot_size: float
    stop_loss: float
    take_profit_1: float    # TP1: 1:1.5
    take_profit_2: float    # TP2: 1:2.5
    take_profit_3: float    # TP3: 1:4
    risk_reward: float
    risk_amount_usd: float
    pip_value: float
    sl_pips: float
    trailing_activation: float   # السعر الذي يبدأ عنده الـ Trailing
    trailing_distance: float     # مسافة الـ Trailing بالـ pips
    max_drawdown_pct: float      # الحد الأقصى للخسارة


@dataclass
class AccountInfo:
    balance: float
    equity: float
    currency: str = "USD"
    leverage: int = 100
    open_trades: int = 0
    daily_loss: float = 0.0


# ─────────────────────────────── Symbol Specs ──────────────────────────────

SYMBOL_SPECS = {
    "XAUUSD": {
        "pip_size": 0.01,
        "pip_value_per_lot": 1.0,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.01,
        "contract_size": 100,
        "spread": 0.3,
    },
    "EURUSD": {
        "pip_size": 0.0001,
        "pip_value_per_lot": 10.0,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.01,
        "contract_size": 100000,
        "spread": 0.8,
    },
    "GBPUSD": {
        "pip_size": 0.0001,
        "pip_value_per_lot": 10.0,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.01,
        "contract_size": 100000,
        "spread": 1.2,
    },
    "USDJPY": {
        "pip_size": 0.01,
        "pip_value_per_lot": 9.0,    # تقريبي
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.01,
        "contract_size": 100000,
        "spread": 0.5,
    },
}


class RiskManager:
    """إدارة المخاطر الذكية والمتكاملة"""

    def __init__(
        self,
        risk_pct: float = 1.0,          # نسبة المخاطرة من الرصيد
        max_risk_pct: float = 2.0,      # الحد الأقصى
        max_daily_loss_pct: float = 5.0, # أقصى خسارة يومية
        max_trades: int = 3,            # أقصى صفقات متزامنة
        rr_min: float = 1.5,            # أدنى نسبة مكافأة/مخاطرة
        trailing_rr: float = 1.0,       # تفعيل trailing عند 1:1
    ):
        self.risk_pct = risk_pct
        self.max_risk_pct = max_risk_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trades = max_trades
        self.rr_min = rr_min
        self.trailing_rr = trailing_rr

    # ─────────────────────────────── Lot Calculator ────────────────────────

    def calc_lot(
        self,
        account: AccountInfo,
        entry: float,
        sl: float,
        symbol: str,
        signal_score: float = 100.0,
    ) -> float:
        """
        حساب حجم اللوت بناءً على:
        - رصيد الحساب
        - مستوى Stop Loss
        - نسبة المخاطرة
        - قوة الإشارة
        """
        spec = SYMBOL_SPECS.get(symbol, SYMBOL_SPECS["EURUSD"])

        # تعديل نسبة المخاطرة حسب قوة الإشارة
        adjusted_risk = self.risk_pct
        if signal_score >= 85:
            adjusted_risk = min(self.risk_pct * 1.5, self.max_risk_pct)
        elif signal_score >= 70:
            adjusted_risk = self.risk_pct
        elif signal_score >= 65:
            adjusted_risk = self.risk_pct * 0.75
        else:
            adjusted_risk = self.risk_pct * 0.5

        # مبلغ المخاطرة بالدولار
        risk_amount = account.equity * (adjusted_risk / 100)

        # حساب المسافة بالـ pips
        sl_distance = abs(entry - sl)
        if sl_distance == 0:
            return spec["min_lot"]

        sl_pips = sl_distance / spec["pip_size"]

        # قيمة الـ pip لكل لوت
        pip_val = spec["pip_value_per_lot"]

        # حساب اللوت
        lot = risk_amount / (sl_pips * pip_val)

        # تقريب للـ lot_step
        step = spec["lot_step"]
        lot = math.floor(lot / step) * step

        # التحقق من الحدود
        lot = max(spec["min_lot"], min(lot, spec["max_lot"]))

        return round(lot, 2)

    # ─────────────────────────────── SL/TP Calculator ──────────────────────

    def calc_sl_tp(
        self,
        entry: float,
        direction: str,
        atr: float,
        symbol: str,
        ob_level: Optional[float] = None,
        fvg_level: Optional[float] = None,
    ) -> tuple[float, float, float, float]:
        """
        حساب SL/TP ديناميكي مع مراعاة ICT levels
        """
        spec = SYMBOL_SPECS.get(symbol, SYMBOL_SPECS["EURUSD"])

        # SL = 1.5x ATR من نقطة الدخول
        base_sl_distance = atr * 1.5

        if direction == "BUY":
            # SL تحت الدخول
            sl = entry - base_sl_distance

            # إذا وجد Order Block، استخدمه كـ SL
            if ob_level and ob_level < entry:
                sl = min(sl, ob_level - atr * 0.3)

            sl_distance = entry - sl
            tp1 = entry + sl_distance * 1.5
            tp2 = entry + sl_distance * 2.5
            tp3 = entry + sl_distance * 4.0

        else:  # SELL
            sl = entry + base_sl_distance

            if ob_level and ob_level > entry:
                sl = max(sl, ob_level + atr * 0.3)

            sl_distance = sl - entry
            tp1 = entry - sl_distance * 1.5
            tp2 = entry - sl_distance * 2.5
            tp3 = entry - sl_distance * 4.0

        return (
            round(sl, 5),
            round(tp1, 5),
            round(tp2, 5),
            round(tp3, 5),
        )

    # ─────────────────────────────── Trailing Stop ──────────────────────────

    def calc_trailing(
        self,
        entry: float,
        sl: float,
        direction: str,
        atr: float,
    ) -> tuple[float, float]:
        """
        حساب مستوى تفعيل Trailing Stop ومسافته
        """
        sl_distance = abs(entry - sl)

        if direction == "BUY":
            # تفعيل عند تحقيق 1:1
            activation = entry + sl_distance * self.trailing_rr
            trail_distance = atr * 0.8
        else:
            activation = entry - sl_distance * self.trailing_rr
            trail_distance = atr * 0.8

        return round(activation, 5), round(trail_distance, 5)

    # ─────────────────────────────── Risk Validation ───────────────────────

    def validate_trade(self, account: AccountInfo, risk_amount: float) -> tuple[bool, str]:
        """التحقق من صحة الصفقة وفق قواعد المخاطرة"""

        # التحقق من عدد الصفقات
        if account.open_trades >= self.max_trades:
            return False, f"تجاوز الحد الأقصى للصفقات ({self.max_trades})"

        # التحقق من الخسارة اليومية
        daily_loss_pct = (account.daily_loss / account.balance) * 100
        if daily_loss_pct >= self.max_daily_loss_pct:
            return False, f"تجاوز الحد الأقصى للخسارة اليومية ({self.max_daily_loss_pct}%)"

        # التحقق من نسبة المخاطرة
        risk_pct = (risk_amount / account.equity) * 100
        if risk_pct > self.max_risk_pct:
            return False, f"نسبة المخاطرة ({risk_pct:.1f}%) تتجاوز الحد الأقصى ({self.max_risk_pct}%)"

        # التحقق من Equity vs Balance
        if account.equity < account.balance * 0.80:
            return False, "تحذير: Equity أقل من 80% من الرصيد - تجنب فتح صفقات جديدة"

        return True, "OK"

    # ─────────────────────────────── Master Calculate ──────────────────────

    def calculate(
        self,
        account: AccountInfo,
        entry: float,
        direction: str,
        atr: float,
        symbol: str,
        signal_score: float,
        ob_level: Optional[float] = None,
        fvg_level: Optional[float] = None,
    ) -> RiskParams:
        """حساب كل معاملات المخاطرة دفعة واحدة"""

        sl, tp1, tp2, tp3 = self.calc_sl_tp(
            entry, direction, atr, symbol, ob_level, fvg_level
        )

        lot = self.calc_lot(account, entry, sl, symbol, signal_score)

        spec = SYMBOL_SPECS.get(symbol, SYMBOL_SPECS["EURUSD"])
        sl_pips = abs(entry - sl) / spec["pip_size"]
        pip_val = spec["pip_value_per_lot"]
        risk_amount = lot * sl_pips * pip_val

        rr = abs(tp2 - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0

        trail_activation, trail_distance = self.calc_trailing(entry, sl, direction, atr)

        return RiskParams(
            lot_size=lot,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=round(rr, 2),
            risk_amount_usd=round(risk_amount, 2),
            pip_value=pip_val,
            sl_pips=round(sl_pips, 1),
            trailing_activation=trail_activation,
            trailing_distance=trail_distance,
            max_drawdown_pct=self.max_daily_loss_pct,
        )

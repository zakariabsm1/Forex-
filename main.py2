"""
Forex Signals API - FastAPI Main
نظام إشارات فوركس احترافي متكامل
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from ict_engine import ICTEngine
from tech_engine import TechEngine
from ai_predictor import AIPredictor
from signal_builder import SignalBuilder
from risk_manager import RiskManager, AccountInfo
from notifier import Notifier, NotifierConfig
from mt5_bridge import MT5Bridge
from data_fetcher import fetch_candles, get_data_source

# ─────────────────────────────── Logging ───────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("forex_api")

# ─────────────────────────────── Config ────────────────────────────────────

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "changeme")
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "60"))

SUPPORTED_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD"]
SUPPORTED_TIMEFRAMES = ["M15", "H1", "H4", "D1"]

# ─────────────────────────────── Global State ──────────────────────────────

app_state: dict = {
    "notifier": None,
    "mt5_bridge": None,
    "signal_cache": {},
    "signal_history": [],
    "stats": {
        "total_signals": 0,
        "valid_signals": 0,
        "executed_trades": 0,
        "start_time": datetime.now(timezone.utc).isoformat(),
    }
}

# ─────────────────────────────── Lifespan ──────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 بدء تشغيل Forex Signals API...")

    config = NotifierConfig.from_env()
    app_state["notifier"] = Notifier(config)

    bridge = MT5Bridge.from_env()
    connected = await bridge.connect()
    app_state["mt5_bridge"] = bridge

    if connected:
        logger.info("✅ متصل بـ MT5")
    else:
        logger.warning("⚠️ MT5 غير متصل - وضع المحاكاة")

    logger.info("✅ التطبيق جاهز")
    yield

    logger.info("🛑 إيقاف التطبيق...")
    await app_state["notifier"].close()
    await bridge.disconnect()


# ─────────────────────────────── FastAPI App ───────────────────────────────

app = FastAPI(
    title="Forex Signals API",
    description="نظام إشارات فوركس احترافي بتحليل ICT + AI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────── Models ────────────────────────────────────

class SignalRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "H1"
    account_balance: float = 10000.0
    account_equity: float = 10000.0
    open_trades: int = 0
    risk_pct: float = 1.0
    auto_execute: bool = False

class WebhookPayload(BaseModel):
    secret: str
    action: str        # signal / close / modify
    symbol: Optional[str] = None
    data: Optional[dict] = None

# ─────────────────────────────── Data Fetcher ──────────────────────────────

# ─── البيانات تُجلب من data_fetcher.py ────────────────────────────────────
# الأولوية: Twelve Data → Alpha Vantage → Yahoo Finance → Demo
# لا حاجة لأي كود هنا — fetch_candles() تتولى كل شيء تلقائياً

# ─────────────────────────────── Endpoints ─────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """الصفحة الرئيسية"""
    return """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<title>Forex Signals API</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.card { background: #1e293b; border-radius: 16px; padding: 40px; max-width: 600px; width: 90%; text-align: center; border: 1px solid #334155; }
h1 { font-size: 2rem; background: linear-gradient(135deg, #22d3ee, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }
.badge { display: inline-block; background: #22c55e22; color: #22c55e; border: 1px solid #22c55e44; padding: 4px 12px; border-radius: 20px; font-size: 13px; margin-bottom: 24px; }
.links { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 24px; }
a { background: #0f172a; border: 1px solid #334155; color: #94a3b8; padding: 12px; border-radius: 8px; text-decoration: none; transition: all 0.2s; }
a:hover { border-color: #818cf8; color: #818cf8; }
</style>
</head>
<body>
<div class="card">
  <h1>📈 Forex Signals API</h1>
  <div class="badge">🟢 Running</div>
  <p style="color:#64748b">نظام إشارات فوركس بتحليل ICT + AI احترافي</p>
  <div class="links">
    <a href="/docs">📖 API Docs</a>
    <a href="/health">❤️ Health</a>
    <a href="/api/stats">📊 Stats</a>
    <a href="/api/signals/history">🕐 History</a>
  </div>
</div>
</body>
</html>
"""


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": get_data_source(),
        "mt5_connected": app_state["mt5_bridge"]._connected if app_state.get("mt5_bridge") else False,
        "version": "2.1.0",
    }


@app.get("/api/stats")
async def get_stats():
    return app_state["stats"]


@app.post("/api/signal")
async def generate_signal(
    req: SignalRequest,
    background: BackgroundTasks,
):
    """توليد إشارة تداول كاملة"""

    if req.symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, f"رمز غير مدعوم. الرموز المتاحة: {SUPPORTED_SYMBOLS}")

    if req.timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(400, f"إطار زمني غير مدعوم. المتاح: {SUPPORTED_TIMEFRAMES}")

    # جلب البيانات (Twelve Data → Alpha Vantage → Yahoo → Demo)
    df = await fetch_candles(req.symbol, req.timeframe)

    # إعداد الحساب
    account = AccountInfo(
        balance=req.account_balance,
        equity=req.account_equity,
        open_trades=req.open_trades,
    )

    # بناء الإشارة
    builder = SignalBuilder(
        symbol=req.symbol,
        timeframe=req.timeframe,
        risk_pct=req.risk_pct,
    )

    signal = builder.build(df, account)
    signal_dict = signal.to_dict()

    # تحديث الإحصائيات
    app_state["stats"]["total_signals"] += 1
    if signal.valid:
        app_state["stats"]["valid_signals"] += 1

    # حفظ في السجل
    app_state["signal_history"].append(signal_dict)
    if len(app_state["signal_history"]) > 100:
        app_state["signal_history"].pop(0)

    # إشعارات وتنفيذ في الخلفية
    if signal.valid:
        background.add_task(
            _process_valid_signal,
            signal,
            signal_dict,
            req.auto_execute,
        )

    return {
        "success": True,
        "signal": signal_dict,
        "conditions_met": signal.valid,
        "message": "إشارة صالحة ✅" if signal.valid else f"الشروط غير مكتملة ⛔: {signal.rejection_reason}",
    }


async def _process_valid_signal(signal, signal_dict: dict, auto_execute: bool):
    """معالجة الإشارة الصالحة في الخلفية"""
    notifier: Notifier = app_state["notifier"]
    bridge: MT5Bridge = app_state["mt5_bridge"]

    # إرسال الإشعارات
    try:
        telegram_text = signal.format_telegram()
        await notifier.send_signal(signal_dict, telegram_text)
    except AttributeError:
        # إذا لم تكن دالة format_telegram موجودة
        pass

    # تنفيذ تلقائي
    if auto_execute and bridge:
        response = await bridge.execute_signal(signal_dict)
        if response.success:
            app_state["stats"]["executed_trades"] += 1
            logger.info(f"✅ تم تنفيذ الصفقة: {response.ticket}")


@app.get("/api/signals/history")
async def signals_history(limit: int = 20):
    history = app_state["signal_history"][-limit:]
    return {"count": len(history), "signals": list(reversed(history))}


@app.post("/api/webhook")
async def webhook_router(payload: WebhookPayload, background: BackgroundTasks):
    """
    Webhook Router - يستقبل إشارات من TradingView أو مصادر خارجية
    """
    if payload.secret != WEBHOOK_SECRET:
        raise HTTPException(403, "Secret غير صحيح")

    action = payload.action.lower()

    if action == "signal" and payload.data:
        background.add_task(_handle_external_signal, payload.data)
        return {"status": "queued", "action": action}

    elif action == "close":
        return {"status": "ok", "action": "close", "data": payload.data}

    elif action == "status":
        return {"status": "ok", "stats": app_state["stats"]}

    raise HTTPException(400, f"action غير معروف: {action}")


async def _handle_external_signal(data: dict):
    """معالجة إشارة خارجية من Webhook"""
    logger.info(f"📥 Webhook signal: {data}")
    notifier: Notifier = app_state["notifier"]
    msg = f"📥 <b>Webhook Signal</b>\n{str(data)[:500]}"
    await notifier.send_telegram(msg)


@app.get("/api/analyze/{symbol}")
async def analyze_symbol(symbol: str, timeframe: str = "H1"):
    """تحليل رمز دون توليد إشارة"""
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, f"رمز غير مدعوم")

    df = await fetch_candles(symbol, timeframe)

    ict = ICTEngine(symbol)
    tech = TechEngine()
    ai = AIPredictor()

    ict_result = ict.analyze(df)
    tech_result = tech.analyze(df, ict_result.bias)
    ai_result = ai.predict(df, ict_result.ict_score, tech_result.tech_score, ict_result.bias, symbol)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ict": {
            "killzone": {"active": ict_result.killzone_active, "name": ict_result.killzone_name},
            "fvg": ict_result.fvg,
            "order_block": ict_result.order_block,
            "bos_choch": ict_result.bos_choch,
            "liquidity_sweep": ict_result.liquidity_sweep,
            "bias": ict_result.bias,
            "score": ict_result.ict_score,
        },
        "technical": {
            "ema_trend": tech_result.ema_trend,
            "rsi": round(tech_result.rsi, 2),
            "rsi_signal": tech_result.rsi_signal,
            "macd_cross": tech_result.macd_cross,
            "adx": round(tech_result.adx, 2),
            "adx_trend": tech_result.adx_trend,
            "atr": round(tech_result.atr, 5),
            "score": tech_result.tech_score,
        },
        "ai": {
            "rf_score": ai_result.rf_score,
            "lstm_score": ai_result.lstm_score,
            "sentiment_score": ai_result.sentiment_score,
            "final_score": ai_result.final_score,
            "direction": ai_result.direction,
            "confidence": ai_result.confidence,
        },
    }


# ─────────────────────────────── Run ───────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

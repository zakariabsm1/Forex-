"""
Data Fetcher - جلب البيانات من مصادر متعددة
الأولوية: Twelve Data → Alpha Vantage → Yahoo Finance → Demo
جميعها تدعم الجزائر ومجانية
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
import pandas as pd

logger = logging.getLogger("data_fetcher")

# ─────────────────────────────── Config ────────────────────────────────────

TWELVE_DATA_KEY   = os.getenv("TWELVE_DATA_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# تحويل الرموز لكل مصدر
TWELVE_SYMBOLS = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "GBPJPY": "GBP/JPY",
    "AUDUSD": "AUD/USD",
}

ALPHA_SYMBOLS = {
    "XAUUSD": ("XAU", "USD"),
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "GBPJPY": ("GBP", "JPY"),
    "AUDUSD": ("AUD", "USD"),
}

YAHOO_SYMBOLS = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "GBPJPY": "GBPJPY=X",
    "AUDUSD": "AUDUSD=X",
}

TWELVE_TF = {"M15": "15min", "H1": "1h", "H4": "4h", "D1": "1day"}
ALPHA_TF  = {"M15": "15min", "H1": "60min", "H4": "60min", "D1": "daily"}


# ═══════════════════════════════════════════════════════
#  1. TWELVE DATA
# ═══════════════════════════════════════════════════════

async def fetch_twelve_data(symbol: str, timeframe: str, count: int = 300) -> pd.DataFrame | None:
    """
    Twelve Data API - مجاني 800 طلب/يوم
    سجّل على: twelvedata.com
    """
    if not TWELVE_DATA_KEY:
        return None

    td_symbol = TWELVE_SYMBOLS.get(symbol)
    td_tf     = TWELVE_TF.get(timeframe, "1h")

    if not td_symbol:
        return None

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol":     td_symbol,
        "interval":   td_tf,
        "outputsize": min(count, 5000),
        "apikey":     TWELVE_DATA_KEY,
        "format":     "JSON",
        "order":      "ASC",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "error":
            logger.warning(f"Twelve Data خطأ: {data.get('message')}")
            return None

        values = data.get("values", [])
        if not values:
            return None

        rows = []
        for v in values:
            rows.append({
                "timestamp": v["datetime"],
                "open":   float(v["open"]),
                "high":   float(v["high"]),
                "low":    float(v["low"]),
                "close":  float(v["close"]),
                "volume": float(v.get("volume", 0)),
            })

        df = pd.DataFrame(rows)
        logger.info(f"✅ Twelve Data: {len(df)} شمعة لـ {symbol} ({timeframe})")
        return df

    except Exception as e:
        logger.warning(f"⚠️ Twelve Data فشل: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  2. ALPHA VANTAGE
# ═══════════════════════════════════════════════════════

async def fetch_alpha_vantage(symbol: str, timeframe: str, count: int = 300) -> pd.DataFrame | None:
    """
    Alpha Vantage - مجاني 25 طلب/يوم
    سجّل على: alphavantage.co
    """
    if not ALPHA_VANTAGE_KEY:
        return None

    pair = ALPHA_SYMBOLS.get(symbol)
    tf   = ALPHA_TF.get(timeframe, "60min")

    if not pair:
        return None

    from_sym, to_sym = pair

    # اختيار الدالة المناسبة
    if timeframe == "D1":
        func    = "FX_DAILY"
        params  = {
            "function":    func,
            "from_symbol": from_sym,
            "to_symbol":   to_sym,
            "outputsize":  "full",
            "apikey":      ALPHA_VANTAGE_KEY,
        }
        key_name = "Time Series FX (Daily)"
    else:
        func    = "FX_INTRADAY"
        params  = {
            "function":    func,
            "from_symbol": from_sym,
            "to_symbol":   to_sym,
            "interval":    tf,
            "outputsize":  "full",
            "apikey":      ALPHA_VANTAGE_KEY,
        }
        key_name = f"Time Series FX ({tf})"

    # للذهب نستخدم COMMODITY
    if symbol == "XAUUSD":
        params = {
            "function":   "COMMODITY_EXCHANGE_RATE",
            "from_symbol": "XAU",
            "to_symbol":   "USD",
            "apikey":      ALPHA_VANTAGE_KEY,
        }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get("https://www.alphavantage.co/query", params=params)
            resp.raise_for_status()
            data = resp.json()

        ts = data.get(key_name, {})
        if not ts:
            logger.warning(f"Alpha Vantage: لا بيانات لـ {symbol}")
            return None

        rows = []
        for dt_str, vals in sorted(ts.items()):
            rows.append({
                "timestamp": dt_str,
                "open":   float(vals.get("1. open",  vals.get("open",  0))),
                "high":   float(vals.get("2. high",  vals.get("high",  0))),
                "low":    float(vals.get("3. low",   vals.get("low",   0))),
                "close":  float(vals.get("4. close", vals.get("close", 0))),
                "volume": float(vals.get("5. volume", 0)),
            })

        df = pd.DataFrame(rows).tail(count)
        logger.info(f"✅ Alpha Vantage: {len(df)} شمعة لـ {symbol}")
        return df

    except Exception as e:
        logger.warning(f"⚠️ Alpha Vantage فشل: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  3. YAHOO FINANCE (بدون مفتاح)
# ═══════════════════════════════════════════════════════

async def fetch_yahoo(symbol: str, timeframe: str, count: int = 300) -> pd.DataFrame | None:
    """
    Yahoo Finance - مجاني بدون تسجيل
    بيانات مؤخرة 15 دقيقة
    """
    yh_symbol = YAHOO_SYMBOLS.get(symbol)
    if not yh_symbol:
        return None

    # تحويل الإطار الزمني
    tf_map = {
        "M15": ("15m",  "5d"),
        "H1":  ("1h",   "30d"),
        "H4":  ("1h",   "60d"),   # Yahoo لا يدعم 4h مباشرة
        "D1":  ("1d",   "2y"),
    }
    interval, period = tf_map.get(timeframe, ("1h", "30d"))

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yh_symbol}"
    params = {
        "interval": interval,
        "range":    period,
        "includePrePost": "false",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        ohlcv = result["indicators"]["quote"][0]

        rows = []
        for i, ts in enumerate(timestamps):
            o = ohlcv["open"][i]
            h = ohlcv["high"][i]
            l = ohlcv["low"][i]
            c = ohlcv["close"][i]
            v = ohlcv.get("volume", [0] * len(timestamps))[i]
            if None in (o, h, l, c):
                continue
            rows.append({
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "open":  float(o),
                "high":  float(h),
                "low":   float(l),
                "close": float(c),
                "volume": float(v or 0),
            })

        df = pd.DataFrame(rows).tail(count)
        logger.info(f"✅ Yahoo Finance: {len(df)} شمعة لـ {symbol}")
        return df

    except Exception as e:
        logger.warning(f"⚠️ Yahoo Finance فشل: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  4. DEMO DATA (الاحتياطي الأخير)
# ═══════════════════════════════════════════════════════

def generate_demo_data(symbol: str, count: int = 300) -> pd.DataFrame:
    """بيانات تجريبية واقعية عند فشل جميع المصادر"""
    bases = {
        "XAUUSD": 2320.0,
        "EURUSD": 1.0850,
        "GBPUSD": 1.2700,
        "USDJPY": 154.50,
        "GBPJPY": 196.00,
        "AUDUSD": 0.6550,
    }
    base = bases.get(symbol, 1.0)
    np.random.seed(abs(hash(symbol)) % 2**31)

    returns = np.random.normal(0.0001, 0.0015, count)
    prices  = base * np.exp(np.cumsum(returns))
    highs   = prices * (1 + np.abs(np.random.normal(0, 0.0008, count)))
    lows    = prices * (1 - np.abs(np.random.normal(0, 0.0008, count)))
    opens   = np.roll(prices, 1); opens[0] = prices[0]
    volumes = np.random.randint(100, 10000, count)

    start = datetime.now(timezone.utc) - timedelta(hours=count)
    ts    = [(start + timedelta(hours=i)).isoformat() for i in range(count)]

    logger.warning(f"⚠️ [{symbol}] استخدام بيانات تجريبية — أضف API Key للبيانات الحقيقية")
    return pd.DataFrame({
        "timestamp": ts, "open": opens, "high": highs,
        "low": lows, "close": prices, "volume": volumes,
    })


# ═══════════════════════════════════════════════════════
#  MASTER FETCHER - يجرب بالترتيب تلقائياً
# ═══════════════════════════════════════════════════════

async def fetch_candles(symbol: str, timeframe: str = "H1", count: int = 300) -> pd.DataFrame:
    """
    جلب البيانات بالأولوية:
    1. Twelve Data  (أفضل - 800 طلب/يوم مجاناً)
    2. Alpha Vantage (جيد  - 25 طلب/يوم مجاناً)
    3. Yahoo Finance (مقبول - بدون مفتاح، مؤخر 15د)
    4. Demo Data     (احتياطي - للاختبار فقط)
    """

    # 1. Twelve Data
    if TWELVE_DATA_KEY:
        df = await fetch_twelve_data(symbol, timeframe, count)
        if df is not None and len(df) >= 50:
            return df

    # 2. Alpha Vantage
    if ALPHA_VANTAGE_KEY:
        df = await fetch_alpha_vantage(symbol, timeframe, count)
        if df is not None and len(df) >= 50:
            return df

    # 3. Yahoo Finance (بدون مفتاح)
    df = await fetch_yahoo(symbol, timeframe, count)
    if df is not None and len(df) >= 50:
        return df

    # 4. Demo (احتياطي)
    return generate_demo_data(symbol, count)


def get_data_source() -> str:
    """إرجاع المصدر النشط حالياً"""
    if TWELVE_DATA_KEY:
        return "Twelve Data ✅"
    if ALPHA_VANTAGE_KEY:
        return "Alpha Vantage ✅"
    return "Yahoo Finance (بدون مفتاح)"

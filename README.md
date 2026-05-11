# 📈 Forex Signals Bot - دليل التثبيت الكامل

نظام إشارات فوركس احترافي بتحليل **ICT + AI** مع تنفيذ تلقائي عبر MT5

---

## ✨ المميزات

| الميزة | التفاصيل |
|--------|----------|
| 🧠 تحليل ICT | Killzone, FVG, Order Blocks, BOS/CHoCH, Liquidity Sweeps |
| 📊 تحليل فني | EMA (21/50/200), RSI, MACD, ATR, ADX |
| 🤖 ذكاء اصطناعي | Random Forest + LSTM + Sentiment Analysis |
| 📱 إشعارات | Telegram + Push (ntfy.sh) + Email |
| ⚡ تنفيذ تلقائي | MT5 عبر ZeroMQ |
| 🔒 إدارة مخاطر | حساب لوت تلقائي، SL/TP ديناميكي، Trailing Stop |

---

## 🚀 خطوات النشر على Railway.app

### 1. تهيئة المستودع

```bash
git init
git add .
git commit -m "Initial: Forex Signals Bot"
```

### 2. رفع إلى GitHub

```bash
gh repo create forex-signals-bot --public
git remote add origin https://github.com/YOUR_USER/forex-signals-bot
git push -u origin main
```

### 3. النشر على Railway

1. اذهب إلى [railway.app](https://railway.app)
2. اضغط **New Project → Deploy from GitHub**
3. اختر مستودع `forex-signals-bot`
4. أضف المتغيرات البيئية (انظر القسم التالي)
5. سيبدأ البناء تلقائياً ✅

---

## 🔧 المتغيرات البيئية

أضف هذه المتغيرات في Railway Dashboard → Variables:

```env
# ─── Telegram ───────────────────────────────────
TELEGRAM_BOT_TOKEN=1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_ENABLED=true

# ─── OANDA API (للبيانات الحية) ─────────────────
# سجّل مجاناً: https://www.oanda.com/forex-trading/
OANDA_API_KEY=your_oanda_practice_api_key
OANDA_ACCOUNT_ID=your_account_id

# ─── MT5 Bridge (اختياري) ───────────────────────
MT5_HOST=your_server_ip
MT5_PUSH_PORT=32768
MT5_PULL_PORT=32769
MT5_TIMEOUT_MS=5000

# ─── Email (اختياري) ─────────────────────────────
EMAIL_ENABLED=false
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app_specific_password
EMAIL_TO=recipient@email.com

# ─── Push Notifications ──────────────────────────
PUSH_ENABLED=true
PUSH_TOPIC=my-forex-signals-unique-topic

# ─── Security ─────────────────────────────────────
WEBHOOK_SECRET=your_strong_secret_here_min_16_chars
```

---

## 📲 إعداد Telegram Bot

```
1. ابحث عن @BotFather في Telegram
2. أرسل: /newbot
3. اختر اسماً ومعرفاً للبوت
4. احفظ التوكن (TELEGRAM_BOT_TOKEN)

للحصول على CHAT_ID:
1. أضف البوت إلى مجموعتك
2. أرسل أي رسالة في المجموعة
3. افتح: https://api.telegram.org/bot{TOKEN}/getUpdates
4. ابحث عن "chat":{"id": -1001XXXXXXX}
```

---

## 🖥️ تثبيت MT5 Bridge (للتنفيذ التلقائي)

### 1. تثبيت مكتبة ZeroMQ في MT5

```
1. افتح MetaTrader 5
2. Tools → Options → Expert Advisors
   ✅ Allow automated trading
   ✅ Allow DLL imports

3. حمّل Zmq.mqh من:
   https://github.com/dingmaotu/mql-zmq/releases
   
4. انسخ الملفات:
   Zmq.mqh  → MQL5\Include\Zmq\
   libzmq.dll → MQL5\Libraries\
```

### 2. تثبيت EA

```
1. انسخ mt5/mt5_zmq_bridge.mq5 إلى:
   C:\Users\...\AppData\Roaming\MetaQuotes\Terminal\...\MQL5\Experts\

2. في MT5: اضغط F4 (MetaEditor) → Compile

3. افتح أي رسمة بيانية
4. اسحب EA على الرسمة
5. تأكد أن الإعدادات:
   - Allow Automated Trading: ✅
   - Push Port: 32768
   - Pull Port: 32769
```

---

## 🐳 تشغيل محلي بـ Docker

```bash
# نسخ ملف البيئة
cp .env.example .env
# عدّل القيم في .env

# تشغيل
docker-compose up -d

# متابعة السجلات
docker-compose logs -f

# إيقاف
docker-compose down
```

---

## 📡 استخدام API

### توليد إشارة

```bash
curl -X POST https://your-app.railway.app/api/signal \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "account_balance": 10000,
    "account_equity": 10000,
    "risk_pct": 1.0,
    "auto_execute": false
  }'
```

### تحليل بدون إشارة

```bash
curl https://your-app.railway.app/api/analyze/XAUUSD?timeframe=H1
```

### Webhook من TradingView

```bash
# في TradingView Alert → Webhook URL
https://your-app.railway.app/api/webhook

# Webhook Body
{
  "secret": "your_webhook_secret",
  "action": "signal",
  "symbol": "XAUUSD",
  "data": {
    "source": "tradingview",
    "alert": "{{strategy.order.action}}"
  }
}
```

### الإحصائيات

```bash
curl https://your-app.railway.app/api/stats
```

---

## 📐 شروط الإشارة الصارمة

الإشارة تُعطى **فقط** عند توفر **جميع** الشروط التالية:

```
✅ Killzone نشط (London/NY/Asian)
✅ FVG موجود (Bullish أو Bearish)
✅ Order Block متوافق مع FVG
✅ BOS أو CHoCH مؤكد
✅ EMA (21/50/200) يؤكد الاتجاه
✅ RSI في النطاق المثالي (40-60)
✅ AI Score > 65%
```

---

## 📁 هيكل الملفات

```
forex_signals/
├── main.py              ← FastAPI الرئيسي
├── ict_engine.py        ← تحليل ICT
├── tech_engine.py       ← تحليل فني
├── ai_predictor.py      ← ذكاء اصطناعي
├── signal_builder.py    ← بناء الإشارات
├── risk_manager.py      ← إدارة المخاطر
├── notifier.py          ← الإشعارات
├── mt5_bridge.py        ← جسر MT5/ZMQ
├── mt5/
│   └── mt5_zmq_bridge.mq5  ← EA للـ MT5
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── railway.toml
```

---

## 🔄 خارطة تدفق الإشارة

```
بيانات OANDA
     ↓
ICT Engine (Killzone + FVG + OB + BOS + Liquidity)
     ↓
Tech Engine (EMA + RSI + MACD + ATR + ADX)
     ↓
AI Predictor (Random Forest + LSTM + Sentiment)
     ↓
Signal Builder (شروط صارمة: 7 شروط مجتمعة)
     ↓
Risk Manager (Lot + SL/TP + Trailing)
     ↓
├── Notifier → Telegram + Push + Email
└── MT5 Bridge → ZeroMQ → تنفيذ تلقائي
```

---

## ⚠️ تنبيهات مهمة

> **هذا النظام للأغراض التعليمية والبحثية**
> 
> - التداول الفوري ينطوي على مخاطر عالية
> - اختبر دائماً على حساب تجريبي (Demo) أولاً
> - لا تستخدم أموالاً لا تستطيع تحمل خسارتها
> - الأداء السابق لا يضمن الأداء المستقبلي

---

## 🛠️ استكشاف الأخطاء

| المشكلة | الحل |
|---------|------|
| Telegram لا يرسل | تحقق من TOKEN و CHAT_ID |
| OANDA خطأ 401 | تحقق من صحة API Key والبيئة (Practice/Live) |
| MT5 لا يتصل | تأكد أن EA يعمل وZMQ مثبت |
| Railway crash | راجع logs: `railway logs` |
| بيانات تجريبية | إذا كان OANDA_API_KEY فارغاً يستخدم بيانات تجريبية |

---

*Made with ❤️ — Forex Signals Bot v2.0*

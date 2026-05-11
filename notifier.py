"""
Notifier - نظام الإشعارات الفوري
Telegram + Email + Push Notifications
"""

import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional
import httpx
import os

logger = logging.getLogger(__name__)


@dataclass
class NotifierConfig:
    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = True

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""
    email_enabled: bool = True

    # Push (ntfy.sh - مجاني)
    push_topic: str = ""
    push_enabled: bool = True

    @classmethod
    def from_env(cls) -> "NotifierConfig":
        return cls(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            telegram_enabled=os.getenv("TELEGRAM_ENABLED", "true").lower() == "true",
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            email_to=os.getenv("EMAIL_TO", ""),
            email_enabled=os.getenv("EMAIL_ENABLED", "false").lower() == "true",
            push_topic=os.getenv("PUSH_TOPIC", "forex-signals"),
            push_enabled=os.getenv("PUSH_ENABLED", "true").lower() == "true",
        )


class Notifier:
    """مدير الإشعارات المتكامل"""

    def __init__(self, config: NotifierConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ─────────────────────────────── Telegram ──────────────────────────────

    async def send_telegram(self, message: str, parse_mode: str = "HTML") -> bool:
        if not self.config.telegram_enabled or not self.config.telegram_token:
            return False

        url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            client = await self._get_client()
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("✅ Telegram: تم الإرسال")
            return True
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
            return False

    async def send_telegram_photo(self, photo_url: str, caption: str) -> bool:
        """إرسال صورة مع تعليق"""
        if not self.config.telegram_enabled or not self.config.telegram_token:
            return False

        url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendPhoto"
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        }

        try:
            client = await self._get_client()
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"❌ Telegram Photo error: {e}")
            return False

    # ─────────────────────────────── Email ─────────────────────────────────

    async def send_email(self, subject: str, body: str, html: bool = True) -> bool:
        if not self.config.email_enabled or not self.config.smtp_user:
            return False

        def _send():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.smtp_user
            msg["To"] = self.config.email_to

            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)

        try:
            await asyncio.get_event_loop().run_in_executor(None, _send)
            logger.info("✅ Email: تم الإرسال")
            return True
        except Exception as e:
            logger.error(f"❌ Email error: {e}")
            return False

    def _format_email_html(self, signal_dict: dict) -> str:
        """تنسيق HTML للبريد الإلكتروني"""
        direction = signal_dict.get("direction", "")
        color = "#22c55e" if direction == "BUY" else "#ef4444"

        return f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
.card {{ max-width: 600px; margin: 20px auto; background: #1e293b; border-radius: 12px; padding: 24px; }}
.badge {{ display: inline-block; background: {color}; color: white; padding: 4px 16px; border-radius: 20px; font-weight: bold; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }}
.metric {{ background: #0f172a; border-radius: 8px; padding: 12px; text-align: center; }}
.metric-label {{ font-size: 12px; color: #64748b; }}
.metric-value {{ font-size: 20px; font-weight: bold; color: #f1f5f9; }}
</style>
</head>
<body>
<div class="card">
  <h2><span class="badge">{direction}</span> {signal_dict.get('symbol', '')}</h2>
  <div class="grid">
    <div class="metric"><div class="metric-label">Entry</div><div class="metric-value">{signal_dict.get('entry', '')}</div></div>
    <div class="metric"><div class="metric-label">Stop Loss</div><div class="metric-value" style="color:#ef4444">{signal_dict.get('sl', '')}</div></div>
    <div class="metric"><div class="metric-label">TP1</div><div class="metric-value" style="color:#22c55e">{signal_dict.get('tp1', '')}</div></div>
    <div class="metric"><div class="metric-label">TP2</div><div class="metric-value" style="color:#22c55e">{signal_dict.get('tp2', '')}</div></div>
    <div class="metric"><div class="metric-label">Lot</div><div class="metric-value">{signal_dict.get('lot', '')}</div></div>
    <div class="metric"><div class="metric-label">AI Score</div><div class="metric-value">{signal_dict.get('ai_score', '')}%</div></div>
  </div>
  <p style="color:#64748b;font-size:12px">{signal_dict.get('timestamp', '')}</p>
</div>
</body>
</html>
"""

    # ─────────────────────────────── Push (ntfy.sh) ─────────────────────────

    async def send_push(self, title: str, message: str, priority: str = "high") -> bool:
        """
        إشعار Push عبر ntfy.sh (مجاني)
        """
        if not self.config.push_enabled or not self.config.push_topic:
            return False

        url = f"https://ntfy.sh/{self.config.push_topic}"
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": "chart_with_upwards_trend",
        }

        try:
            client = await self._get_client()
            resp = await client.post(url, content=message.encode(), headers=headers)
            resp.raise_for_status()
            logger.info("✅ Push: تم الإرسال")
            return True
        except Exception as e:
            logger.error(f"❌ Push error: {e}")
            return False

    # ─────────────────────────────── Master Send ───────────────────────────

    async def send_signal(self, signal_dict: dict, telegram_text: str) -> dict:
        """إرسال الإشارة عبر جميع القنوات"""
        results = {}

        # إرسال متوازي
        tasks = []

        if self.config.telegram_enabled:
            tasks.append(("telegram", self.send_telegram(telegram_text)))

        if self.config.email_enabled:
            html = self._format_email_html(signal_dict)
            subject = f"🚨 إشارة {signal_dict.get('direction', '')} {signal_dict.get('symbol', '')} - Score: {signal_dict.get('total_score', '')}%"
            tasks.append(("email", self.send_email(subject, html)))

        if self.config.push_enabled:
            push_msg = f"{signal_dict.get('direction', '')} {signal_dict.get('symbol', '')} @ {signal_dict.get('entry', '')} | SL: {signal_dict.get('sl', '')} | TP: {signal_dict.get('tp2', '')}"
            tasks.append(("push", self.send_push(
                f"Forex Signal: {signal_dict.get('direction', '')} {signal_dict.get('symbol', '')}",
                push_msg
            )))

        # تنفيذ متوازي
        for name, coro in tasks:
            try:
                results[name] = await coro
            except Exception as e:
                results[name] = False
                logger.error(f"خطأ في إرسال {name}: {e}")

        logger.info(f"📤 نتائج الإشعارات: {results}")
        return results

    async def send_alert(self, title: str, message: str) -> None:
        """إرسال تنبيه عام"""
        full_msg = f"⚠️ <b>{title}</b>\n\n{message}"
        await self.send_telegram(full_msg)
        await self.send_push(title, message, priority="urgent")

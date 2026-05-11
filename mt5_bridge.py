"""
MT5 Bridge - جسر MetaTrader 5 عبر ZeroMQ
يرسل الأوامر إلى MT5 EA ويستقبل النتائج
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional
import os

logger = logging.getLogger(__name__)

try:
    import zmq
    import zmq.asyncio
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    logger.warning("⚠️ ZeroMQ غير متاح - وضع المحاكاة")


@dataclass
class MT5Order:
    """أمر تداول لـ MT5"""
    action: str          # OPEN / CLOSE / MODIFY
    symbol: str
    order_type: str      # BUY / SELL / BUY_STOP / SELL_STOP
    lot: float
    price: float
    sl: float
    tp: float
    comment: str = "ForexSignals-Bot"
    magic: int = 123456
    deviation: int = 20  # slippage بالـ points


@dataclass
class MT5Response:
    success: bool
    ticket: Optional[int]
    message: str
    price_executed: Optional[float]
    error_code: Optional[int]


class MT5Bridge:
    """
    جسر ZeroMQ للتواصل مع MT5 EA
    
    يتطلب تثبيت EA في MetaTrader 5 يستمع على نفس المنفذ
    ملف EA: mt5_zmq_ea.mq5 (مرفق في مجلد mt5/)
    """

    def __init__(
        self,
        host: str = "localhost",
        push_port: int = 32768,    # Python → MT5
        pull_port: int = 32769,    # MT5 → Python
        timeout_ms: int = 5000,
    ):
        self.host = host
        self.push_port = push_port
        self.pull_port = pull_port
        self.timeout_ms = timeout_ms
        self._context = None
        self._push_socket = None
        self._pull_socket = None
        self._connected = False

    async def connect(self) -> bool:
        """الاتصال بـ MT5 عبر ZeroMQ"""
        if not ZMQ_AVAILABLE:
            logger.warning("ZMQ غير متاح - وضع المحاكاة")
            return False

        try:
            self._context = zmq.asyncio.Context()

            # PUSH socket (إرسال الأوامر)
            self._push_socket = self._context.socket(zmq.PUSH)
            self._push_socket.connect(f"tcp://{self.host}:{self.push_port}")

            # PULL socket (استقبال الردود)
            self._pull_socket = self._context.socket(zmq.PULL)
            self._pull_socket.connect(f"tcp://{self.host}:{self.pull_port}")
            self._pull_socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)

            self._connected = True
            logger.info(f"✅ متصل بـ MT5 Bridge على {self.host}:{self.push_port}")
            return True

        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ MT5: {e}")
            return False

    async def disconnect(self):
        if self._push_socket:
            self._push_socket.close()
        if self._pull_socket:
            self._pull_socket.close()
        if self._context:
            self._context.term()
        self._connected = False

    async def send_order(self, order: MT5Order) -> MT5Response:
        """إرسال أمر تداول إلى MT5"""

        if not self._connected:
            return await self._simulate_order(order)

        payload = json.dumps(asdict(order))

        try:
            await self._push_socket.send_string(payload)
            response_str = await self._pull_socket.recv_string()
            response = json.loads(response_str)

            return MT5Response(
                success=response.get("success", False),
                ticket=response.get("ticket"),
                message=response.get("message", ""),
                price_executed=response.get("price"),
                error_code=response.get("error_code"),
            )

        except zmq.error.Again:
            logger.error("⏰ MT5 لم يرد في الوقت المحدد")
            return MT5Response(
                success=False,
                ticket=None,
                message="Timeout - MT5 لم يرد",
                price_executed=None,
                error_code=-1,
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الأمر: {e}")
            return MT5Response(
                success=False,
                ticket=None,
                message=str(e),
                price_executed=None,
                error_code=-2,
            )

    async def _simulate_order(self, order: MT5Order) -> MT5Response:
        """وضع المحاكاة عند عدم توفر ZMQ"""
        logger.info(f"🔵 [SIMULATION] {order.action} {order.order_type} {order.symbol} @ {order.price}")
        await asyncio.sleep(0.1)  # محاكاة تأخير الشبكة
        return MT5Response(
            success=True,
            ticket=123456,
            message=f"[SIMULATION] {order.order_type} {order.symbol} executed",
            price_executed=order.price,
            error_code=None,
        )

    async def close_trade(self, ticket: int, symbol: str, lot: float) -> MT5Response:
        """إغلاق صفقة بتذكرتها"""
        order = MT5Order(
            action="CLOSE",
            symbol=symbol,
            order_type="CLOSE",
            lot=lot,
            price=0,
            sl=0,
            tp=0,
            comment=f"Close#{ticket}",
        )
        return await self.send_order(order)

    async def modify_sl_tp(
        self,
        ticket: int,
        symbol: str,
        new_sl: float,
        new_tp: float,
    ) -> MT5Response:
        """تعديل SL/TP لصفقة قائمة"""
        order = MT5Order(
            action="MODIFY",
            symbol=symbol,
            order_type="MODIFY",
            lot=0,
            price=0,
            sl=new_sl,
            tp=new_tp,
            comment=f"Modify#{ticket}",
            magic=ticket,
        )
        return await self.send_order(order)

    async def get_open_positions(self) -> list:
        """استقبال الصفقات المفتوحة من MT5"""
        if not self._connected:
            return []

        query = json.dumps({"action": "GET_POSITIONS"})
        try:
            await self._push_socket.send_string(query)
            response_str = await self._pull_socket.recv_string()
            return json.loads(response_str).get("positions", [])
        except Exception as e:
            logger.error(f"خطأ في جلب الصفقات: {e}")
            return []

    async def execute_signal(self, signal_dict: dict) -> MT5Response:
        """
        تنفيذ إشارة كاملة في MT5
        يحول Signal.to_dict() إلى أمر MT5
        """
        direction = signal_dict["direction"]
        order_type = "BUY" if direction == "BUY" else "SELL"

        order = MT5Order(
            action="OPEN",
            symbol=signal_dict["symbol"],
            order_type=order_type,
            lot=signal_dict["lot"],
            price=signal_dict["entry"],
            sl=signal_dict["sl"],
            tp=signal_dict["tp2"],  # TP2 كهدف رئيسي
            comment=f"Signal#{signal_dict['id'][:20]}",
        )

        response = await self.send_order(order)

        if response.success:
            logger.info(f"✅ MT5 تنفيذ ناجح: Ticket#{response.ticket} @ {response.price_executed}")
        else:
            logger.error(f"❌ MT5 فشل التنفيذ: {response.message}")

        return response

    @classmethod
    def from_env(cls) -> "MT5Bridge":
        return cls(
            host=os.getenv("MT5_HOST", "localhost"),
            push_port=int(os.getenv("MT5_PUSH_PORT", "32768")),
            pull_port=int(os.getenv("MT5_PULL_PORT", "32769")),
            timeout_ms=int(os.getenv("MT5_TIMEOUT_MS", "5000")),
        )

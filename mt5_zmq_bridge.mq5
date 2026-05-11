//+------------------------------------------------------------------+
//| MT5 ZeroMQ Bridge EA                                             |
//| يستقبل الأوامر من Python ويُرسل الردود                          |
//+------------------------------------------------------------------+
#property copyright "Forex Signals Bot"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Zmq\Zmq.mqh>

// المعلمات
input int    InpPushPort  = 32768;    // منفذ الاستقبال (Python → MT5)
input int    InpPullPort  = 32769;    // منفذ الإرسال (MT5 → Python)
input int    InpMagicNum  = 123456;   // Magic Number
input bool   InpDebugMode = true;     // وضع التصحيح

// ZMQ
Context context;
Socket  receiver(context, ZMQ_PULL);
Socket  sender(context, ZMQ_PUSH);
CTrade  trade;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   // الاتصال بـ ZMQ
   receiver.bind(StringFormat("tcp://*:%d", InpPushPort));
   sender.bind(StringFormat("tcp://*:%d", InpPullPort));
   
   receiver.setReceiveHighWaterMark(1000);
   receiver.setSendHighWaterMark(1000);
   
   // إعداد التداول
   trade.SetExpertMagicNumber(InpMagicNum);
   trade.SetDeviationInPoints(20);
   trade.SetTypeFilling(ORDER_FILLING_IOC);
   
   Print("✅ MT5 ZMQ Bridge جاهز على المنفذ ", InpPushPort);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   receiver.unbind(StringFormat("tcp://*:%d", InpPushPort));
   sender.unbind(StringFormat("tcp://*:%d", InpPullPort));
   Print("🛑 MT5 ZMQ Bridge أُغلق");
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   ZmqMsg message;
   
   // استقبال الأمر (غير متزامن)
   if(receiver.recv(message, true))
   {
      string json_str = message.getData();
      if(InpDebugMode) Print("📥 أمر مستلم: ", json_str);
      
      // معالجة الأمر وإرسال الرد
      string response = ProcessOrder(json_str);
      
      ZmqMsg reply(response);
      sender.send(reply);
      
      if(InpDebugMode) Print("📤 رد: ", response);
   }
}

//+------------------------------------------------------------------+
//| معالجة الأمر                                                     |
//+------------------------------------------------------------------+
string ProcessOrder(string json_str)
{
   // تحليل JSON بسيط
   string action    = ExtractField(json_str, "action");
   string symbol    = ExtractField(json_str, "symbol");
   string orderType = ExtractField(json_str, "order_type");
   double lot       = StringToDouble(ExtractField(json_str, "lot"));
   double price     = StringToDouble(ExtractField(json_str, "price"));
   double sl        = StringToDouble(ExtractField(json_str, "sl"));
   double tp        = StringToDouble(ExtractField(json_str, "tp"));
   string comment   = ExtractField(json_str, "comment");
   
   if(action == "GET_POSITIONS")
      return GetOpenPositions();
   
   if(action == "OPEN")
      return OpenOrder(symbol, orderType, lot, sl, tp, comment);
   
   if(action == "CLOSE")
   {
      int magic = (int)StringToInteger(ExtractField(json_str, "magic"));
      return CloseOrder(symbol, magic);
   }
   
   if(action == "MODIFY")
   {
      int magic = (int)StringToInteger(ExtractField(json_str, "magic"));
      return ModifyOrder(magic, sl, tp);
   }
   
   return "{\"success\":false,\"message\":\"Unknown action\",\"error_code\":-1}";
}

//+------------------------------------------------------------------+
//| فتح صفقة                                                         |
//+------------------------------------------------------------------+
string OpenOrder(string sym, string type, double lot, double sl, double tp, string comment)
{
   bool result = false;
   
   if(type == "BUY")
      result = trade.Buy(lot, sym, 0, sl, tp, comment);
   else if(type == "SELL")
      result = trade.Sell(lot, sym, 0, sl, tp, comment);
   
   if(result)
   {
      ulong ticket = trade.ResultOrder();
      double price = trade.ResultPrice();
      return StringFormat("{\"success\":true,\"ticket\":%d,\"price\":%f,\"message\":\"Order opened\",\"error_code\":null}", ticket, price);
   }
   
   int err = (int)trade.ResultRetcode();
   return StringFormat("{\"success\":false,\"ticket\":null,\"price\":null,\"message\":\"%s\",\"error_code\":%d}",
                       trade.ResultRetcodeDescription(), err);
}

//+------------------------------------------------------------------+
//| إغلاق صفقة                                                       |
//+------------------------------------------------------------------+
string CloseOrder(string sym, int magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == magic &&
         PositionGetString(POSITION_SYMBOL) == sym)
      {
         if(trade.PositionClose(ticket))
            return "{\"success\":true,\"message\":\"Position closed\",\"ticket\":" + IntegerToString(ticket) + "}";
      }
   }
   return "{\"success\":false,\"message\":\"Position not found\",\"error_code\":-3}";
}

//+------------------------------------------------------------------+
//| تعديل SL/TP                                                      |
//+------------------------------------------------------------------+
string ModifyOrder(int magic, double new_sl, double new_tp)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == magic)
      {
         if(trade.PositionModify(ticket, new_sl, new_tp))
            return "{\"success\":true,\"message\":\"SL/TP modified\"}";
      }
   }
   return "{\"success\":false,\"message\":\"Position not found for modify\"}";
}

//+------------------------------------------------------------------+
//| جلب الصفقات المفتوحة                                             |
//+------------------------------------------------------------------+
string GetOpenPositions()
{
   string positions = "[";
   bool first = true;
   
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(!first) positions += ",";
      positions += StringFormat(
         "{\"ticket\":%d,\"symbol\":\"%s\",\"type\":\"%s\",\"lot\":%.2f,\"open_price\":%.5f,\"profit\":%.2f}",
         ticket,
         PositionGetString(POSITION_SYMBOL),
         PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL",
         PositionGetDouble(POSITION_VOLUME),
         PositionGetDouble(POSITION_PRICE_OPEN),
         PositionGetDouble(POSITION_PROFIT)
      );
      first = false;
   }
   positions += "]";
   
   return "{\"success\":true,\"positions\":" + positions + "}";
}

//+------------------------------------------------------------------+
//| استخراج حقل من JSON (تحليل بسيط)                                |
//+------------------------------------------------------------------+
string ExtractField(string json, string field)
{
   string search = "\"" + field + "\":";
   int pos = StringFind(json, search);
   if(pos == -1) return "";
   
   pos += StringLen(search);
   
   // تخطي الفراغات
   while(pos < StringLen(json) && StringSubstr(json, pos, 1) == " ") pos++;
   
   bool is_string = StringSubstr(json, pos, 1) == "\"";
   if(is_string) pos++;
   
   string result = "";
   int end_pos = pos;
   
   while(end_pos < StringLen(json))
   {
      string ch = StringSubstr(json, end_pos, 1);
      if(is_string && ch == "\"") break;
      if(!is_string && (ch == "," || ch == "}" || ch == " ")) break;
      result += ch;
      end_pos++;
   }
   
   return result;
}

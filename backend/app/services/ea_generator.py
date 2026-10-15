"""
EA Generator — Generates production-ready MQL5 Expert Advisor source code for MT5.
Includes No-Code pairing, OnTradeTransaction real-time sync, and tick streaming.
"""


def generate_mql5_ea_source(default_server_url: str = "https://trade.homever.my.id", default_pairing_code: str = "TG-000000") -> str:
    """Generate complete MQL5 Expert Advisor source code."""
    # Ensure URL doesn't have trailing slash
    clean_url = default_server_url.rstrip("/")

    return f"""//+------------------------------------------------------------------+
//|                                             TradeGearBridge.mq5  |
//|                             Copyright 2026, TradeGear Platform   |
//|                            https://tradegear.platform (No-Code)  |
//+------------------------------------------------------------------+
#property copyright   "TradeGear Platform"
#property link        "https://tradegear.platform"
#property version     "2.00"
#property description "TradeGear No-Code MT5 Bridge & Real-Time Synchronizer"
#property strict

//--- Input Parameters
input group "=== TradeGear Connection Settings ==="
input string   InpServerUrl     = "{clean_url}"; // TradeGear Webhook Server URL
input string   InpPairingCode   = "{default_pairing_code}"; // 6-Digit Pairing Code from Website
input int      InpHeartbeatSec  = 3;                        // Sync Interval (Seconds)
input bool     InpStreamTicks   = true;                     // Stream Real-Time Prices (Ticks)

//--- Global Variables
string g_Token = "";
datetime g_LastTickTime = 0;
bool g_IsPaired = false;

//+------------------------------------------------------------------+
//| Helper: Send HTTP POST Request via WebRequest                    |
//+------------------------------------------------------------------+
int HttpPost(string endpoint, string jsonPayload, string &responseOut)
{{
   string url = InpServerUrl + endpoint;
   string headers = "Content-Type: application/json\\r\\n";
   if(StringLen(g_Token) > 0)
   {{
      headers += "X-Agent-Token: " + g_Token + "\\r\\n";
   }}
   
   char postData[];
   char resultData[];
   string resultHeaders;
   
   StringToCharArray(jsonPayload, postData, 0, WHOLE_ARRAY, CP_UTF8);
   // Remove null terminator byte from payload
   int dataSize = ArraySize(postData) - 1;
   if(dataSize <= 0) return -1;
   ArrayResize(postData, dataSize);
   
   ResetLastError();
   int res = WebRequest("POST", url, headers, 3000, postData, resultData, resultHeaders);
   
   if(res == -1)
   {{
      int err = GetLastError();
      if(err == 4014)
      {{
         Print("❌ Error 4014: Please allow WebRequest for URL '", InpServerUrl, "' in Tools -> Options -> Expert Advisors");
      }}
      else
      {{
         Print("⚠️ WebRequest failed with error: ", err);
      }}
      return -1;
   }}
   
   responseOut = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
   return res;
}}

//+------------------------------------------------------------------+
//| Helper: Format Current Open Positions JSON                       |
//+------------------------------------------------------------------+
string GetOpenPositionsJson()
{{
   string json = "[";
   int total = PositionsTotal();
   int count = 0;
   
   for(int i = 0; i < total; i++)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {{
         string sym = PositionGetString(POSITION_SYMBOL);
         long type = PositionGetInteger(POSITION_TYPE);
         double lot = PositionGetDouble(POSITION_VOLUME);
         double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
         double currPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
         double sl = PositionGetDouble(POSITION_SL);
         double tp = PositionGetDouble(POSITION_TP);
         double profit = PositionGetDouble(POSITION_PROFIT);
         string comment = PositionGetString(POSITION_COMMENT);
         
         if(count > 0) json += ",";
         json += StringFormat(
            "{{\\"ticket\\":%I64u,\\"symbol\\":\\"%s\\",\\"direction\\":\\"%s\\",\\"lot\\":%.2f,\\"open_price\\":%.5f,\\"current_price\\":%.5f,\\"sl_price\\":%.5f,\\"tp_price\\":%.5f,\\"pnl\\":%.2f,\\"comment\\":\\"%s\\"}}",
            ticket, sym, (type == POSITION_TYPE_BUY ? "buy" : "sell"), lot, openPrice, currPrice, sl, tp, profit, comment
         );
         count++;
      }}
   }}
   json += "]";
   return json;
}}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{{
   Print("🚀 TradeGear Bridge initializing...");
   Print("   Server URL: ", InpServerUrl);
   Print("   Pairing Code: ", InpPairingCode);
   
   // 1. Send Handshake Pairing to TradeGear Server
   string pairPayload = StringFormat(
      "{{\\"pairing_code\\":\\"%s\\",\\"login\\":%I64d,\\"server\\":\\"%s\\",\\"broker\\":\\"%s\\",\\"balance\\":%.2f,\\"equity\\":%.2f}}",
      InpPairingCode,
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      AccountInfoString(ACCOUNT_COMPANY),
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoDouble(ACCOUNT_EQUITY)
   );
   
   string pairResponse = "";
   int code = HttpPost("/api/v1/accounts/pair", pairPayload, pairResponse);
   
   if(code >= 200 && code < 300)
   {{
      g_Token = InpPairingCode;
      g_IsPaired = true;
      Print("✅ Terminal successfully paired with TradeGear! Server: ", pairResponse);
   }}
   else
   {{
      Print("⚠️ Initial pairing pending or failed (code ", code, "). Will retry in heartbeat timer.");
      g_Token = InpPairingCode;
   }}
   
   // Start sync timer
   EventSetTimer(InpHeartbeatSec);
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
   EventKillTimer();
   Print("👋 TradeGear Bridge stopped.");
}}

//+------------------------------------------------------------------+
//| Real-Time Trade Event: OnTradeTransaction                        |
//| Triggered INSTANTLY on position open, close, SL/TP execution     |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                         const MqlTradeRequest& request,
                         const MqlTradeResult& result)
{{
   // Capture Deal Additions (executions)
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {{
      ulong dealTicket = trans.deal;
      if(HistoryDealSelect(dealTicket))
      {{
         long entryType = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
         long dealType  = HistoryDealGetInteger(dealTicket, DEAL_TYPE);
         string symbol  = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
         double volume  = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
         double price   = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
         double profit  = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
         ulong posId    = HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
         string comment = HistoryDealGetString(dealTicket, DEAL_COMMENT);
         
         string eventName = "deal_add";
         if(entryType == DEAL_ENTRY_OUT || entryType == DEAL_ENTRY_OUT_BY)
         {{
            eventName = "position_closed";
         }}
         else if(entryType == DEAL_ENTRY_IN)
         {{
            eventName = "position_opened";
         }}
         
         string direction = (dealType == DEAL_TYPE_BUY ? "buy" : "sell");
         
         string eventPayload = StringFormat(
            "{{\\"agent_token\\":\\"%s\\",\\"event\\":\\"%s\\",\\"data\\":{{\\"ticket\\":%I64u,\\"position_id\\":%I64u,\\"symbol\\":\\"%s\\",\\"direction\\":\\"%s\\",\\"lot\\":%.2f,\\"price\\":%.5f,\\"pnl\\":%.2f,\\"comment\\":\\"%s\\",\\"balance\\":%.2f,\\"equity\\":%.2f}}}}",
            g_Token, eventName, dealTicket, posId, symbol, direction, volume, price, profit, comment,
            AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY)
         );
         
         string resp = "";
         HttpPost("/api/v1/trades/agent-event", eventPayload, resp);
         Print("⚡ Real-time Trade Event sent: ", eventName, " #", posId, " ", symbol, " PnL: ", profit);
      }}
   }}
}}

//+------------------------------------------------------------------+
//| Real-Time Ticks: OnTick                                          |
//+------------------------------------------------------------------+
void OnTick()
{{
   if(!InpStreamTicks || !g_IsPaired) return;
   
   datetime now = TimeCurrent();
   // Throttle tick broadcast to 1 sec per chart to protect bandwidth
   if(now <= g_LastTickTime) return;
   g_LastTickTime = now;
   
   MqlTick lastTick;
   if(SymbolInfoTick(_Symbol, lastTick))
   {{
      string tickPayload = StringFormat(
         "{{\\"agent_token\\":\\"%s\\",\\"event\\":\\"tick\\",\\"data\\":{{\\"symbol\\":\\"%s\\",\\"bid\\":%.5f,\\"ask\\":%.5f,\\"time\\":%I64d}}}}",
         g_Token, _Symbol, lastTick.bid, lastTick.ask, (long)lastTick.time
      );
      string resp = "";
      HttpPost("/api/v1/trades/agent-event", tickPayload, resp);
   }}
}}

//+------------------------------------------------------------------+
//| Timer function: Heartbeat & Command Processing                   |
//+------------------------------------------------------------------+
void OnTimer()
{{
   string positionsJson = GetOpenPositionsJson();
   
   string syncPayload = StringFormat(
      "{{\\"agent_token\\":\\"%s\\",\\"event\\":\\"heartbeat\\",\\"data\\":{{\\"login\\":%I64d,\\"server\\":\\"%s\\",\\"broker\\":\\"%s\\",\\"balance\\":%.2f,\\"equity\\":%.2f,\\"margin\\":%.2f,\\"margin_free\\":%.2f,\\"positions\\":%s}}}}",
      g_Token,
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      AccountInfoString(ACCOUNT_COMPANY),
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoDouble(ACCOUNT_EQUITY),
      AccountInfoDouble(ACCOUNT_MARGIN),
      AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      positionsJson
   );
   
   string response = "";
   int resCode = HttpPost("/api/v1/trades/agent-event", syncPayload, response);
   if(resCode >= 200 && resCode < 300)
   {{
      g_IsPaired = true;
   }}
}}
//+------------------------------------------------------------------+
"""

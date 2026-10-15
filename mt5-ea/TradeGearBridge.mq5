//+------------------------------------------------------------------+
//|                                             TradeGearBridge.mq5  |
//|                             Copyright 2026, TradeGear Platform   |
//|                            https://tradegear.platform (No-Code)  |
//+------------------------------------------------------------------+
#property copyright   "TradeGear Platform"
#property link        "https://tradegear.platform"
#property version     "2.10"
#property description "TradeGear Autonomous MT5 Robot & Real-Time Synchronizer"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "=== TradeGear Connection Settings ==="
input string   InpServerUrl     = "https://trade.homever.my.id"; // TradeGear Webhook Server URL
input string   InpPairingCode   = "TG-000000";                 // 6-Digit Pairing Code from Website
input int      InpHeartbeatSec  = 3;                            // Sync Interval (Seconds)
input bool     InpStreamTicks   = true;                         // Stream Real-Time Prices (Ticks)

input group "=== Autonomous Auto-Trading (Robot Autopilot) ==="
input bool     InpAutoTrade      = true;                         // 🤖 Aktifkan Robot Autopilot (Beli/Jual Otomatis)
input double   InpLotSize        = 0.01;                         // Lot Size untuk Setiap Posisi
input int      InpFastEma        = 9;                            // Fast EMA Period
input int      InpSlowEma        = 21;                           // Slow EMA Period
input int      InpStopLossPips   = 40;                           // Stop Loss (Pips, 0 = Nonaktif)
input int      InpTakeProfitPips = 80;                           // Take Profit (Pips, 0 = Nonaktif)
input ulong    InpMagicNumber    = 884920;                       // Magic Number Robot

//--- Global Variables
CTrade   g_Trade;
string   g_Token = "";
datetime g_LastTickTime = 0;
datetime g_LastBarTime = 0;
bool     g_IsPaired = false;
int      g_FastEmaHandle = INVALID_HANDLE;
int      g_SlowEmaHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Helper: Send HTTP POST Request via WebRequest                    |
//+------------------------------------------------------------------+
int HttpPost(string endpoint, string jsonPayload, string &responseOut)
{
   string url = InpServerUrl + endpoint;
   string headers = "Content-Type: application/json\r\n";
   if(StringLen(g_Token) > 0)
   {
      headers += "X-Agent-Token: " + g_Token + "\r\n";
   }
   
   char postData[];
   char resultData[];
   string resultHeaders;
   
   StringToCharArray(jsonPayload, postData, 0, WHOLE_ARRAY, CP_UTF8);
   int dataSize = ArraySize(postData) - 1;
   if(dataSize <= 0) return -1;
   ArrayResize(postData, dataSize);
   
   ResetLastError();
   int res = WebRequest("POST", url, headers, 3000, postData, resultData, resultHeaders);
   
   if(res == -1)
   {
      int err = GetLastError();
      if(err == 4014)
      {
         Print("⚠️ Error 4014: Please allow WebRequest for URL '", InpServerUrl, "' in Tools -> Options -> Expert Advisors");
      }
      else
      {
         Print("⚠️ WebRequest failed with error: ", err);
      }
      return -1;
   }
   
   responseOut = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
   return res;
}

//+------------------------------------------------------------------+
//| Helper: Format Current Open Positions JSON                       |
//+------------------------------------------------------------------+
string GetOpenPositionsJson()
{
   string json = "[";
   int total = PositionsTotal();
   int count = 0;
   
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
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
            "{\"ticket\":%I64u,\"symbol\":\"%s\",\"direction\":\"%s\",\"lot\":%.2f,\"open_price\":%.5f,\"current_price\":%.5f,\"sl_price\":%.5f,\"tp_price\":%.5f,\"pnl\":%.2f,\"comment\":\"%s\"}",
            ticket, sym, (type == POSITION_TYPE_BUY ? "buy" : "sell"), lot, openPrice, currPrice, sl, tp, profit, comment
         );
         count++;
      }
   }
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
//| Autonomous Trading Evaluation (Autopilot Entry Engine)           |
//+------------------------------------------------------------------+
void CheckAutonomousEntry()
{
   if(!InpAutoTrade || g_FastEmaHandle == INVALID_HANDLE || g_SlowEmaHandle == INVALID_HANDLE) return;

   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_LastBarTime) return;

   // Check if a position is already open for this robot on this symbol
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
      {
         return; // Position already open
      }
   }

   double fastEma[];
   double slowEma[];
   ArraySetAsSeries(fastEma, true);
   ArraySetAsSeries(slowEma, true);

   if(CopyBuffer(g_FastEmaHandle, 0, 1, 2, fastEma) < 2) return;
   if(CopyBuffer(g_SlowEmaHandle, 0, 1, 2, slowEma) < 2) return;

   // fastEma[0] is Bar 1 (just closed), fastEma[1] is Bar 2 (previous closed bar)
   bool bullishCross = (fastEma[1] <= slowEma[1] && fastEma[0] > slowEma[0]);
   bool bearishCross = (fastEma[1] >= slowEma[1] && fastEma[0] < slowEma[0]);

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pipMultiplier = (digits == 3 || digits == 5) ? 10 * point : point;

   if(bullishCross)
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl = (InpStopLossPips > 0) ? NormalizeDouble(ask - (InpStopLossPips * pipMultiplier), digits) : 0;
      double tp = (InpTakeProfitPips > 0) ? NormalizeDouble(ask + (InpTakeProfitPips * pipMultiplier), digits) : 0;

      if(g_Trade.Buy(InpLotSize, _Symbol, ask, sl, tp, "TradeGear AutoBot EMA"))
      {
         Print("🚀 [TradeGear AutoBot] Golden Cross detected! Auto BUY executed on ", _Symbol, " Lot: ", InpLotSize);
         g_LastBarTime = currentBarTime;
      }
      else
      {
         Print("❌ [TradeGear AutoBot] Buy order failed: ", g_Trade.ResultRetcodeDescription());
      }
   }
   else if(bearishCross)
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl = (InpStopLossPips > 0) ? NormalizeDouble(bid + (InpStopLossPips * pipMultiplier), digits) : 0;
      double tp = (InpTakeProfitPips > 0) ? NormalizeDouble(bid - (InpTakeProfitPips * pipMultiplier), digits) : 0;

      if(g_Trade.Sell(InpLotSize, _Symbol, bid, sl, tp, "TradeGear AutoBot EMA"))
      {
         Print("🚀 [TradeGear AutoBot] Death Cross detected! Auto SELL executed on ", _Symbol, " Lot: ", InpLotSize);
         g_LastBarTime = currentBarTime;
      }
      else
      {
         Print("❌ [TradeGear AutoBot] Sell order failed: ", g_Trade.ResultRetcodeDescription());
      }
   }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("🚀 TradeGear Bridge & Auto-Trading Robot initializing...");
   Print("   Server URL: ", InpServerUrl);
   Print("   Pairing Code: ", InpPairingCode);
   Print("   Autopilot Mode: ", InpAutoTrade ? "ENABLED (Automatic Trading)" : "DISABLED (Sync Only)");

   g_Trade.SetExpertMagicNumber(InpMagicNumber);
   g_Trade.SetDeviationInPoints(20);
   g_Trade.SetTypeFillingBySymbol(_Symbol);

   if(InpAutoTrade)
   {
      g_FastEmaHandle = iMA(_Symbol, _Period, InpFastEma, 0, MODE_EMA, PRICE_CLOSE);
      g_SlowEmaHandle = iMA(_Symbol, _Period, InpSlowEma, 0, MODE_EMA, PRICE_CLOSE);
      Print("🤖 [TradeGear AutoBot] Strategy initialized: EMA ", InpFastEma, "/", InpSlowEma, " on ", _Symbol);
   }

   // 1. Send Handshake Pairing to TradeGear Server
   string pairPayload = StringFormat(
      "{\"pairing_code\":\"%s\",\"login\":%I64d,\"server\":\"%s\",\"broker\":\"%s\",\"balance\":%.2f,\"equity\":%.2f}",
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
   {
      g_Token = InpPairingCode;
      g_IsPaired = true;
      Print("✅ Terminal successfully paired with TradeGear! Server: ", pairResponse);
   }
   else
   {
      Print("⚠️ Initial pairing pending or failed (code ", code, "). Will retry in heartbeat timer.");
      g_Token = InpPairingCode;
   }
   
   EventSetTimer(InpHeartbeatSec);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_FastEmaHandle != INVALID_HANDLE) IndicatorRelease(g_FastEmaHandle);
   if(g_SlowEmaHandle != INVALID_HANDLE) IndicatorRelease(g_SlowEmaHandle);
   Print("👋 TradeGear Bridge & Auto-Trading Robot stopped.");
}

//+------------------------------------------------------------------+
//| Real-Time Trade Event: OnTradeTransaction                        |
//| Triggered INSTANTLY on position open, close, SL/TP execution     |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                         const MqlTradeRequest& request,
                         const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      ulong dealTicket = trans.deal;
      if(HistoryDealSelect(dealTicket))
      {
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
         {
            eventName = "position_closed";
         }
         else if(entryType == DEAL_ENTRY_IN)
         {
            eventName = "position_opened";
         }
         
         string direction = (dealType == DEAL_TYPE_BUY ? "buy" : "sell");
         
         string eventPayload = StringFormat(
            "{\"agent_token\":\"%s\",\"event\":\"%s\",\"data\":{\"ticket\":%I64u,\"position_id\":%I64u,\"symbol\":\"%s\",\"direction\":\"%s\",\"lot\":%.2f,\"price\":%.5f,\"pnl\":%.2f,\"comment\":\"%s\",\"balance\":%.2f,\"equity\":%.2f}}",
            g_Token, eventName, dealTicket, posId, symbol, direction, volume, price, profit, comment,
            AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY)
         );
         
         string resp = "";
         HttpPost("/api/v1/trades/agent-event", eventPayload, resp);
         Print("⚡ Real-time Trade Event sent: ", eventName, " #", posId, " ", symbol, " PnL: ", profit);
      }
   }
}

//+------------------------------------------------------------------+
//| Real-Time Ticks: OnTick                                          |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Run autonomous trading analysis on every tick/bar
   CheckAutonomousEntry();

   // 2. Stream tick data to web dashboard
   if(!InpStreamTicks || !g_IsPaired) return;
   
   datetime now = TimeCurrent();
   if(now <= g_LastTickTime) return;
   g_LastTickTime = now;
   
   MqlTick lastTick;
   if(SymbolInfoTick(_Symbol, lastTick))
   {
      string tickPayload = StringFormat(
         "{\"agent_token\":\"%s\",\"event\":\"tick\",\"data\":{\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"time\":%I64d}}",
         g_Token, _Symbol, lastTick.bid, lastTick.ask, (long)lastTick.time
      );
      string resp = "";
      HttpPost("/api/v1/trades/agent-event", tickPayload, resp);
   }
}

//+------------------------------------------------------------------+
//| Timer function: Heartbeat & State Synchronization                |
//+------------------------------------------------------------------+
void OnTimer()
{
   string positionsJson = GetOpenPositionsJson();
   
   string syncPayload = StringFormat(
      "{\"agent_token\":\"%s\",\"event\":\"heartbeat\",\"data\":{\"login\":%I64d,\"server\":\"%s\",\"broker\":\"%s\",\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"margin_free\":%.2f,\"positions\":%s}}",
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
   {
      g_IsPaired = true;
   }
}
//+------------------------------------------------------------------+

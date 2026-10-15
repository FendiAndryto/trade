"""
TradeGear — TradingView Webhook Simulator CLI
Simulates live TradingView alert webhooks to test the Risk Engine and Dashboard execution pipeline.
"""

import argparse
import json
import sys
import time
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_SERVER_URL = "http://localhost:8001"
DEFAULT_STRATEGY_ID = "6465a5ac-feb3-4247-9ee5-706a1f63daa4"
DEFAULT_TOKEN = "dev-test-token"


def get_live_price(symbol: str = "XAUUSD") -> float:
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            for name in [symbol, f"{symbol}m", f"{symbol}.pro", f"{symbol}_i"]:
                tick = mt5.symbol_info_tick(name)
                if tick and tick.bid > 0:
                    return float(tick.bid)
    except Exception:
        pass
    return 4145.00 if "XAU" in symbol else 1.08950


def get_preset_payload(preset: str, price: float | None = None) -> dict:
    curr_gold = price or get_live_price("XAUUSD")
    if preset == "buy-gold":
        return {
            "action": "buy",
            "symbol": "XAUUSD",
            "price": round(curr_gold, 2),
            "sl": round(curr_gold - 10.0, 2),
            "tp": round(curr_gold + 20.0, 2),
            "comment": "Simulator: 15m Gold Bullish Breakout",
        }
    elif preset == "sell-gold":
        return {
            "action": "sell",
            "symbol": "XAUUSD",
            "price": round(curr_gold, 2),
            "sl": round(curr_gold + 10.0, 2),
            "tp": round(curr_gold - 20.0, 2),
            "comment": "Simulator: 15m Gold Bearish Rejection",
        }
    elif preset == "sell-eur":
        curr_eur = price or get_live_price("EURUSD")
        return {
            "action": "sell",
            "symbol": "EURUSD",
            "price": round(curr_eur, 5),
            "sl": round(curr_eur + 0.0025, 5),
            "tp": round(curr_eur - 0.0055, 5),
            "comment": "Simulator: 1h Trend Pin Bar",
        }
    elif preset == "close-gold":
        return {
            "action": "close",
            "symbol": "XAUUSD",
            "price": round(curr_gold, 2),
            "comment": "Simulator: Exit Gold Position",
        }
    elif preset == "reject-risk":
        return {
            "action": "buy",
            "symbol": "XAUUSD",
            "price": 2650.00,
            "sl": 2649.99,  # Ridiculously tight SL -> calculated lot size > 50 -> triggers risk clamp/rejection
            "lot": 99.0,    # Will exceed maximum lot bounds
            "comment": "Simulator: Over-leveraged trade attempt",
        }
    return {
        "action": "buy",
        "symbol": "XAUUSD",
        "price": price or 2650.00,
        "sl": 2642.00,
        "tp": 2665.00,
        "comment": "Simulator: Custom signal",
    }


def send_webhook(
    server_url: str,
    strategy_id: str,
    token: str,
    payload: dict,
):
    url = f"{server_url.rstrip('/')}/api/v1/webhook/{strategy_id}"

    headers = {
        "Content-Type": "application/json",
        "X-API-Token": token,
    }

    print("\n" + "=" * 60)
    print("🚀 TradeGear Webhook Simulator")
    print("=" * 60)
    print(f"📡 Target Endpoint: {url}")
    print(f"🔑 Header Token:    {token}")
    print(f"📦 Outgoing Payload:")
    print(json.dumps(payload, indent=2))
    print("-" * 60)

    start_t = time.perf_counter()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            elapsed_ms = (time.perf_counter() - start_t) * 1000

        print(f"⏱️  Roundtrip Latency: {elapsed_ms:.1f} ms")
        print(f"📊 HTTP Status:       {response.status_code} {response.reason_phrase}")

        try:
            res_json = response.json()
            print("📬 Server Response:")
            print(json.dumps(res_json, indent=2))

            if response.status_code == 200:
                status_val = res_json.get("status", "")
                if status_val == "executed":
                    print("\n✅ SUCCESS: Sinyal berhasil lolos validasi Risk Engine dan dieksekusi!")
                    print("👉 Cek dashboard Anda: https://localhost:3000/dashboard (Tabel posisi & toast)")
                elif status_val == "rejected":
                    print("\n🛡️  RISK ENGINE TRIPPED: Sinyal sengaja ditolak oleh guardrails risiko.")
                    print(f"👉 Alasan penolakan: {res_json.get('message')}")
            else:
                print(f"\n❌ Error from server: {response.text}")

        except json.JSONDecodeError:
            print("Response:", response.text)

    except httpx.ConnectError:
        print(f"\n❌ Connection Error: Backend server tidak aktif di {server_url}!")
        print("Pastikan uvicorn sudah berjalan: uvicorn app.main:app --reload --port 8001")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="TradeGear TradingView Webhook Simulator CLI"
    )
    parser.add_argument(
        "--preset",
        choices=["buy-gold", "sell-gold", "sell-eur", "close-gold", "reject-risk", "custom"],
        default="buy-gold",
        help="Predefined test scenario",
    )
    parser.add_argument("--action", choices=["buy", "sell", "close", "close_buy", "close_sell"], help="Action type")
    parser.add_argument("--symbol", default="XAUUSD", help="Trading symbol (e.g. XAUUSD, EURUSD)")
    parser.add_argument("--price", type=float, help="Market / alert price")
    parser.add_argument("--sl", type=float, help="Stop loss price")
    parser.add_argument("--tp", type=float, help="Take profit price")
    parser.add_argument("--lot", type=float, help="Explicit lot size override")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="TradeGear Backend Server URL")
    parser.add_argument("--strategy", default=DEFAULT_STRATEGY_ID, help="Target Strategy UUID")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="X-API-Token for auth")

    args = parser.parse_args()

    if args.preset != "custom" and not args.action:
        payload = get_preset_payload(args.preset, args.price)
    else:
        payload = {
            "action": args.action or "buy",
            "symbol": args.symbol.upper(),
            "price": args.price or 2650.00,
            "sl": args.sl,
            "tp": args.tp,
            "lot": args.lot,
            "comment": f"Simulator: {args.action or 'buy'} on {args.symbol}",
        }

    send_webhook(
        server_url=args.server,
        strategy_id=args.strategy,
        token=args.token,
        payload=payload,
    )


if __name__ == "__main__":
    main()

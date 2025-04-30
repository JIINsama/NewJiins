from flask import Flask, request, jsonify
from binance.client import Client
from dotenv import load_dotenv
import os

# ✅ API 키 불러오기
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

client = Client(API_KEY, API_SECRET)
app = Flask(__name__)

# ✅ 자동 주문 함수
def place_futures_order(signal, symbol="BTCUSDT"):
    try:
        leverage = 20
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        print(f"🔧 레버리지 설정: {leverage}배")

        side = Client.SIDE_BUY if signal == "buy" else Client.SIDE_SELL

        ticker = client.futures_symbol_ticker(symbol=symbol)
        current_price = float(ticker["price"])
        print("📊 현재 BTC 가격:", current_price)

        balances = client.futures_account_balance()
        usdt_balance = next(item for item in balances if item["asset"] == "USDT")
        available_balance = float(usdt_balance["balance"])
        print("💰 사용 가능 잔고:", available_balance)

        order_value = available_balance * 0.30 * leverage
        if order_value < 10:
            print(f"⚠️ 주문 금액이 너무 작아서 생략됨: {order_value:.2f} USDT")
            return False

        quantity = round(order_value / current_price, 3)
        if quantity < 0.001:
            print(f"⚠️ 수량이 너무 작아서 주문 생략됨: {quantity} BTC")
            return False

        print("📦 주문 수량(BTC):", quantity)

        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )

        print("✅ 주문 성공:", order)
        return True

    except Exception as e:
        print("❌ 주문 실패:", str(e))
        return False

# ✅ 포지션 종료 함수
def close_position(symbol="BTCUSDT"):
    try:
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            amt = float(pos["positionAmt"])
            if amt != 0:
                side = Client.SIDE_SELL if amt > 0 else Client.SIDE_BUY
                qty = abs(amt)
                print(f"🔻 포지션 종료 시도: {side} {qty} BTC")

                order = client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=qty,
                    reduceOnly=True
                )
                print("✅ 포지션 종료 성공:", order)
                return True

        print("ℹ️ 종료할 포지션 없음")
        return False

    except Exception as e:
        print("❌ 포지션 종료 실패:", str(e))
        return False

# ✅ Webhook 수신
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("📩 수신 데이터:", data)

        signal = data.get("signal", "").lower()
        print("🧭 받은 시그널:", signal)

        if signal in ["buy", "sell"]:
            success = place_futures_order(signal)
            return jsonify({"status": "order sent" if success else "order failed"})

        elif signal == "exit":
            success = close_position()
            return jsonify({"status": "exit sent" if success else "no position to exit"})

        return jsonify({"error": "invalid signal"}), 400

    except Exception as e:
        print("❌ 처리 중 에러:", str(e))
        return jsonify({"error": "server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
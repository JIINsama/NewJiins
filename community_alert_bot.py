import os
import time
import schedule
import requests
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
from datetime import datetime

# ─────── .env 환경변수 로딩 ───────
load_dotenv()
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK    = os.getenv("DISCORD_WEBHOOK")
TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# ─────── OpenAI 키 설정 ───────
openai.api_key = OPENAI_API_KEY

# ─────── 알림 전송 함수들 ───────
def send_discord(message):
    try:
        r = requests.post(DISCORD_WEBHOOK, json={"content": message})
        if r.status_code != 204:
            print("❌ 디스코드 전송 실패:", r.status_code, r.text)
    except Exception as e:
        print("❌ 디스코드 오류:", e)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print("❌ 텔레그램 전송 실패:", r.status_code, r.text)
    except Exception as e:
        print("❌ 텔레그램 오류:", e)

def send_alert_to_both(msg):
    print(f"📢 전송 중: {msg[:60]}...")
    send_discord(msg)
    send_telegram(msg)

# ─────── 커뮤니티 심리 분석 ───────
def fetch_text(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        texts = [tag.get_text(strip=True) for tag in soup.find_all(['h3', 'h4', 'p', 'td'])]
        return "\n".join(texts)
    except Exception as e:
        return f"[크롤링 오류] {url}: {e}"

def extract_top3(text):
    prompt = (
        "다음은 코인 커뮤니티 글 제목 및 본문입니다.\n"
        "영문 티커(BTC, ETH, XRP 등) 중 가장 많이 언급된 Top 3를 알려줘.\n"
        "형식: 순위. 티커 (횟수)\n\n"
        f"{text}"
    )
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.2
    )
    return res.choices[0].message.content.strip()

def run_community_alert():
    print("📡 커뮤니티 글 수집 중...")
    fm_text = fetch_text("https://www.fmkorea.com/coin")
    dc_text = fetch_text("https://gall.dcinside.com/board/lists?id=bitcoins_new1")
    print("🧠 GPT 분석 중...")
    top3 = extract_top3(fm_text + "\n\n" + dc_text)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    alert_msg = f"📰 커뮤니티 심리 분석 결과 ({timestamp})\n{top3}"
    send_alert_to_both(alert_msg)

# ─────── 가격 변동률 테스트 알람 (예시) ───────
def run_price_alert():
    now = datetime.now().strftime('%H:%M')
    msg = f"📈 [{now}] BTCUSDT 변동률 테스트: +1.53%\nOI -2.3%, 거래량 +25.6%"
    send_alert_to_both(msg)

# ─────── 자동 실행 스케줄 등록 ───────
schedule.every(6).hours.do(run_community_alert)  # 심리 분석: 6시간마다
schedule.every(5).minutes.do(run_price_alert)    # 가격 알림: 5분마다

# ─────── 메인 루프 ───────
if __name__ == "__main__":
    print("⏱️ 알람봇 실행 시작됨 (6시간 심리 분석 / 5분 가격 알림)")
    while True:
        schedule.run_pending()
        time.sleep(10)
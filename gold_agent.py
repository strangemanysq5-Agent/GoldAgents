import os
import subprocess
import sys

# تثبيت المكتبات المساعدة تلقائياً
required_packages = ["requests", "schedule", "google-genai", "pytz"]
for package in required_packages:
    try:
        __import__(package if package != "google-genai" else ("google.genai" if package != "pytz" else "pytz"))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import time
import datetime
import pytz
import requests
from google import genai
from google.genai import types
import schedule

# --- 1. المفاتيح والمعلومات ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOLD_API_KEY = os.getenv("GOLD_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
client = genai.Client()

# المتغيرات الخاصة بالأسعار والتنبيهات
last_checked_price = None
reference_open_price = None  # لحساب الهبوط عن سعر الإغلاق/الافتتاح اليومي

local_tz = pytz.timezone('Asia/Muscat')

# --- 2. جلب بيانات الذهب ---
def get_gold_market_data() -> dict:
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {"x-access-token": GOLD_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        price = data.get("price", 0)
        prev_close = data.get("prev_close_price", price)
        return {"success": True, "price": price, "prev_close": prev_close}
    except Exception as e:
        print(f"خطأ أثناء جلب أسعار الذهب: {e}")
        return {"success": False, "error": str(e)}

# --- 3. إرسال الرسائل لتيليجرام ---
def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في تليجرام: {e}")

system_instruction = """
أنت وكيل ذكي استثماري محترف ومخصص لسبائك الذهب.
تعتمد استراتيجيتك على الشراء التدريجي (DCA) وحفظ القيمة على المدى الطويل.
ضع الأسعار والتوصيات بالريال العماني (OMR) والدولار الأمريكي (USD).
"""

# --- 4. فحص تنبيهات الهبوط ---
def check_price_drop_emergency():
    global last_checked_price
    data = get_gold_market_data()
    if not data["success"] or data["price"] == 0:
        return

    current_price = data["price"]
    prev_close = data["prev_close"]

    # مقارنة الهبوط اليومي مقارنة بإغلاق الأمس
    if prev_close > 0:
        daily_change_pct = ((current_price - prev_close) / prev_close) * 100
        # إذا انخفض الذهب اليوم بمقدار 1% أو أكثر مقارنة بسعر إغلاق الأمس
        if daily_change_pct <= -1.0:
            alert_message = (
                f"🚨 *تنبيه طارئ: انخفاض في سعر الذهب!* 🚨\n\n"
                f"انخفض الذهب اليوم بنسبة *{abs(daily_change_pct):.2f}%* مقارنة بإغلاق الأمس!\n"
                f"السعر الحالي: `{current_price}` USD للأونصة\n"
                f"سعر الإغلاق السابق: `{prev_close}` USD"
            )
            send_telegram_message(alert_message)

    last_checked_price = current_price

# --- 5. التقارير اليومية والأسبوعية ---
def job_daily_report():
    data = get_gold_market_data()
    if not data["success"]:
        return

    price_usd = data['price']
    price_omr_oz = price_usd * 0.3845
    price_gram_24_omr = price_omr_oz / 31.1035

    prompt = (
        f"سعر أونصة الذهب الحالي هو {price_usd} دولار (ما يعادل {price_gram_24_omr:.2f} ريال عماني لجرام عيار 24).\n"
        f"اكتب تقريراً يومياً موجزاً ومنظماً لأسعار الذهب وفرص الشراء والملاحظات الاستثمارية."
    )
    
    config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
    
    now_str = datetime.datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p")
    report = f"📊 *التقرير اليومي لأسعار الذهب ({now_str})*\n\n{response.text}"
    send_telegram_message(report)

def job_weekly_report():
    prompt = "اكتب تقريراً أسبوعياً تحليلياً شاملاً لاتجاهات أسعار الذهب ونصائح الاستثمار في السبائك بالريال العماني."
    config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
    report = f"📈 *التقرير الأسبوعي الشامل لأسعار الذهب*\n\n{response.text}"
    send_telegram_message(report)

# --- 6. حلقة التوقيت والجدولة بتوقيت مسقط (UTC+4) ---
# التقرير اليومي مبرمج للساعة 09:00 صباحاً بتوقيت سلطنة عمان (يعادل 05:00 صباحاً UTC)
schedule.every(1).hours.do(check_price_drop_emergency)
schedule.every().day.at("05:00").do(job_daily_report) # 05:00 UTC = 09:00 AM Oman Time

print("🤖 تم تشغيل السكربت بنجاح وتفعيل مراقبة التوقيت...")

while True:
    try:
        schedule.run_pending()
    except Exception as e:
        print(f"خطأ في الحلقة الرئيسية: {e}")
    time.sleep(30)

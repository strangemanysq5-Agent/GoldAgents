import os
import subprocess
import sys

# تثبيت المكتبات تلقائياً إذا لم تكن موجودة (لضمان عدم ظهور أخطاء على سحابة Render)
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

# --- 1. إعداد المفاتيح والمعلومات الشخصية ---
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "ضع_مفتاح_جيميني_هنا")
GOLD_API_KEY = os.getenv("GOLD_API_KEY", "ضع_مفتاح_جولد_اي_بي_اي_هنا")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ضع_توكن_بوت_تليجرام_هنا")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "ضع_رقم_الـ_Chat_ID_هنا")

client = genai.Client()
last_checked_price = None

# تحديد المنطقة الزمنية لسلطنة عمان (مسقط)
local_tz = pytz.timezone('Asia/Muscat')

# --- 2. الأدوات (Tools): جلب سعر الذهب ---
def get_gold_market_data() -> dict:
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {"x-access-token": GOLD_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        price = data.get("price", 0)
        prev_close = data.get("prev_close_price", price)
        return {"success": True, "price": price, "prev_close": prev_close}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 3. إرسال الرسائل عبر تليجرام ---
def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"خطأ في تليجرام: {e}")

# --- 4. تعليمات الوكيل ---
system_instruction = """
أنت وكيل ذكي استثماري محترف ومخصص لسبائك الذهب.
تعتمد استراتيجيتك على الشراء التدريجي (DCA) وحفظ القيمة على المدى الطويل.
"""

# --- 5. وظائف التنبيهات والتقارير ---
def check_price_drop_emergency():
    global last_checked_price
    data = get_gold_market_data()
    if not data["success"]: return

    current_price = data["price"]
    if last_checked_price is None:
        last_checked_price = current_price
        return

    price_diff = current_price - last_checked_price
    percentage_change = (price_diff / last_checked_price) * 100

    if percentage_change <= -1.0:
        alert_message = (
            f"🚨 *تنبيه طارئ: فرصة شراء محتملة!* 🚨\n\n"
            f"هبط الذهب بنسبة *{abs(percentage_change):.2f}%* خلال الساعة الماضية!\n"
            f"السعر الحالي: `{current_price}` دولار"
        )
        send_telegram_message(alert_message)

    last_checked_price = current_price

def job_daily_report():
    data = get_gold_market_data()
    prompt = f"سعر أونصة الذهب الحالي هو {data['price']} دولار. اكتب تقريراً يومياً موجزاً عن حالة السوق وفرص الشراء بالريال العماني والدولار."
    config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
    report = f"📊 *التقرير اليومي لأسعار الذهب*\n\n{response.text}"
    send_telegram_message(report)

def job_weekly_report():
    prompt = "اكتب تقريراً أسبوعياً تحليلياً شاملاً لاتجاهات أسعار الذهب ونصائح الاستثمار في السبائك."
    config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
    report = f"📈 *التقرير الأسبوعي الشامل لأسعار الذهب*\n\n{response.text}"
    send_telegram_message(report)

# --- 6. الجدولة والتشغيل المستمر مع مراعاة توقيت مسقط ---
def run_scheduled_jobs():
    while True:
        schedule.run_pending()
        time.sleep(1)

# حساب التوقيت المناسب وجدولة المهام بناءً على توقيت مسقط (سلطنة عمان)
# بما أن مكتبة schedule تنفذ وفق التوقيت المحلي للسيرفر، سنقوم بتحويل توقيت مسقط إلى توقيت السيرفر أو استخدام حلقة التحقق بالزمن المحلي:

def schedule_jobs_local_time():
    # بدلاً من الاعتماد المطلق على schedule.every().day، نتحقق بالدقيقة بناءً على توقيت مسقط
    now_local = datetime.datetime.now(local_tz)
    return now_local

# ضبط جدول المهام اليومية (الساعة 9:00 صباحاً بتوقيت مسقط - أو الساعة 14:00 حسب رغبتك)
schedule.every(1).hours.do(check_price_drop_emergency)

# جدولة التقرير اليومي بالساعة 9:00 صباحاً بتوقيت مسقط
schedule.every().day.at("09:00").do(job_daily_report)

# جدولة التقرير الأسبوعي يوم الجمعة الساعة 15:00 بتوقيت مسقط
schedule.every().friday.at("15:00").do(job_weekly_report)

print("🤖 وكيل الذهب يعمل بنجاح ويراقب السوق حسب توقيت مسقط...")
send_telegram_message("🤖 مرحباً! تم تشغيل وكيل الذهب بنجاح وهو يراقب السوق الآن.")

while True:
    # التحقق من المهام المعلقة
    schedule.run_pending()
    time.sleep(30)

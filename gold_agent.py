import os
import time
import requests
from google import genai
from google.genai import types
import schedule

# --- 1. إعداد المفاتيح والمعلومات (نقرأها من النظام أو نضعها مباشرة هنا) ---
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6KDWLa2W-2nZ2lCPwJsCGwTgn5yj-kqMB5h8eDBKfIQzA")
GOLD_API_KEY = os.getenv("GOLD_API_KEY", "goldapi-a4cc96d6713e9d7e1e6e2c3e2f1de657-io")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9053104032:AAEWYN8_TwUkxWrazQqN45MJ3BQgW4Ky_cM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6695331440")

client = genai.Client()
last_checked_price = None

# --- 2. الأدوات (Tools): جلب سعر الذهب ---
def get_gold_market_data() -> dict:
    """جلب سعر أونصة الذهب الحالي عالمياً بالدولار."""
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

# --- 4. تعليمات الوكيل (System Instructions) ---
system_instruction = """
أنت وكيل ذكي استثماري محترف ومخصص لسبائك الذهب.
تعتمد استراتيجيتك على الشراء التدريجي (DCA) وحفظ القيمة على المدى الطويل (3-5 سنوات).
قم بتحليل الأسعار بموضوعية وإعطاء تقارير دقيقة ومباشرة.
"""

# --- 5. وظائف التنبيهات والتقارير ---
def check_price_drop_emergency():
    """مراقبة طارئة تفحص السعر كل ساعة وترسل تنبيهاً إذا هبط بأكثر من 1%"""
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
            f"السعر الحالي: `{current_price}` دولار\n\n"
            f"💡 *نصيحة الوكيل:* فرصة ممتازة لتنفيذ جزء من خطة الشراء التدريجي."
        )
        send_telegram_message(alert_message)

    last_checked_price = current_price

def job_daily_report():
    """تقرير يومي الساعة 2 ظهراً"""
    data = get_gold_market_data()
    prompt = f"سعر أونصة الذهب الحالي هو {data['price']} دولار. اكتب تقريراً يومياً موجزاً عن حالة السوق وفرص الشراء."
    config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
    report = f"📊 *التقرير اليومي لأسعار الذهب (الساعة 2:00 ظهراً)*\n\n{response.text}"
    send_telegram_message(report)

def job_weekly_report():
    """تقرير أسبوعي"""
    prompt = "اكتب تقريراً أسبوعياً تحليلياً شاملاً لاتجاهات أسعار الذهب ونصائح الاستثمار في السبائك."
    config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
    report = f"📈 التقرير الأسبوعي الشامل لأسعار الذهب\n\n{response.text}"
    send_telegram_message(report)

# --- 6. الجدولة والتشغيل المستمر ---
schedule.every(1).hours.do(check_price_drop_emergency)
schedule.every().day.at("14:00").do(job_daily_report)  # 2:00 ظهراً
schedule.every().friday.at("15:00").do(job_weekly_report)

print("🤖 وكيل الذهب يعمل بنجاح...")
# رسالة تجريبية فورية عند تشغيل السكريبت
send_telegram_message("🤖 مرحباً! تم تشغيل وكيل الذهب بنجاح وهو يراقب السوق الآن.")

while True:
    schedule.run_pending()
    time.sleep(60)
import os
import time
import json
import logging
import requests
from flask import Flask, request, jsonify

# --- ۱. تنظیمات پیشرفته لاگ‌گیری سیستم ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- ۲. بارگذاری و صحت‌سنجی متغیرهای محیطی ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
RENDER_URL = os.environ.get('RENDER_URL')

if not all([TOKEN, GEMINI_KEY, RENDER_URL]):
    logger.critical("خطا: برخی از متغیرهای محیطی (TELEGRAM_TOKEN, GEMINI_API_KEY, RENDER_URL) تنظیم نشده‌اند!")

# تمیزکاری آدرس رندر برای جلوگیری از دبل‌اسلش
BASE_URL = RENDER_URL.rstrip('/')

# آدرس امن وب‌هوک که به هیچ وجه توکن تو را در لاگ‌ها لو نمی‌دهد
WEBHOOK_PATH = "/v1/api/telegram/secure/updates"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# --- ۳. پرامپت تخصصی و مهندسی‌شده برای برنامه نویسی (System Instruction) ---
SYSTEM_PROMPT = (
    "شما یک مهندس ارشد نرم‌افزار (Senior Software Engineer) و یک معمار سیستم فوق‌العاده هوشمند هستید. "
    "وظیفه شما تحلیل، عیب‌یابی، بهینه‌سازی و نوشتن کدهای تمیز، استاندارد، امن و کاملاً بهینه است. "
    "قوانین سختی که باید رعایت کنید:\n"
    "۱. کدهایی که می‌نویسید باید کاملاً آماده اجرا (Production-ready) بدون باگ و دارای کامنت‌های توضیحی باشند.\n"
    "۲. پاسخ‌ها را با ساختار مرتب، استفاده از مارک‌داون پیشرفته برای سینتکس کدها (مثل ```python) بفرستید.\n"
    "۳. همیشه بهینه‌ترین الگوریتم از نظر حافظه و زمان (Time & Space Complexity) را انتخاب کنید.\n"
    "۴. زبان پاسخگویی شما فارسی روان، دقیق و کاملاً فنی باشد."
)

# --- ۴. تابع ارتباط بهینه و پرسرعت با هسته هوش مصنوعی گوگل ---
def call_gemini_api(user_prompt, retries=3, delay=2):
    """
    ارتباط با API مستقیم گوگل همراه با سیستم خودکار بازه زمانی صعودی (Exponential Backoff)
    برای جلوگیری از ارور شلوغی سرور یا محدودیت تعداد پیام.
    """
    # استفاده از مدل فوق‌العاده سریع و قدرتمند gemini-2.0-flash
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=){GEMINI_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"parts": [{"text": user_prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.3,  # کاهش دما برای افزایش دقت و تمرکز روی کدنویسی بدون خطا
            "maxOutputTokens": 4096 # دریافت حداکثر سقف پاسخ برای کدهای طولانی
        }
    }
    
    for attempt in range(retries):
        try:
            logger.info(f"Sending request to Gemini API (Attempt {attempt + 1}/{retries})...")
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
            # اگر خطای ۴۲۹ (تعداد درخواست زیاد) رخ داد، کمی صبر میکند و دوباره تلاش میکند
            if response.status_code == 429:
                logger.warning(f"Rate limit hit (429). Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
                continue
                
            response.raise_for_status()
            res_json = response.json()
            
            # استخراج ایمن متن تولید شده توسط جمینای
            ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
            return ai_text
            
        except Exception as e:
            logger.error(f"Error during Gemini API call: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                return "❌ سرورهای پردازش کد در حال حاضر پاسخگو نیستند. لطفا چند لحظه دیگر مجدداً تلاش کنید."

# --- ۵. متدهای فرعی ارسال دیتا به تلگرام (Telegram Bot API Wrapper) ---
def send_telegram_action(chat_id, action="typing"):
    """ارسال وضعیت در حال تایپ یا ارسال متن برای کاربر"""
    try:
        requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": action}, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send chat action: {e}")

def send_telegram_message(chat_id, text, reply_to_message_id=None):
    """ارسال پیام نهایی با پشتیبانی کامل و ایمن از MarkdownV2 و Markdown معمولی"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown" # بهترین فرمت برای نمایش کدهای برنامه‌نویسی به صورت خوانا
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        res = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=15)
        # اگر مارک‌داون به خاطر کاراکترهای خاص ارور داد، پیام را به صورت متن ساده می‌فرستد تا ربات کماکان کار کند
        if res.status_code != 200:
            logger.warning("Markdown parsing failed, falling back to plain text...")
            payload.pop("parse_mode", None)
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")

# --- ۶. مدیریت هسته مرکزی درخواست‌های وب‌هوک (Webhook Core) ---
@app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    """دریافت لایو پیام‌ها از تلگرام بدون کوچکترین نشتی توکن در دشبورد"""
    if request.headers.get('content-type') == 'application/json':
        update = request.get_json()
        
        # بررسی اینکه آیا آپدیت حاوی پیام متنی است یا خیر
        if "message" in update and "text" in update["message"]:
            message = update["message"]
            chat_id = message["chat"]["id"]
            user_text = message["text"]
            message_id = message["message_id"]
            
            # ۱. مدیریت کامند /start
            if user_text.startswith('/start'):
                welcome_msg = (
                    "💻 **به محیط توسعه ارشد هوش مصنوعی خوش آمدید**\n\n"
                    "من به جمینای متصل هستم و تخصصی برای کارهای سنگین برنامه نویسی، دیباگ کدهای پیچیده و معماری سیستم بهینه‌سازی شده‌ام.\n"
                    "📝 کدت یا سوالت را بفرست تا با دقت بالا برات بنویسم یا تحلیل کنم."
                )
                send_telegram_message(chat_id, welcome_msg)
                return jsonify({"status": "success"}), 200
                
            # ۲. مدیریت پردازش پیام‌های معمولی و کدهای سنگین
            send_telegram_action(chat_id, "typing")
            
            # فراخوانی هسته جمینای
            ai_response = call_gemini_api(user_text)
            
            # ارسال پاسخ هوشمند به کاربر
            send_telegram_message(chat_id, ai_response, reply_to_message_id=message_id)
            
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "Forbidden"}), 403

@app.route('/', methods=['GET'])
def health_check():
    """متد زنده نگه داشتن سرور رندر بدون قطعی"""
    return "⚡️ Advanced Coding Engine is active and stable!", 200

# --- ۷. فرآیند استارت‌آپ و کانفیگ ارتباطات ---
if __name__ == "__main__":
    logger.info("Initializing Telegram Webhook connection...")
    
    # حذف وب‌هوک قدیمی برای جلوگیری از تداخل سرورها
    try:
        requests.get(f"{TELEGRAM_API_URL}/deleteWebhook", timeout=10)
    except Exception as e:
        logger.error(f"Error deleting old webhook: {e}")
        
    # ست کردن وب‌هوک جدید روی آدرس کاملاً امن اختصاصی
    target_webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    try:
        set_res = requests.post(f"{TELEGRAM_API_URL}/setWebhook", json={"url": target_webhook_url}, timeout=10)
        if set_res.status_code == 200:
            logger.info(f"✅ Secure Webhook successfully established at target URL")
        else:
            logger.error(f"❌ Failed to set webhook: {set_res.text}")
    except Exception as e:
        logger.error(f"Critical error setting webhook: {e}")

    # اجرای سرور Flask روی پورت اختصاصی رندر
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    

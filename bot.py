import os
import time
import logging
import requests
from flask import Flask, request, jsonify

# --- ۱. تنظیمات پیشرفته لاگ‌گیری سیستم ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# --- ۲. بارگذاری متغیرهای محیطی ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
RENDER_URL = os.environ.get('RENDER_URL')

BASE_URL = RENDER_URL.rstrip('/')
WEBHOOK_PATH = "/v1/api/telegram/secure/updates"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# --- ۳. پرامپت تخصصی و مهندسی‌شده برای برنامه نویسی ---
SYSTEM_PROMPT = (
    "شما یک مهندس ارشد نرم‌افزار (Senior Software Engineer) و یک معمار سیستم فوق‌العاده هوشمند هستید. "
    "وظیفه شما تحلیل، عیب‌یابی، بهینه‌سازی و نوشتن کدهای تمیز، استاندارد، امن و کاملاً بهینه است. "
    "قوانین سختی که باید رعایت کنید:\n"
    "۱. کدهایی که می‌نویسید باید کاملاً آماده اجرا (Production-ready) بدون باگ و دارای کامنت‌های توضیحی باشند.\n"
    "۲. پاسخ‌ها را با ساختار مرتب، استفاده از مارک‌داون پیشرفته برای سینتکس کدها (مثل ```python) بفرستید.\n"
    "۳. همیشه بهینه‌ترین الگوریتم از نظر حافظه و زمان را انتخاب کنید.\n"
    "۴. زبان پاسخگویی شما فارسی روان، دقیق و کاملاً فنی باشد."
)

# --- ۴. تابع ارتباط بهینه با هسته هوش مصنوعی گوگل ---
def call_gemini_api(user_prompt, retries=3, delay=2):
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=){GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096}
    }
    
    for attempt in range(retries):
        try:
            logger.info(f"Connecting to Google Gemini API (Attempt {attempt + 1})...")
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if response.status_code == 429:
                time.sleep(delay)
                delay *= 2
                continue
                
            response.raise_for_status()
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                return "❌ سرور پردازشگر گوگل در حال حاضر شلوغ است. لطفا یک لحظه دیگر پیام خود را مجدداً ارسال کنید."

# --- ۵. متدهای ارسال دیتای تلگرام ---
def send_telegram_action(chat_id):
    try:
        requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except:
        pass

def send_telegram_message(chat_id, text, reply_id=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_id:
        payload["reply_to_message_id"] = reply_id
    try:
        res = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=15)
        if res.status_code != 200:
            payload.pop("parse_mode", None)
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        logger.error(f"Telegram Send Error: {e}")

# --- ۶. مدیریت هسته مرکزی درخواست‌های وب‌هوک ---
@app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        update = request.get_json()
        if "message" in update and "text" in update["message"]:
            message = update["message"]
            chat_id = message["chat"]["id"]
            user_text = message["text"]
            
            if user_text.startswith('/start'):
                send_telegram_message(chat_id, "💻 **به محیط توسعه ارشد هوش مصنوعی خوش آمدید**\n\nکد یا سوال برنامه‌نویسی خود را بفرستید.")
                return jsonify({"status": "success"}), 200
                
            send_telegram_action(chat_id)
            ai_response = call_gemini_api(user_text)
            send_telegram_message(chat_id, ai_response, reply_id=message["message_id"])
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Forbidden"}), 403

@app.route('/', methods=['GET'])
def health_check():
    return "⚡️ Advanced Coding Engine is active!", 200

if __name__ == "__main__":
    try:
        requests.get(f"{TELEGRAM_API_URL}/deleteWebhook", timeout=10)
    except:
        pass
        
    target_webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
    requests.post(f"{TELEGRAM_API_URL}/setWebhook", json={"url": target_webhook_url}, timeout=10)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    

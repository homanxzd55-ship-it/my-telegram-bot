import os
import time
import telebot
from flask import Flask, request
import google.generativeai as genai

# ۱. دریافت اطلاعات خصوصی از رندر
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
raw_gemini_keys = os.environ.get("GEMINI_API_KEYS", "")

# جداسازی کلیدهای جمینای
GEMINI_KEYS = [key.strip() for key in raw_gemini_keys.split(",") if key.strip()]

app = Flask(__name__)
bot = None

# مقداردهی ربات تلگرام بدون ترد برای حالت وب‌هوک
if BOT_TOKEN:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
        print("🟢 Telegram Bot Initialized.")
    except Exception as e:
        print(f"🔴 Telegram Init Error: {e}")

# ۲. تنظیم خودکار وب‌هوک تلگرام
if bot and RENDER_URL:
    try:
        webhook_url = f"{RENDER_URL.rstrip('/')}/{BOT_TOKEN}"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print(f"🛰️ Webhook set to: {webhook_url}")
    except Exception as e:
        print(f"❌ Webhook Error: {e}")

# ۳. دریافت پیام‌ها از تلگرام (Webhook Endpoint)
@app.route(f'/{BOT_TOKEN}' if BOT_TOKEN else '/dummy_route', methods=['POST'])
def telegram_webhook():
    if bot and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Unauthorized', 403

# ۴. صفحه اصلی بسیار ساده برای بیدار نگه داشتن سرور
@app.route('/')
def home():
    return "🤖 Gemix System Active and Running...", 200

# ۵. سیستم هوش مصنوعی و مدیریت کلیدها
if bot and len(GEMINI_KEYS) > 0:
    current_key_index = 0

    def get_gemini_model():
        global current_key_index
        system_prompt = (
            "You are an expert Senior Software Engineer. Your job is to help the user with "
            "programming, code optimization, and debugging. Provide clean, secure code snippets "
            "using proper Markdown formatting."
        )
        genai.configure(api_key=GEMINI_KEYS[current_key_index])
        return genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt
        )

    def rotate_key():
        global current_key_index
        if len(GEMINI_KEYS) > 1:
            current_key_index = (current_key_index + 1) % len(GEMINI_KEYS)
            print(f"🔄 Switched to Key Index: {current_key_index}")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        welcome_text = (
            "💻 به ربات دستیار برنامه‌نویسی Gemix خوش آمدید!\n\n"
            "من یک هوش مصنوعی متخصص در کدنویسی و دیباگ هستم. "
            "سوال یا کدت را بفرست تا کمکت کنم."
        )
        bot.reply_to(message, welcome_text)

    @bot.message_handler(func=lambda message: True)
    def handle_ai_request(message):
        chat_id = message.chat.id
        bot.send_chat_action(chat_id, 'typing')
        
        for _ in range(len(GEMINI_KEYS)):
            try:
                model = get_gemini_model()
                response = model.generate_content(message.text)
                bot.reply_to(message, response.text, parse_mode='Markdown')
                return
            except Exception as e:
                print(f"❌ Error on key index {current_key_index}: {e}")
                rotate_key()
                bot.send_chat_action(chat_id, 'typing')
                time.sleep(1)
                
        bot.reply_to(message, "⚠️ سیستم شلوغ است. دوباره تلاش کن.")

# ۶. اجرای سرور
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

import os
import time
import threading
import telebot
import requests
from flask import Flask
import google.generativeai as genai
from telebot.apihelper import ApiTelegramException

# ==========================================
# ۱. دریافت اطلاعات خصوصی از محیط امن رندر
# ==========================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# دریافت و جداسازی ۳ کلید جمینای
raw_gemini_keys = os.environ.get("GEMINI_API_KEYS", "")
GEMINI_KEYS = [key.strip() for key in raw_gemini_keys.split(",") if key.strip()]

# بررسی اولیه برای اطمینان از وجود هر ۵ داده خصوصی (۱ توکن + ۳ کلید + ۱ لینک)
if not BOT_TOKEN or not RENDER_URL or len(GEMINI_KEYS) < 3:
    print("⚠️ اخطار: لطفاً تنظیمات هر ۵ متغیر خصوصی را در پنل رندر چک کنید.")

current_key_index = 0
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ==========================================
# ۲. مدیریت چرخش کلیدها و تخصص برنامه‌نویسی
# ==========================================
def get_gemini_model():
    global current_key_index
    
    # پرامپت تخصصی برای تبدیل ربات به یک مهندس ارشد برنامه‌نویسی
    system_prompt = (
        "You are an expert Senior Software Engineer. Your job is to help the user with "
        "programming, code optimization, and debugging. Provide clean, secure code snippets "
        "using proper Markdown formatting."
    )
    
    # ست کردن کلید فعلی
    genai.configure(api_key=GEMINI_KEYS[current_key_index])
    
    return genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=system_prompt
    )

def rotate_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(GEMINI_KEYS)
    print(f"🔄 Switch to API Key index: {current_key_index}")

# ==========================================
# ۳. سیستم ضد خواب رندر (Keep-Alive)
# ==========================================
@app.route('/')
def home():
    return "Coding AI Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive_ping():
    """پینگ خودکار هر ۴ دقیقه به آدرس رندر برای بیدار ماندن قطعی"""
    time.sleep(30) # صبر برای لود کامل سرور
    while True:
        try:
            if RENDER_URL:
                # حذف اسلش آخر آدرس در صورت وجود برای جلوگیری از خطا
                url = RENDER_URL.rstrip('/')
                requests.get(url, timeout=10)
                print("🚀 Self-Ping sent successfully! Container is awake.")
        except Exception as e:
            print(f"⚠️ Self-Ping failed: {e}")
        time.sleep(240) # هر ۴ دقیقه یکبار

# ==========================================
# ۴. پردازش پیام‌های تلگرام
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "💻 سلام! من دستیار تخصصی برنامه‌نویسی شما هستم. سوال یا باگ کدت رو برام بفرست.")

@bot.message_handler(func=lambda message: True)
def handle_ai_request(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    # تلاش برای گرفتن پاسخ با چرخش کلیدها در صورت بروز لیمیت
    for _ in range(len(GEMINI_KEYS)):
        try:
            model = get_gemini_model()
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text, parse_mode='Markdown')
            return
            
        except Exception as e:
            print(f"❌ Error on key {current_key_index}: {e}")
            rotate_key()
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(1)
            
    bot.reply_to(message, "⚠️ سیستم شلوغ است، لطفاً چند لحظه دیگر پیام دهید.")

# ==========================================
# ۵. اجرای موتورهای ربات
# ==========================================
if __name__ == '__main__':
    # اجرای سرور وب برای بیدار ماندن
    threading.Thread(target=run_flask, daemon=True).start()
    # اجرای بازرس پینگ
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    
    print("⚡ Bot polling started...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except ApiTelegramException as te:
            print(f"Telegram Exception: {te}")
            time.sleep(5)
        except Exception as ex:
            print(f"Connection lost, retrying...: {ex}")
            time.sleep(5)

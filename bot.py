import os
import requests
import logging
from flask import Flask, request
import telebot

# --- تنظیمات لاگ‌گیری برای پیدا کردن راحت‌تر ارورها در داشبورد رندر ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- دریافت متغیرهای محیطی امن ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY')
RENDER_URL = os.environ.get('RENDER_URL')

# مقداردهی اولیه
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- تابع ارتباط با OpenRouter ---
def get_openrouter_response(user_message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [
            # در خط زیر می‌توانی شخصیت ربات را تغییر دهی
            {"role": "system", "content": "شما یک دستیار هوش مصنوعی هوشمند، مودب و کمک‌کننده هستید که به زبان فارسی و با لحن دوستانه پاسخ می‌دهید."},
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status() # بررسی ارورهای HTTP
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"OpenRouter API Error: {e}")
        return "متأسفانه مشکلی در ارتباط با سرور هوش مصنوعی پیش آمده. لطفاً کمی بعد دوباره تلاش کنید. 🔄"

# --- مدیریت دستور /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "سلام! 👋 به ربات هوشمند من خوش آمدی.\n\n"
        "من به مدل رایگان Gemini متصل هستم. هر سوالی داری می‌توانی بپرسی!"
    )
    bot.reply_to(message, welcome_text)

# --- مدیریت دستور /help ---
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "🤖 **راهنمای استفاده:**\n\n"
        "🔸 کافیست سوال یا متن خود را بفرستی تا من جواب دهم.\n"
        "🔸 در حال حاضر من فقط پیام‌های متنی را متوجه می‌شوم.\n"
        "🔸 اگر پاسخم طولانی شد، کمی صبور باش تا متن کامل تولید شود."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

# --- مدیریت پیام‌های متنی عادی ---
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    # ارسال وضعیت "در حال تایپ..."
    bot.send_chat_action(message.chat.id, 'typing')
    
    # دریافت جواب
    ai_reply = get_openrouter_response(message.text)
    
    # تلاش برای ارسال پیام با فرمت زیبای Markdown
    try:
        bot.reply_to(message, ai_reply, parse_mode='Markdown')
    except Exception as e:
        logging.warning(f"Markdown formatting failed, sending plain text. Error: {e}")
        # اگر در متن هوش مصنوعی کاراکتر خاصی بود که باعث ارور تلگرام شد، پیام را به صورت متن ساده می‌فرستد
        bot.reply_to(message, ai_reply)

# --- مدیریت پیام‌های غیرمتنی (عکس، صدا، فایل و...) ---
@bot.message_handler(content_types=['photo', 'video', 'audio', 'document', 'voice', 'sticker'])
def handle_non_text(message):
    bot.reply_to(message, "من فعلاً چشم و گوش ندارم! 👀 فقط می‌توانم متن‌ها را بخوانم. لطفاً سوالت را برایم تایپ کن. ✍️")

# --- مسیر اصلی وب‌هوک ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Forbidden', 403

# --- مسیر زنده نگه داشتن سرور (Keep Alive) ---
@app.route('/', methods=['GET'])
def index():
    return "🚀 Bot Server is running perfectly!", 200

# --- اجرای برنامه ---
if __name__ == "__main__":
    # حذف وب‌هوک قدیمی برای جلوگیری از تداخل
    bot.remove_webhook()
    
    # تنظیم آدرس دقیق وب‌هوک
    base_url = RENDER_URL if RENDER_URL.endswith('/') else f"{RENDER_URL}/"
    webhook_url = f"{base_url}{TOKEN}"
    
    bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook successfully set to: {webhook_url}")
    
    # استارت سرور
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

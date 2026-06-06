import os
import time
import requests
import telebot
from flask import Flask, request

# ==========================================
# ۱. دریافت متغیرهای امنیتی از رندر
# ==========================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
RENDER_URL = os.environ.get('RENDER_URL')

# لود کردن ۳ کلید برای سیستم چرخش کلید (Key Rotation)
GEMINI_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]
# فیلتر کردن کلیدهای خالی جهت پایداری سیستم
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# شمارنده نوبتی برای چرخاندن کلیدها
key_index = 0

# ==========================================
# ۲. مکانیزم پرو چرخش کلید و ارتباط با گوگل
# ==========================================
def get_active_key():
    """چرخش نوبتی بین کلیدها برای موازنه بار و حذف محدودیت تعداد پیام"""
    global key_index
    if not GEMINI_KEYS:
        return None
    selected_key = GEMINI_KEYS[key_index % len(GEMINI_KEYS)]
    key_index += 1
    return selected_key

def ask_gemini_pro(prompt_text, image_data=None, mime_type=None):
    """
    ارتباط مستقیم با API رسمی گوگل جمینای.
    پشتیبانی همزمان از متن، عکس و هدایت سیستم (System Prompt) برای تولید کدهای فوق‌حرفه‌ای.
    """
    current_key = get_active_key()
    if not current_key:
        return "⚠️ خطای سرور: هیچ کلید API فعالی در بخش Environment رندر یافت نشد."

    # استفاده از مدل فوق‌العاده سریع و قدرتمند 1.5-Flash با قابلیت رایگان مولتی‌مدال
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={current_key}"
    headers = {'Content-Type': 'application/json'}

    # پرامپت ارشد برای بالا بردن دقت ربات در حد نسخه پرو
    system_instruction = (
        "You are Gemini Pro, an expert senior software engineer and system architect. "
        "Provide production-ready, highly optimized, secure, and clean code. "
        "Explain key parts briefly. Support Persian language perfectly for user guidance."
    )

    # ساختار پارت‌های درخواست (متن و عکس)
    parts = []
    
    # اگر کاربر عکس فرستاده بود، به فرمت باینری پایه به گوگل ارسال می‌شود
    if image_data and mime_type:
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": image_data
            }
        })
        
    # اضافه کردن متن کاربر یا کپشن عکس
    parts.append({
        "text": prompt_text if prompt_text else "این تصویر را به دقت تحلیل کن و اگر کدی در آن است بهینه‌سازی کن."
    })

    # بدنه اصلی درخواست بر اساس مستندات رسمی گوگل جمینای
    payload = {
        "contents": [{"parts": parts}],
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.2,  # پایین آوردن خطا و بالا بردن دقت منطقی کدها
            "maxOutputTokens": 4000
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # در صورت لیمیت شدن یک کلید، لایه دوم دفاعی سیستم فعال می‌شود
            return f"⚠️ پردازش پیام با خطا مواجه شد (کد {response.status_code}). لطفاً مجدداً پیام دهید تا کلید بعدی جایگزین شود."
    except requests.exceptions.Timeout:
        return "⏱️ پاسخ سرور گوگل کمی طولانی شد. لطفاً دوباره تلاش کنید."
    except Exception:
        return "⚠️ سیستم موقتاً در دسترس نیست. در حال بازنشانی ارتباط..."

# ==========================================
# ۳. هندلرهای عمومی ربات تلگرام (پیام متنی و عکس)
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🌟 به ربات هوش مصنوعی معماری و کدنویسی پیشرفته خوش آمدید!\n\n"
        "💻 **قابلیت‌ها:**\n"
        "• نوشتن و تحلیل کدهای بسیار خفن و بهینه در سطح Senior\n"
        "• پردازش و عیب‌یابی عکسِ ارورها، کدها و نمودارها\n"
        "• مجهز به سیستم پایدار چرخش ۳ کلید اختصاصی بدون قطعی\n\n"
        "✉️ پیام متنی خود را بفرستید یا یک تصویر آپلود کنید:"
    )
    bot.reply_to(message, welcome_text)

# هندلر پردازش عکس عمومی و سریع
import base64
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # دانلود امن عکس از سرور تلگرام به حافظه موقت سرور
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # تبدیل فایل عکس به Base64 جهت ارسال مستقیم به API گوگل
        encoded_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        user_caption = message.caption
        
        # فرستادن اطلاعات به موتور جمینای
        ai_response = ask_gemini_pro(user_caption, image_data=encoded_image, mime_type="image/jpeg")
        
        try:
            bot.reply_to(message, ai_response, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, ai_response)
            
    except Exception as e:
        bot.reply_to(message, "⚠️ خطایی در دانلود یا پردازش تصویر رخ داد.")

# هندلر پیام‌های متنی عمومی
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_response = ask_gemini_pro(message.text)
    
    try:
        bot.reply_to(message, ai_response, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, ai_response)

# ==========================================
# ۴. مدیریت وب‌هوک و بیدارباش زیر ۱۵ ثانیه
# ==========================================
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    """تضمین بیداری سریع وب‌هوک به محض دریافت اولین سیگنال بعد از خواب سرور"""
    bot.remove_webhook()
    time.sleep(0.1)
    bot.set_webhook(url=RENDER_URL + '/' + TOKEN)
    return "<h1>Amir AI Engine Status: Active & Stable</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    

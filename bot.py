import os
import time
import base64
import requests
import telebot
from flask import Flask, request

# ==========================================
# ۱. ساختار امنیتی و متغیرهای محیطی رندر
# ==========================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
RENDER_URL = os.environ.get('RENDER_URL')

# لود کردن هوشمند ۳ کلید اختصاصی گوگل جمینای
GEMINI_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]
# فیلتر کردن کلیدهای خالی برای تضمین پایداری لایه سرور
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# شمارنده نوبتی برای سیستم چرخش کلیدها (Load Balancing)
key_index = 0

# دیکشنری مدیریت محدودیت نرخ ارسال پیام کاربران برای مهار ارور 429
user_requests = {}

# ==========================================
# ۲. توابع زیرساختی و مدیریت منابع سیستم
# ==========================================

def get_active_gemini_key():
    """چرخش نوبتی کلیدها برای موازنه بار و از بین بردن محدودیت نرخ درخواست"""
    global key_index
    if not GEMINI_KEYS:
        return None
    selected_key = GEMINI_KEYS[key_index % len(GEMINI_KEYS)]
    key_index += 1
    return selected_key

def check_rate_limit(user_id):
    """
    جلوگیری از ارسال بیش از حد پیام در دقیقه.
    اجازه ارسال حداکثر ۱۵ پیام در دقیقه را به صورت کاملاً بهینه می‌دهد تا تلگرام آی‌پی را مسدود نکند.
    """
    now = time.time()
    if user_id not in user_requests:
        user_requests[user_id] = []
    
    # حذف پین‌های قدیمی‌تر از ۶۰ ثانیه پیش
    user_requests[user_id] = [t for t in user_requests[user_id] if now - t < 60]
    
    if len(user_requests[user_id]) >= 15:
        return True
        
    user_requests[user_id].append(now)
    return False

def call_gemini_api(prompt_text, image_base64=None, mime_type=None):
    """
    ارتباط مستقیم با Core هسته گوگل جمینای (بدون واسطه اوپن‌روتر).
    دارای سیستم خودکار هندل خطا و مدیریت تایم‌اوت‌های طولانی سرور رندر.
    """
    api_key = get_active_gemini_key()
    if not api_key:
        return "❌ خطای زیرساخت: کلیدهای هوش مصنوعی در تنظیمات رندر تعریف نشده‌اند."

    # اتصال به مدل مولتی‌مدال سریع و بهینه Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    # مهندسی پرامپت ارشد (System Instruction) برای خروجی‌های سطح پرو و تخصصی کدنویسی
    system_prompt = (
        "You are Gemini Pro, a world-class senior software engineer and system architect. "
        "Your task is to provide extremely optimized, clean, secure, and production-ready code blocks. "
        "Explain structural choices briefly. Respond in Persian for natural conversation, "
        "but keep code syntax, variables, and explanations professional."
    )

    # ساختار بخش داخلی پیام (پشتیبانی همزمان از عکس و متن)
    contents_parts = []
    
    if image_base64 and mime_type:
        contents_parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": image_base64
            }
        })
        
    contents_parts.append({
        "text": prompt_text if prompt_text else "این تصویر و آرایه کدهای داخل آن را به طور کامل تحلیل و عیب‌یابی کن."
    })

    payload = {
        "contents": [{"parts": contents_parts}],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "temperature": 0.2,  # تنظیم روی مقدار پایین برای ثبات منطقی کدها و کاهش ضریب خطا
            "maxOutputTokens": 4096
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        if response.status_code == 200:
            res_json = response.json()
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ پاسخ ناموفق موتور هوش مصنوعی (کد خطا: {response.status_code}). مجدداً تلاش کنید."
    except requests.exceptions.Timeout:
        return "⏱️ زمان پاسخگویی سرور اصلی طولانی شد. لطفاً پیام خود را دوباره ارسال کنید."
    except Exception:
        return "⚠️ اختلال موقت در هسته پردازش هوش مصنوعی. لطفاً چند لحظه دیگر امتحان کنید."

# ==========================================
# ۳. هندلرهای اصلی ربات تلگرام (Core Handlers)
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def welcome_user(message):
    welcome_message = (
        "🚀 **به نسخه پرو و پایدار ربات هوش مصنوعی خوش آمدید!**\n\n"
        "این سیستم برای کارهای سنگین، کدنویسی پیشرفته و معماری سیستم بهینه‌سازی شده است.\n\n"
        "🛠️ **ویژگی‌های کلیدی:**\n"
        "• **پردازش تصویر:** تصاویر ارورها، فرمول‌ها یا کدهایتان را ارسال کنید.\n"
        "• **کدنویسی ارشد (Senior):** تولید کدهای تمیز، بهینه و Production-Ready.\n"
        "• **پایداری کامل:** مجهز به سیستم سوییچ چرخشی بین ۳ هسته فعال گوگل.\n\n"
        "📝 پیام خود را بنویسید یا تصویر مورد نظر را ارسال کنید:"
    )
    try:
        bot.reply_to(message, welcome_message, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, welcome_message)

@bot.message_handler(content_types=['photo'])
def process_incoming_photo(message):
    """مدیریت عکس‌های ورودی، تبدیل مستقیم به باینری رم و عیب‌یابی آن ارورها"""
    user_id = message.from_user.id
    if check_rate_limit(user_id):
        bot.reply_to(message, "⚠️ امیر جان لطفا کمی آرام‌تر! سیستم در حال پردازش درخواست‌های قبلی شماست.")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_binary = bot.download_file(file_info.file_path)
        
        # تبدیل امن تصویر به فرمت استاندارد Base64 در حافظه رم
        base64_image = base64.b64encode(downloaded_binary).decode('utf-8')
        caption_text = message.caption
        
        # ارسال مستقیم پکت به API رسمی گوگل جمینای
        ai_reply = call_gemini_api(caption_text, image_base64=base64_image, mime_type="image/jpeg")
        
        try:
            bot.reply_to(message, ai_reply, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, ai_reply)
            
    except Exception:
        bot.reply_to(message, "❌ پردازش و دانلود تصویر با خطا مواجه شد. لطفاً کیفیت عکس را چک کرده و دوباره بفرستید.")

@bot.message_handler(func=lambda message: True)
def process_incoming_text(message):
    """پردازش متن و عیب‌یابی پیام‌های ورودی عمومی"""
    user_id = message.from_user.id
    if check_rate_limit(user_id):
        bot.reply_to(message, "⚠️ لطفاً بین ارسال پیام‌ها کمی فاصله بگذارید تا پایداری ربات حفظ شود.")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_reply = call_gemini_api(message.text)
    
    try:
        bot.reply_to(message, ai_reply, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, ai_reply)

# ==========================================
# ۴. مدیریت وب‌هوک و مکانیزم بیدارباش سریع رندر
# ==========================================

@app.route('/' + TOKEN, methods=['POST'])
def receive_telegram_updates():
    """هسته دریافت سیگنال از سرورهای تلگرام و پاس دادن مستقیم به ربات با متد امن"""
    try:
        json_data = request.get_data().decode('utf-8')
        update_obj = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update_obj])
        return "OK", 200
    except Exception as e:
        # ثبت استثنا در لاگ‌های رندر جهت خطایابی بدون خاموش شدن سرور
        print(f"Error executing webhook logic: {str(e)}")
        return "Internal Error", 500

@app.route("/")
def render_keep_alive_endpoint():
    """
    نقطه بیدارباش سرور رندر.
    اگر بعد از ۱۵ دقیقه خواب سرور، درخواستی بیاید، این تابع زیر ۱۵ ثانیه لود شده،
    وب‌هوک قدیمی را پاک کرده و اتصال تلگرام را بدون ارور ۴۲۹ نوسازی می‌کند.
    """
    try:
        bot.remove_webhook()
        time.sleep(0.1)
        # ست کردن مجدد آدرس وب‌هوک اصلی
        bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
        return "<h1>Amir Software Architecture Core: Online</h1>", 200
    except Exception as e:
        return f"<h1>Core System Initialization Failed</h1><p>{str(e)}</p>", 500

if __name__ == "__main__":
    # اجرای وب‌سرور فلَسک روی پورت اختصاصی ارائه شده توسط رندر
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    

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

# دریافت ۳ کلید مستقیم گوگل جمینای
GEMINI_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]
# فیلتر کردن مقادیر خالی برای جلوگیری از ارورهای اولیه
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# مدیریت محدودیت نرخ ارسال پیام (حداکثر ۱۵ پیام در دقیقه)
user_requests = {}

# ==========================================
# ۲. تابع ارتباط با API گوگل با لایه دفاعی چرخش خودکار در صورت خطا
# ==========================================
def ask_gemini_direct(prompt_text, image_base64=None, mime_type=None):
    if not GEMINI_KEYS:
        return "❌ خطای زیرساخت: هیچ کلید API فعالی در بخش Environment رندر تعریف نشده است."

    # سیستم به جای چرخاندنِ کورکورانه، تک تک کلیدها را تست می‌کند تا بالاخره یکی جواب دهد
    for api_key in GEMINI_KEYS:
        # استفاده از مدل قدرتمند و رایگان 1.5-Flash مستقیم گوگل
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        # پرامپت ارشد برای خروجی‌های فوق‌العاده تمیز و پرو کدنویسی
        system_prompt = (
            "You are Gemini Pro, a world-class senior software engineer and system architect. "
            "Provide production-ready, highly optimized, secure, and clean code blocks. "
            "Explain key parts briefly. Respond in Persian perfectly."
        )

        # ساخت پکت ساختاریافته متن و عکس برای گوگل
        contents_parts = []
        if image_base64 and mime_type:
            contents_parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_base64
                }
            })
            
        contents_parts.append({"text": prompt_text if prompt_text else "این تصویر را تحلیل کن:"})

        payload = {
            "contents": [{"parts": contents_parts}],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2, # دقت بالا و خلاقیت پایین برای کدهای بدون باگ
                "maxOutputTokens": 4000
            }
        }

        try:
            # ارسال درخواست به گوگل با تایم‌اوت مناسب
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            
            # اگر این کلید سالم بود و گوگل جواب داد، سریعاً پاسخ را برگردان و کار را تمام کن
            if response.status_code == 200:
                res_json = response.json()
                return res_json['candidates'][0]['content']['parts'][0]['text']
            else:
                # اگر این کلید ارور داد (مثلاً خطای 400 یا 429 یا 403)، بیخیال شو و برو سراغ کلید بعدی توی حلقه for
                print(f"Key failed with status {response.status_code}, trying next key...")
                continue
                
        except Exception as e:
            print(f"Connection error with key: {str(e)}")
            continue # در صورت خطای اتصال هم برو سراغ کلید بعدی

    # اگر کلیدها را چرخید و هیچ‌کدام کار نکردند:
    return "⚠️ در حال حاضر همه‌ی کلیدهای متصل به گوگل با خطا مواجه شدند. لطفاً کلیدهای خود را در رندر بررسی کنید یا چند لحظه دیگر پیام دهید."

def check_rate_limit(user_id):
    now = time.time()
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id] = [t for t in user_requests[user_id] if now - t < 60]
    if len(user_requests[user_id]) >= 15:
        return True
    user_requests[user_id].append(now)
    return False

# ==========================================
# ۳. هندلرهای ربات تلگرام (پیام متنی و عکس)
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def welcome_user(message):
    welcome_message = (
        "🤖 **سیستم مستقیم گوگل جمینای فعال شد!**\n\n"
        "این ربات مستقیماً به سرورهای رسمی گوگل متصل است و هیچ واسطه‌ای ندارد.\n\n"
        "💻 **امکانات پرو:**\n"
        "• **ارسال عکس:** عکس ارورها، کدها یا پروژه‌هات رو بفرست تا تحلیل کنم.\n"
        "• **کدنویسی ارشد:** تولید کدهای فوق‌العاده تمیز و بهینه.\n"
        "• **سیستم ضد‌کرش:** تست موازی ۳ کلید جیمیل برای دور زدن محدودیت‌ها.\n\n"
        "بپرس تا شروع کنیم داداش!"
    )
    bot.reply_to(message, welcome_message)

@bot.message_handler(content_types=['photo'])
def process_incoming_photo(message):
    user_id = message.from_user.id
    if check_rate_limit(user_id):
        bot.reply_to(message, "⚠️ لطفاً چند لحظه صبر کنید و سپس پیام دهید.")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_binary = bot.download_file(file_info.file_path)
        
        # تبدیل امن تصویر به Base64 در حافظه رم سرور رندر برای ارسال مستقیم به گوگل
        base64_image = base64.b64encode(downloaded_binary).decode('utf-8')
        caption_text = message.caption
        
        ai_reply = ask_gemini_direct(caption_text, image_base64=base64_image, mime_type="image/jpeg")
        
        try:
            bot.reply_to(message, ai_reply, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, ai_reply)
    except Exception:
        bot.reply_to(message, "❌ پردازش تصویر با خطا مواجه شد. دوباره تلاش کنید.")

@bot.message_handler(func=lambda message: True)
def process_incoming_text(message):
    user_id = message.from_user.id
    if check_rate_limit(user_id):
        bot.reply_to(message, "⚠️ امیر جان لطفاً بین پیام‌ها چند ثانیه فاصله بگذار.")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_reply = ask_gemini_direct(message.text)
    
    try:
        bot.reply_to(message, ai_reply, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, ai_reply)

# ==========================================
# ۴. مدیریت وب‌هوک و بیدارباش رندر
# ==========================================
@app.route('/' + TOKEN, methods=['POST'])
def receive_telegram_updates():
    try:
        json_data = request.get_data().decode('utf-8')
        update_obj = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update_obj])
        return "OK", 200
    except Exception as e:
        print(f"Webhook Error: {str(e)}")
        return "Error", 500

@app.route("/")
def render_keep_alive_endpoint():
    try:
        bot.remove_webhook()
        time.sleep(0.1)
        bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
        return "<h1>Amir Gemini Direct Core: Online</h1>", 200
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    

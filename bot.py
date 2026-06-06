import os
import time
import telebot
from flask import Flask, request, render_template_string
import google.generativeai as genai

# ==========================================
# ۱. دریافت کاملاً امن متغیرها از رندر
# ==========================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
raw_gemini_keys = os.environ.get("GEMINI_API_KEYS", "")

# استخراج و تمیزکاری کلیدهای جمینای
GEMINI_KEYS = [key.strip() for key in raw_gemini_keys.split(",") if key.strip()]

app = Flask(__name__)
bot = None
bot_status = "🔴 متغیر TELEGRAM_BOT_TOKEN در رندر یافت نشد!"
bot_username = ""

# راه‌اندازی ربات تلگرام با مکانیزم جلوگیری از کرش سرور
if BOT_TOKEN and not BOT_TOKEN.startswith("YOUR_"):
    try:
        # استفاده از وب‌هوک سازگار با هاست‌های بدون پولینگ
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
        bot_info = bot.get_me()
        bot_username = f"@{bot_info.username}"
        bot_status = f"🟢 متصل به تلگرام ({bot_info.first_name})"
    except Exception as e:
        bot_status = f"🔴 خطا در توکن تلگرام: {str(e)}"
        bot = None

# تنظیم خودکار وب‌هوک تلگرام
webhook_status = "🔴 غیرفعال (تنظیمات ناقص)"
if bot and RENDER_URL:
    try:
        webhook_url = f"{RENDER_URL.rstrip('/')}/{BOT_TOKEN}"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        webhook_status = f"🟢 فعال روی آدرس {webhook_url}"
        print(f"🛰️ Webhook successfully established: {webhook_url}")
    except Exception as e:
        webhook_status = f"🔴 خطا در ثبت وب‌هوک: {str(e)}"
        print(f"❌ Webhook registration failed: {e}")

# ==========================================
# ۲. صفحه وب عیب‌یابی و راهنمای زنده (ویژه گوشی)
# ==========================================
@app.route('/')
def diagnostics_dashboard():
    # تست وضعیت زنده کلیدهای جمینای
    gemini_status_list = []
    working_keys = 0
    for i, key in enumerate(GEMINI_KEYS):
        try:
            genai.configure(api_key=key)
            test_model = genai.GenerativeModel('gemini-1.5-flash')
            # تست بسیار سریع و کم‌حجم کلید
            test_model.generate_content("ping", generation_config={"max_output_tokens": 1})
            gemini_status_list.append(f"<li>🔑 کلید شماره {i+1}: <span style='color: #10b981; font-weight: bold;'>✅ فعال و سالم</span></li>")
            working_keys += 1
        except Exception as e:
            err_str = str(e)
            status_desc = "❌ کلید اشتباه یا مسدود"
            if "API_KEY_INVALID" in err_str:
                status_desc = "❌ کلید نامعتبر است"
            elif "429" in err_str or "quota" in err_str:
                status_desc = "⚠️ محدودیت ظرفیت (Rate Limit)"
            gemini_status_list.append(f"<li>🔑 کلید شماره {i+1}: <span style='color: #ef4444; font-weight: bold;'>{status_desc}</span></li>")

    keys_html = "".join(gemini_status_list) if GEMINI_KEYS else "<li><span style='color: #ef4444; font-weight: bold;'>❌ هیچ کلیدی تعریف نشده است!</span></li>"
    
    # تعیین وضعیت کلی سیستم
    system_healthy = (bot is not None) and (working_keys > 0) and (RENDER_URL is not None)
    badge_text = "🟢 ربات برنامه‌نویسی فعال و آماده کار است" if system_healthy else "🔴 ربات دارای نقص فنی در تنظیمات است"
    badge_bg = "#e0f2fe" if system_healthy else "#fee2e2"
    badge_color = "#0369a1" if system_healthy else "#b91c1c"

    html = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>پنل عیب‌یابی ربات هوش مصنوعی</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background-color: #0f172a; color: #cbd5e1; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 15px; }}
            .card {{ background: #1e293b; padding: 25px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); max-width: 450px; width: 100%; border: 1px solid #334155; }}
            h1 {{ text-align: center; font-size: 20px; color: #38bdf8; margin-top: 0; }}
            .badge {{ text-align: center; font-weight: bold; padding: 10px; border-radius: 10px; margin: 20px 0; background: {badge_bg}; color: {badge_color}; font-size: 14px; }}
            .item {{ background: #0f172a; padding: 12px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; font-size: 13px; }}
            .title {{ color: #94a3b8; font-weight: bold; display: block; margin-bottom: 5px; }}
            ul {{ padding-right: 20px; margin: 5px 0; }}
            .alert {{ background: #1e1b4b; border-right: 4px solid #6366f1; padding: 12px; border-radius: 8px; font-size: 12px; color: #c7d2fe; line-height: 1.6; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>📡 پنل وضعیت هوشمند Gemix</h1>
            <div class="badge">{badge_text}</div>
            
            <div class="item">
                <span class="title">🔌 وضعیت اتصال به تلگرام</span>
                <b>وضعیت:</b> {bot_status}<br>
                {f"<b>لینک ربات:</b> <a href='https://t.me/{bot_username[1:]}' style='color: #38bdf8; text-decoration: none;'>{bot_username}</a>" if bot_username else ""}
            </div>

            <div class="item">
                <span class="title">🧠 وضعیت کلیدهای جمینای (GEMINI_API_KEYS)</span>
                <ul>{keys_html}</ul>
            </div>

            <div class="item">
                <span class="title">🔗 آدرس وب‌هوک (RENDER_EXTERNAL_URL)</span>
                <b>وضعیت:</b> {webhook_status}
            </div>

            <div class="alert">
                💡 <b>راهنمای امنیتی برای گوشی:</b><br>
                اگر ضربدر قرمز یا خطایی می‌بینید، نگران نباشید. کد شما ایمن است. کافیست وارد پنل رندر شده، به بخش <b>Environment</b> بروید و متغیرهای مورد نظر را با دقت اصلاح کنید. با ذخیره تغییرات، سرور شما خودکار آپدیت می‌شود.
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html), 200

# Endpoint وب‌هوک برای پردازش پیام‌های دریافتی از تلگرام
@app.route(f'/{BOT_TOKEN}' if BOT_TOKEN else '/dummy_route', methods=['POST'])
def telegram_webhook():
    if bot and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Unauthorized', 403

# ==========================================
# ۳. هوش مصنوعی و مدیریت کلیدها (چرخش خودکار)
# ==========================================
if bot and len(GEMINI_KEYS) > 0:
    current_key_index = 0

    def get_gemini_model():
        global current_key_index
        system_prompt = (
            "You are an expert Senior Software Engineer. Help the user with programming, "
            "debugging, and code optimization. Provide clean, well-commented code blocks in Markdown."
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
            print(f"🔄 Switched to API Key Index: {current_key_index}")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        welcome_text = (
            "💻 به ربات هوشمند برنامه‌نویسی Gemix خوش آمدید!\n\n"
            "من یک متخصص ارشد برنامه‌نویسی، دیباگ و بهینه‌سازی کد هستم. "
            "سوال یا کد باگ‌دارت رو برام بفرست تا با بالاترین سرعت برات حلش کنم."
        )
        bot.reply_to(message, welcome_text)

    @bot.message_handler(func=lambda message: True)
    def handle_ai_request(message):
        chat_id = message.chat.id
        bot.send_chat_action(chat_id, 'typing')
        
        # تلاش متوالی روی کلیدها در صورت بروز خطا یا لیمیت
        for _ in range(len(GEMINI_KEYS)):
            try:
                model = get_gemini_model()
                response = model.generate_content(message.text)
                bot.reply_to(message, response.text, parse_mode='Markdown')
                return
            except Exception as e:
                print(f"❌ Error with key index {current_key_index}: {e}")
                rotate_key()
                bot.send_chat_action(chat_id, 'typing')
                time.sleep(1)
                
        bot.reply_to(message, "⚠️ تمام کلیدهای من موقتاً به محدودیت ظرفیت برخورد کرده‌اند. لطفاً چند دقیقه دیگر مجدداً تلاش کنید.")

# ==========================================
# ۴. اجرای وب سرور
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

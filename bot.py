import os
import time
import threading
import telebot
import requests
from flask import Flask
import google.generativeai as genai

# ==========================================
# ۱. دریافت اطلاعات خصوصی از رندر
# ==========================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
raw_gemini_keys = os.environ.get("GEMINI_API_KEYS", "")

# تمیز کردن و جداسازی کلیدهای جمینای
GEMINI_KEYS = [key.strip() for key in raw_gemini_keys.split(",") if key.strip()]

app = Flask(__name__)
bot = None
bot_status = "🔴 مقداردهی نشده (توکن تلگرام یافت نشد)"
bot_username = ""

# راه‌اندازی امن ربات تلگرام برای جلوگیری از کرش کل سرور
if BOT_TOKEN:
    try:
        bot = telebot.TeleBot(BOT_TOKEN)
        # تست اتصال توکن به تلگرام
        bot_info = bot.get_me()
        bot_username = f"@{bot_info.username}"
        bot_status = f"🟢 فعال و متصل به تلگرام ({bot_info.first_name})"
    except Exception as e:
        bot_status = f"🔴 خطا در اتصال به تلگرام: {str(e)}"
        bot = None

# ==========================================
# ۲. پنل مانیتورینگ زنده و عیب‌یابی فارسی
# ==========================================
@app.route('/')
def monitor_panel():
    # تست زنده تک‌تک کلیدهای جمینای برای اطمینان از کارکرد آن‌ها
    gemini_status_list = []
    working_keys_count = 0
    
    for i, key in enumerate(GEMINI_KEYS):
        try:
            # تست سه‌سوته کلید روی یک متن بسیار کوتاه
            genai.configure(api_key=key)
            test_model = genai.GenerativeModel('gemini-1.5-flash')
            test_model.generate_content("hi", generation_config={"max_output_tokens": 1})
            gemini_status_list.append(f"<li>🔑 کلید شماره {i+1}: <b style='color: #10b981;'>✅ فعال و سالم</b></li>")
            working_keys_count += 1
        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg:
                status = "❌ نامعتبر (کپی اشتباه)"
            elif "429" in error_msg or "quota" in error_msg:
                status = "⚠️ اتمام سهمیه روزانه (Rate Limit)"
            else:
                status = f"❌ خطا: {error_msg[:30]}..."
            gemini_status_list.append(f"<li>🔑 کلید شماره {i+1}: <b style='color: #ef4444;'>{status}</b></li>")

    keys_html = "".join(gemini_status_list) if GEMINI_KEYS else "<li><b style='color: #ef4444;'>❌ هیچ کلیدی یافت نشد! متغیر GEMINI_API_KEYS خالی است.</b></li>"
    
    # تعیین وضعیت نهایی سیستم
    system_ready = bot is not None and working_keys_count > 0
    system_badge = "🟢 سیستم ۱۰۰٪ آماده به کار و فعال است" if system_ready else "🔴 سیستم دارای نقص فنی است (به راهنما دقت کنید)"
    badge_color = "#e0f2fe" if system_ready else "#fee2e2"
    text_color = "#0369a1" if system_ready else "#b91c1c"

    # ساخت یک صفحه وب فوق‌العاده شیک و مدرن متناسب با تم گوشی
    html_page = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>پنل وضعیت ربات هوش مصنوعی Gemix</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
            .container {{ background: #1e293b; padding: 30px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 500px; width: 100%; border: 1px solid #334155; }}
            h1 {{ text-align: center; font-size: 22px; color: #38bdf8; margin-top: 0; margin-bottom: 25px; }}
            .badge {{ text-align: center; font-weight: bold; padding: 12px; border-radius: 12px; margin-bottom: 25px; background: {badge_color}; color: {text_color}; font-size: 14px; }}
            .section {{ background: #0f172a; padding: 15px; border-radius: 16px; margin-bottom: 20px; border: 1px solid #334155; }}
            .section-title {{ font-size: 14px; color: #94a3b8; font-weight: bold; margin-bottom: 10px; display: block; border-bottom: 1px solid #334155; padding-bottom: 5px; }}
            .status-text {{ font-size: 14px; word-break: break-all; line-height: 1.6; }}
            ul {{ margin: 0; padding-right: 20px; line-height: 1.8; font-size: 14px; }}
            .guide {{ background: #1e1b4b; border-right: 4px solid #6366f1; padding: 15px; border-radius: 12px; font-size: 12px; color: #c7d2fe; line-height: 1.6; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 پنل وضعیت هوشمند Gemix</h1>
            <div class="badge">{system_badge}</div>
            
            <div class="section">
                <span class="section-title">🔌 وضعیت اتصال به تلگرام</span>
                <div class="status-text">
                    <b>وضعیت:</b> {bot_status}<br>
                    {f"<b>آیدی ربات شما:</b> <a href='https://t.me/{bot_username[1:]}' style='color: #38bdf8; text-decoration: none;'>{bot_username}</a>" if bot_username else ""}
                </div>
            </div>

            <div class="section">
                <span class="section-title">🧠 وضعیت کلیدهای هوش مصنوعی (Gemini)</span>
                <ul style="list-style-type: square;">
                    {keys_html}
                </ul>
            </div>

            <div class="section">
                <span class="section-title">🔄 سیستم ضد خواب (Keep-Alive)</span>
                <div class="status-text">
                    <b>آدرس ست شده:</b> <span style="color: #cbd5e1; font-family: monospace;">{RENDER_URL if RENDER_URL else "❌ ست نشده (پینگ غیرفعال)"}</span>
                </div>
            </div>

            <div class="guide">
                💡 <b>راهنمای سریع رفع مشکل:</b><br>
                اگر ضربدر قرمز یا خطایی در بخش تلگرام یا کلیدها می‌بینید، کافیست در پنل رندر به بخش <b>Environment</b> بروید و مقادیر را اصلاح کنید. تغییرات پس از ذخیره به طور خودکار اعمال خواهند شد!
            </div>
        </div>
    </body>
    </html>
    """
    return html_page, 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# ۳. سیستم پینگ خودکار ضد خواب رندر
# ==========================================
def keep_alive_ping():
    time.sleep(30)
    while True:
        try:
            if RENDER_URL:
                url = RENDER_URL.rstrip('/')
                requests.get(url, timeout=10)
                print("🚀 Keep-Alive: Self-ping sent successfully!")
        except Exception as e:
            print(f"⚠️ Keep-Alive Ping failed: {e}")
        time.sleep(240)

# ==========================================
# ۴. پردازش پیام‌های برنامه‌نویسی تلگرام
# ==========================================
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
            print(f"🔄 Switched to Gemini API Key index: {current_key_index}")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        welcome_text = (
            "💻 به ربات دستیار برنامه‌نویسی Gemix خوش آمدید!\n\n"
            "من یک هوش مصنوعی متخصص در کدنویسی، دیباگ و حل مسائل برنامه‌نویسی هستم. "
            "کافیست سوال یا کدت را برای من بفرستی تا در سریع‌ترین زمان کمکت کنم."
        )
        bot.reply_to(message, welcome_text)

    @bot.message_handler(func=lambda message: True)
    def handle_ai_request(message):
        chat_id = message.chat.id
        bot.send_chat_action(chat_id, 'typing')
        
        # تلاش برای پردازش پیام با چرخاندن کلیدها در صورت بروز خطا
        for _ in range(len(GEMINI_KEYS)):
            try:
                model = get_gemini_model()
                response = model.generate_content(message.text)
                bot.reply_to(message, response.text, parse_mode='Markdown')
                return
            except Exception as e:
                print(f"❌ Error with Key {current_key_index}: {e}")
                rotate_key()
                bot.send_chat_action(chat_id, 'typing')
                time.sleep(1)
                
        bot.reply_to(message, "⚠️ در حال حاضر تمامی کلیدهای هوش مصنوعی با محدودیت موقت مواجه شده‌اند. لطفا چند دقیقه دیگر مجدداً تلاش کنید.")

# ==========================================
# ۵. اجرای موتورهای ربات
# ==========================================
if __name__ == '__main__':
    # اجرای وب سرور مانیتورینگ تحت هر شرایطی (جلوگیری از خطای رندر)
    threading.Thread(target=run_flask, daemon=True).start()
    
    if bot and len(GEMINI_KEYS) > 0:
        # اجرای پینگ ضد خواب
        threading.Thread(target=keep_alive_ping, daemon=True).start()
        
        print("⚡ Telegram Bot is Polling...")
        while True:
            try:
                bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
            except Exception as ex:
                print(f"Connection lost, retrying polling: {ex}")
                time.sleep(5)
    else:
        print("⚠️ Bot is not fully configured. Monitor panel is active at /")
        while True:
            time.sleep(3600)

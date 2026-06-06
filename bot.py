```python
import os
import time
import telebot
from flask import Flask, request, render_template_string
import google.generativeai as genai

# ==========================================
# ۱. دریافت اطلاعات خصوصی از محیط رندر
# ==========================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
raw_gemini_keys = os.environ.get("GEMINI_API_KEYS", "")

# جداسازی ۳ کلید جمینای
GEMINI_KEYS = [key.strip() for key in raw_gemini_keys.split(",") if key.strip()]

app = Flask(__name__)
bot = None
bot_username = ""
bot_status = "🔴 تنظیم نشده"

# مقداردهی ربات تلگرام
if BOT_TOKEN:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False) # غیرفعال کردن تردینگ داخلی برای وب‌هوک تلفیقی
        bot_info = bot.get_me()
        bot_username = f"@{bot_info.username}"
        bot_status = f"🟢 متصل به تلگرام ({bot_info.first_name})"
    except Exception as e:
        bot_status = f"🔴 خطا در توکن تلگرام: {str(e)}"
        bot = None

# ==========================================
# ۲. پیکربندی وب‌هوک تلگرام به صورت خودکار
# ==========================================
if bot and RENDER_URL:
    try:
        # حذف وب‌هوک قبلی و تنظیم وب‌هوک جدید روی آدرس رندر شما
        webhook_url = f"{RENDER_URL.rstrip('/')}/{BOT_TOKEN}"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print(f"🛰️ Webhook successfully set to: {webhook_url}")
    except Exception as e:
        print(f"❌ Failed to set Webhook: {e}")

# ==========================================
# ۳. دریافت پیام‌ها از تلگرام (Webhook Endpoint)
# ==========================================
@app.route(f'/{BOT_TOKEN}' if BOT_TOKEN else '/dummy_route', methods=['POST'])
def telegram_webhook():
    if bot and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Unauthorized', 403

# ==========================================
# ۴. صفحه وب مانیتورینگ فارسی برای گوشی
# ==========================================
@app.route('/')
def monitor_panel():
    # تست وضعیت کلیدهای هوش مصنوعی
    gemini_status_list = []
    working_keys = 0
    for i, key in enumerate(GEMINI_KEYS):
        try:
            genai.configure(api_key=key)
            test_model = genai.GenerativeModel('gemini-1.5-flash')
            test_model.generate_content("hi", generation_config={"max_output_tokens": 1})
            gemini_status_list.append(f"<li>🔑 کلید شماره {i+1}: <span style='color: #10b981; font-weight: bold;'>✅ فعال و سالم</span></li>")
            working_keys += 1
        except Exception as e:
            gemini_status_list.append(f"<li>🔑 کلید شماره {i+1}: <span style='color: #ef4444; font-weight: bold;'>❌ خطا (محدودیت یا کلید نامعتبر)</span></li>")

    keys_html = "".join(gemini_status_list) if GEMINI_KEYS else "<li><span style='color: #ef4444;'>❌ هیچ کلیدی یافت نشد!</span></li>"
    system_ready = bot is not None and working_keys > 0
    system_badge = "🟢 وب‌هوک فعال و سیستم آماده به کار است" if system_ready else "🔴 سیستم دارای نقص فنی در متغیرهاست"
    badge_bg = "#e0f2fe" if system_ready else "#fee2e2"
    badge_color = "#0369a1" if system_ready else "#b91c1c"

    html = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>پنل وضعیت وب‌هوک Gemix</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background-color: #0f172a; color: #cbd5e1; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 15px; }}
            .card {{ background: #1e293b; padding: 25px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); max-width: 450px; width: 100%; border: 1px solid #334155; }}
            h1 {{ text-align: center; font-size: 20px; color: #38bdf8; margin-top: 0; }}
            .badge {{ text-align: center; font-weight: bold; padding: 10px; border-radius: 10px; margin: 20px 0; background: {badge_bg}; color: {badge_color}; }}
            .item {{ background: #0f172a; padding: 12px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; font-size: 13px; }}
            .title {{ color: #94a3b8; font-weight: bold; display: block; margin-bottom: 5px; }}
            ul {{ padding-right: 20px; margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>📡 مانیتورینگ وب‌هوک ربات Gemix</h1>
            <div class="badge">{system_badge}</div>
            
            <div class="item">
                <span class="title">🔌 وضعیت اتصال به تلگرام</span>
                <b>وضعیت:</b> {bot_status}<br>
                {f"<b>آدرس بات:</b> <a href='https://t.me/{bot_username[1:]}' style='color: #38bdf8; text-decoration: none;'>{bot_username}</a>" if bot_username else ""}
            </div>

            <div class="item">
                <span class="title">🧠 کلیدهای جمینای (چرخشی)</span>
                <ul>{keys_html}</ul>
            </div>

            <div class="item">
                <span class="title">🔗 آدرس وب‌هوک فعال شده</span>
                <span style="font-family: monospace; color: #94a3b8; word-break: break-all;">{RENDER_URL if RENDER_URL else "❌ تنظیم نشده"}</span>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html), 200

# ==========================================
# ۵. پردازش هوش مصنوعی (مدیریت چرخش کلیدها)
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
            print(f"🔄 Switched to API Key Index: {current_key_index}")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        welcome_text = (
            "💻 به ربات دستیار برنامه‌نویسی Gemix خوش آمدید!\n\n"
            "من یک هوش مصنوعی متخصص در کدنویسی، دیباگ و حل مسائل برنامه‌نویسی هستم. "
            "کافیست سوال یا کدت را برای من بفرستی تا سریعاً کمکت کنم."
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
                
        bot.reply_to(message, "⚠️ تمام کلیدهای هوش مصنوعی موقتاً پر شده‌اند. لطفا چند دقیقه دیگر مجدداً تلاش کنید.")

# ==========================================
# ۶. اجرای سرور وب‌هوک
# ==========================================
if __name__ == '__main__':
    # رندر پورت را به ما می‌دهد
    port = int(os.environ.get("PORT", 8080))
    print(f"⚡ Starting Webhook server on port {port}...")
    app.run(host='0.0.0.0', port=port)

```

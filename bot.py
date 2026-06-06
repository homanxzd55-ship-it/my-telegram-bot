import os
import sys
import time
import base64
import requests
import telebot
from flask import Flask, request

# ==========================================
# متغیرهای محیطی
# ==========================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
RENDER_URL = os.environ.get('RENDER_URL')

GEMINI_KEYS = [
    os.environ.get('GEMINI_API_KEY_1'),
    os.environ.get('GEMINI_API_KEY_2'),
    os.environ.get('GEMINI_API_KEY_3')
]
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

print(f"✅ {len(GEMINI_KEYS)} Gemini key loaded", flush=True)
print(f"✅ RENDER_URL: {RENDER_URL}", flush=True)

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

user_requests = {}

# ==========================================
# ارتباط با Gemini
# ==========================================
def ask_gemini_direct(prompt_text, image_base64=None, mime_type=None):
    if not GEMINI_KEYS:
        return "❌ هیچ کلید API تعریف نشده."

    for i, api_key in enumerate(GEMINI_KEYS):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        system_prompt = (
            "You are Gemini Pro, a world-class senior software engineer and system architect. "
            "Provide production-ready, highly optimized, secure, and clean code blocks. "
            "Explain key parts briefly. Respond in Persian perfectly."
        )

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
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4000
            }
        }

        try:
            print(f"🔑 Trying key {i+1}...", flush=True)
            response = requests.post(url, json=payload, headers=headers, timeout=45)
            print(f"📊 Key {i+1} status: {response.status_code}", flush=True)

            if response.status_code == 200:
                res_json = response.json()
                print(f"✅ Key {i+1} success!", flush=True)
                return res_json['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"❌ Key {i+1} failed: {response.text[:200]}", flush=True)
                continue

        except requests.exceptions.Timeout:
            print(f"⏱ Key {i+1} timeout", flush=True)
            continue
        except Exception as e:
            print(f"💥 Key {i+1} error: {str(e)}", flush=True)
            continue

    return "⚠️ همه کلیدها با خطا مواجه شدند. لطفاً چند لحظه دیگر پیام دهید."


# ==========================================
# محدودیت نرخ
# ==========================================
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
# هندلرهای تلگرام
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def welcome_user(message):
    welcome_message = (
        "🤖 *سیستم مستقیم گوگل جمینای فعال شد!*\n\n"
        "این ربات مستقیماً به سرورهای رسمی گوگل متصل است.\n\n"
        "💻 *امکانات:*\n"
        "• ارسال عکس برای تحلیل کد یا ارور\n"
        "• تولید کدهای تمیز و بهینه\n"
        "• سیستم ضدکرش با ۳ کلید موازی\n\n"
        "بپرس تا شروع کنیم!"
    )
    bot.reply_to(message, welcome_message, parse_mode="Markdown")


@bot.message_handler(content_types=['photo'])
def process_incoming_photo(message):
    user_id = message.from_user.id
    if check_rate_limit(user_id):
        bot.reply_to(message, "⚠️ لطفاً چند لحظه صبر کنید.")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_binary = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_binary).decode('utf-8')
        caption_text = message.caption

        ai_reply = ask_gemini_direct(caption_text, image_base64=base64_image, mime_type="image/jpeg")

        try:
            bot.reply_to(message, ai_reply, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, ai_reply)

    except Exception as e:
        print(f"📸 Photo handler error: {str(e)}", flush=True)
        bot.reply_to(message, "❌ پردازش تصویر با خطا مواجه شد.")


@bot.message_handler(func=lambda message: True)
def process_incoming_text(message):
    user_id = message.from_user.id
    if check_rate_limit(user_id):
        bot.reply_to(message, "⚠️ لطفاً بین پیام‌ها چند ثانیه فاصله بگذار.")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        print(f"💬 Message: {message.text[:50]}", flush=True)
        ai_reply = ask_gemini_direct(message.text)
        try:
            bot.reply_to(message, ai_reply, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, ai_reply)
    except Exception as e:
        print(f"💥 Text handler error: {str(e)}", flush=True)
        bot.reply_to(message, "❌ خطایی رخ داد، دوباره تلاش کن.")


# ==========================================
# Flask routes
# ==========================================
@app.route('/' + TOKEN, methods=['POST'])
def receive_telegram_updates():
    try:
        json_data = request.get_data().decode('utf-8')
        update_obj = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update_obj])
        return "OK", 200
    except Exception as e:
        print(f"🔴 Webhook Error: {str(e)}", flush=True)
        return "Error", 500


@app.route("/")
def keep_alive():
    # فقط یه پاسخ ساده - بدون set_webhook
    return "<h1>Gemini Bot: Online ✅</h1>", 200


# ==========================================
# اجرا - webhook فقط یه بار set میشه
# ==========================================
if __name__ == "__main__":
    print("🚀 Setting webhook...", flush=True)
    try:
        bot.remove_webhook()
        time.sleep(2)
        result = bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
        print(f"✅ Webhook set: {result}", flush=True)
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}", flush=True)

    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

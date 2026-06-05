import os
import telebot
import requests
from flask import Flask
from threading import Thread

# --- ربات اطلاعات حساس را مستقیم از پنل امن رندر می‌خواند ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_FAST_KEY = os.getenv("OPENROUTER_FAST_KEY")
OPENROUTER_HEAVY_KEY = os.getenv("OPENROUTER_HEAVY_KEY")

# آیدی عددی تلگرام خودت و دوستت (آیدی‌های واقعی خودتان را جایگزین این دو عدد فرضی کن)
ALLOWED_USERS = [12345678, 87654321] 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "Gemix AI Bot is Online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- توابع هوش مصنوعی ---
def call_ai(prompt, api_key, model_name):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(url, headers=headers, json=data, timeout=60)
    return response.json()['choices'][0]['message']['content']

def call_gemini(prompt):
    # به جای YOUR_WORKER_URL آدرس ورکر کلاودفلر خودت را بگذار
    url = f"https://YOUR_WORKER_URL/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- مدیریت هوشمند پیام‌ها ---
@bot.message_handler(func=lambda message: message.from_user.id in ALLOWED_USERS)
def handle_message(message):
    user_prompt = message.text
    
    # تشخیص هوشمند سوالات سنگین و ریاضی برای مدل دقیق (DeepSeek R1)
    if len(user_prompt) > 100 or any(char in user_prompt for char in ['+', '-', '=', '/', '*']):
        try:
            bot.reply_to(message, "⏳ در حال پردازش سنگین و دقیق...")
            reply = call_ai(user_prompt, OPENROUTER_HEAVY_KEY, "deepseek/deepseek-r1")
            bot.reply_to(message, reply)
            return
        except Exception as e:
            print(f"Heavy AI failed: {e}")

    # پردازش سریع روزمره
    try:
        reply = call_gemini(user_prompt)
        bot.reply_to(message, reply)
    except:
        try:
            reply = call_ai(user_prompt, OPENROUTER_FAST_KEY, "meta-llama/llama-3-8b-instruct:free")
            bot.reply_to(message, reply)
        except:
            bot.reply_to(message, "⚠️ سیستم شلوغ است. دوباره تلاش کن.")

if __name__ == "__main__":
    Thread(target=run_server).start()
    print("🤖 Gemix System Active...")
    bot.infinity_polling()
    

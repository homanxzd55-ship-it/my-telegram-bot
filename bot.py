import os
import telebot
import requests
from flask import Flask, request

# دریافت توکن‌ها از Environment Variables رندر
TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENROUTER_FAST_KEY = os.environ.get('OPENROUTER_FAST_KEY')
OPENROUTER_HEAVY_KEY = os.environ.get('OPENROUTER_HEAVY_KEY')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# لیست آیدی‌های عددی مجاز (خودت و رفیقت)
ALLOWED_USERS = [6148577369,5547255464]

# ۱. موتور اول: Gemini 1.5 Flash (از طریق ورکر کلاودفلر شما)
def ask_gemini(prompt):
    model = "gemini-1.5-flash"
    # آدرس ورکر کلاودفلر شما دقیقاً در اینجا جایگذاری شد:
    url = f"https://gemini-worker.ilberich6831-cell.workers.dev/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return None
    return None

# ۲. موتور دوم: OpenRouter - DeepSeeks (سریع و سبک برای پاسخ‌های کوتاه و ریاضی)
def ask_openrouter_fast(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_FAST_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except:
        return None
    return None

# ۳. موتور سوم: OpenRouter - DeepSeek R1 (سنگین و استدلالی برای کارهای پیچیده)
def ask_openrouter_heavy(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_HEAVY_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except:
        return None
    return None

# سیستم هوشمند مسیریابی پیام‌ها (سیستم ۳ موتوره)
def generate_response(prompt):
    # الف) اگر پیام نیاز به استدلال سنگین دارد (کلمات کلیدی خاص) -> موتور سوم (Heavy)
    heavy_keywords = ['چرا', 'دلیل', 'ثابت کن', 'برنامه‌نویسی', 'کد', 'تحلیل']
    if any(keyword in prompt for keyword in heavy_keywords) or len(prompt) > 150:
        res = ask_openrouter_heavy(prompt)
        if res: return res

    # ب) اگر پیام محاسباتی یا فرمول ریاضی دارد -> موتور دوم (Fast)
    math_chars = ['+', '-', '*', '/', '=', '^', 'x', 'y', 'حل کن', 'ریاضی']
    if any(char in prompt for char in math_chars):
        res = ask_openrouter_fast(prompt)
        if res: return res

    # ج) پیام‌های عمومی، چت عادی و پیش‌فرض -> اول موتور اول (Gemini)
    res = ask_gemini(prompt)
    if res: return res

    # د) لایه‌های بک‌آپ و پشتیبان در صورت قطعی هر کدام
    res = ask_openrouter_fast(prompt)
    if res: return res
    
    res = ask_openrouter_heavy(prompt)
    if res: return res

    return "⚠️ سیستم شلوغ است. دوباره تلاش کن."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id in ALLOWED_USERS:
        bot.reply_to(message, "🤖 سیستم ۳ موتوره‌ی هوش مصنوعی فعال شد!\n\nآماده پاسخگویی به سوالات عمومی، محاسبات ریاضی و تحلیل‌های سنگین شما هستم. بپرس!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    sent_msg = bot.reply_to(message, "⏳ در حال پردازش توسط هوش مصنوعی...")
    user_prompt = message.text
    ai_response = generate_response(user_prompt)
    
    bot.edit_message_text(ai_response, chat_id=message.chat.id, message_id=sent_msg.message_id)

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + request.host + '/' + TOKEN)
    return "🤖 Gemix System Active...", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 10000)))
    

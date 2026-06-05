import os
import asyncio
import logging
from flask import Flask
from threading import Thread
import httpx  # کتابخانه ناهمگام برای بالا بردن سرعت ارتباط با هوش مصنوعی
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# فعال‌سازی لاگ برای بررسی وضعیت ربات در پنل رندر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ۱. وب‌سرور داخلی برای زنده نگه داشتن رندر ---
app = Flask('')

@app.route('/')
def home():
    return "MASHALLAH! The Bot is Active, Safe, and Super Fast."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ۲. فراخوانی امن کلیدها از تنظیمات سرور (Environment Variables) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
RENDER_URL = os.environ.get("RENDER_URL") 

# تعریف ۳ موتور هوش مصنوعی قدرتمند بر اساس نیاز
MODELS = {
    "CODING": "qwen/qwen-2.5-coder-32b-instruct", # غول کدنویسی و برنامه نویسی بدون محدودیت حجم
    "MATH": "deepseek/deepseek-r1",              # مدل استدلالی برای ریاضی و فیزیک
    "GENERAL": "google/gemini-flash-1.5"          # مدل فوق‌سریع برای چت‌های عمومی
}

# پرامپت مهندسی شده برای فهم دقیق کلمه "چطوری" و جلوگیری از احوال‌پرسی کاذب
SYSTEM_PROMPT = """تو یک دستیار هوشمند، بسیار باهوش و متخصص فنی هستی.
قانون حیاتی: کاربر کلماتی مثل 'چطور'، 'چطوری' یا 'چگونه' را برای پرسیدن روش انجام یک کار فنی یا آموزشی به کار می‌برد (مثلاً: چطوری بات بنویسم؟ چطوری مسئله را حل کنم؟).
هرگز و تحت هیچ شرایطی این کلمات را با احوال‌پرسی اشتباه نگیر! به هیچ وجه نگو 'من خوبم شما چطوری'. 
بلافاصله برو سراغ اصل مطلب و پاسخ فنی، الگوریتمی یا راهکار عملی را به صورت گام‌به‌گام و شیک به زبان فارسی توضیح بده."""

# --- ۳. سیستم پینگ خودکار داخلی برای بیدار نگه داشتن سرور ---
async def keep_alive_ping():
    await asyncio.sleep(30) # صبر برای لود شدن کامل سرور
    async with httpx.AsyncClient() as client:
        while True:
            try:
                if RENDER_URL and RENDER_URL.startswith("https"):
                    response = await client.get(RENDER_URL, timeout=10.0)
                    logger.info(f"Self-Ping successful! Status Code: {response.status_code}")
            except Exception as e:
                logger.warning(f"Self-Ping failed: {e}")
            
            # هر ۱۰ دقیقه یک‌بار پینگ می‌فرستد
            await asyncio.sleep(600)

# --- ۴. تابع ارتباطی کاملاً Async با OpenRouter (عامل اصلی حذف تاخیر ۱۰ ثانیه‌ای) ---
async def ask_openrouter_async(user_message, model_name):
    if not OPENROUTER_API_KEY:
        return "❌ خطا: کلید API اوپن‌روتر در تنظیمات رندر ست نشده است."
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com", 
        "X-Title": "Amir Architect Bot"
    }
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    }
    
    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            response_json = response.json()
            return response_json['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenRouter Error: {e}")
            return "❌ خطایی در پردازش هوش مصنوعی رخ داد. لطفاً مجدداً تلاش کنید."

# --- ۵. منطق تلگرام و تفکیک هوشمند پیام‌ها (Routing) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام امیر جان! معماری جدید، ۳ موتوره و ایمن ربات فعال شد.\n"
        "سیستم بدون تاخیر پیام‌ها را پردازش می‌کند. سوالت را بپرس:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # ارسال فوری وضعیت در حال تایپ به کاربر برای حس سرعت بالا
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # روتینگ پیش‌فرض روی مدل عمومی
    selected_model = MODELS["GENERAL"]
    
    # تفکیک هوشمند برای کدهای برنامه‌نویسی و طراحی وب
    if any(word in user_text.lower() for word in ["کد", "برنامه", "python", "html", "css", "سایت", "ساخت", "کدنویسی", "ربات"]):
        selected_model = MODELS["CODING"]
        logger.info(f"Routing to CODING model for chat_id {chat_id}")
    
    # تفکیک هوشمند برای مسائل ریاضی، فیزیک و محاسباتی
    elif any(word in user_text for word in ["حل", "فرمول", "ریاضی", "فیزیک", "محاسبه"]) or any(char.isdigit() for char in user_text):
        selected_model = MODELS["MATH"]
        logger.info(f"Routing to MATH model for chat_id {chat_id}")

    # گرفتن پاسخ از اوپن‌روتر بدون قفل شدن سرور
    reply_text = await ask_openrouter_async(user_text, selected_model)
    
    # ارسال ایمن پاسخ به تلگرام و جلوگیری از کرش‌های فرمت مارک‌داون
    try:
        await update.message.reply_text(reply_text, parse_mode="Markdown")
    except Exception as parse_error:
        logger.warning(f"Markdown failed, sending plain text: {parse_error}")
        await update.message.reply_text(reply_text)

# --- ۶. راه‌اندازی و اجرای همزمان کل سیستم ---
async def main():
    if not TELEGRAM_TOKEN:
        logger.error("Telegram Token NOT FOUND in Environment Variables!")
        return

    # اجرای وب‌سرور در ترید مستقل
    Thread(target=run_flask, daemon=True).start()
    
    # اجرای تسک پس‌زمینه پینگ خودکار
    asyncio.create_task(keep_alive_ping())

    # کانفیگ نهایی پایتون تلگرام بات
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Secure Bot is fully polling now...")
    
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped cleanly.")
        

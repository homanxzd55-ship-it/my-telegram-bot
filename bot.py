import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import Update
from aiogram.enums import ParseMode

# ==========================================
# 1. تنظیمات امنیتی و متغیرهای محیطی (Environment Variables)
# ==========================================
# به هیچ وجه توکن‌ها را مستقیماً در کد ننویسید! 
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # آدرس سایت رندر شما، مثال: https://my-bot.onrender.com

# دریافت 3 کلید API از محیط رندر
GEMINI_KEYS = [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3")
]
# حذف کلیدهای خالی (در صورتی که یکی را وارد نکردید)
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

if not BOT_TOKEN or not WEBHOOK_URL or not GEMINI_KEYS:
    raise ValueError("توکن ربات، آدرس وب‌هوک یا کلیدهای جمینای در تنظیمات رندر وارد نشده‌اند!")

# مسیر مخفی برای وب‌هوک جهت امنیت بیشتر (فقط تلگرام این آدرس را می‌داند)
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# ==========================================
# 2. کلاس مدیریت و چرخش کلیدهای جمینای (Load Balancing)
# ==========================================
class GeminiManager:
    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0
        # تنظیم پرامپت سیستم برای اینکه ربات مثل یک مهندس نرم‌افزار حرفه‌ای رفتار کند
        self.system_instruction = (
            "You are an expert Senior Software Engineer and coding assistant. "
            "Provide clean, well-documented, and efficient code. "
            "Explain your logic briefly. Answer in Persian unless the user asks for English."
        )

    def get_next_key(self):
        """کلید بعدی را برای توزیع بار (Round-Robin) برمی‌گرداند"""
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key

    async def generate_response(self, prompt: str) -> str:
        """ارسال درخواست به جمینای با قابلیت تست کلیدهای جایگزین در صورت خرابی"""
        for _ in range(len(self.keys)):
            current_key = self.get_next_key()
            genai.configure(api_key=current_key)
            
            # استفاده از مدل فلش که برای متن و کد بسیار سریع و بهینه است
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=self.system_instruction
            )
            
            try:
                # اجرای درخواست در یک ترد جداگانه تا سرور متوقف نشود
                response = await asyncio.to_thread(model.generate_content, prompt)
                return response.text
            except Exception as e:
                logging.error(f"Error with key starting with {current_key[:5]}: {e}")
                continue # اگر این کلید ارور داد (مثلا لیمیت شده بود)، برو کلید بعدی
                
        return "⚠️ متأسفانه در حال حاضر تمام کلیدهای هوش مصنوعی من به سقف مجاز رسیده‌اند یا خطایی رخ داده است. لطفا چند دقیقه دیگر تلاش کنید."

gemini_manager = GeminiManager(GEMINI_KEYS)

# ==========================================
# 3. راه‌اندازی تلگرام و سرور
# ==========================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ==========================================
# 4. هندلرهای تلگرام (منطق ربات)
# ==========================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "سلام! 👨‍💻\n"
        "من یک دستیار کدنویسی حرفه‌ای (بر پایه مدل جمینای) هستم.\n"
        "کافیه سوال برنامه‌نویسی، دیباگ یا قطعه کد خودت رو برام بفرستی تا کمکت کنم."
    )
    await message.reply(welcome_text)

@dp.message(F.text)
async def handle_coding_queries(message: types.Message):
    # ارسال وضعیت "در حال تایپ..." به کاربر
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # پیام اولیه برای اینکه کاربر بداند ربات در حال فکر کردن است
    wait_msg = await message.reply("⏳ در حال پردازش و نوشتن کد...")
    
    try:
        # دریافت پاسخ از جمینای
        ai_response = await gemini_manager.generate_response(message.text)
        
        # تلگرام محدودیت ۴۰۹۶ کاراکتر در هر پیام دارد. پیام‌های طولانی (مثل کدهای بلند) باید تکه‌تکه شوند.
        max_length = 4000
        parts = [ai_response[i:i+max_length] for i in range(0, len(ai_response), max_length)]
        
        for part in parts:
            # ارسال پیام (از فرمت مارک‌داون استفاده نمی‌کنیم تا کاراکترهای خاص کدها باعث ارور تلگرام نشوند)
            await message.reply(part)
            
    except Exception as e:
        logging.error(f"Telegram Send Error: {e}")
        await message.reply("❌ خطایی در ارسال پاسخ به وجود آمد.")
    finally:
        # پاک کردن پیام "در حال پردازش..."
        await wait_msg.delete()

# ==========================================
# 5. تنظیمات FastAPI برای Webhook و Render
# ==========================================
@app.on_event("startup")
async def on_startup():
    """این تابع هنگام روشن شدن سرور رندر اجرا می‌شود و وب‌هوک را تنظیم می‌کند"""
    webhook_info = await bot.get_webhook_info()
    target_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    
    if webhook_info.url != target_url:
        await bot.set_webhook(url=target_url, drop_pending_updates=True)
        logging.info(f"Webhook set to {target_url}")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """دریافت پیام‌ها از سرور تلگرام"""
    try:
        update_data = await request.json()
        update = Update(**update_data)
        await dp.feed_update(bot=bot, update=update)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """یک صفحه ساده برای اینکه UptimeRobot بتواند ربات را بیدار نگه دارد"""
    return {"status": "Bot is Running", "message": "The coding assistant is awake!"}

# این بخش فقط برای تست روی سیستم شخصی است. در رندر از دستورات استارت استفاده می‌شود.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
        

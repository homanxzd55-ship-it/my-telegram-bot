import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
from collections import defaultdict
from io import BytesIO

# کتابخانه‌های اصلی ربات و هوش مصنوعی
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from google import genai
from google.genai import types as genai_types
from PIL import Image

# ۱. پیکربندی سیستم لاگینگ پیشرفته برای دیباگ و امنیت پروپوزال
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AdvancedDevBot")

# ۲. دور زدن محدودیت پورت رندر (Render Port Keeper)
app = Flask('')

@app.route('/')
def home():
    return f"Bot is alive! Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def keep_alive_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# روشن کردن سرور فِیک در یک Thread مجزا
Thread(target=keep_alive_server, daemon=True).start()
logger.info("Keep-Alive server started successfully to prevent Render Port Timeout.")

# ۳. مدیریت امن توکن‌ها از طریق متغیرهای محیطی (Environment Variables)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# دریافت ۳ تا API Key جمینای برای جلوگیری از محدودیت درخواست (Rate Limit)
GEMINI_KEYS = [
    os.environ.get("GEMINI_KEY_1"),
    os.environ.get("GEMINI_KEY_2"),
    os.environ.get("GEMINI_KEY_3")
]

# فیلتر کردن کلیدهای خالی جهت پایداری سیستم
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

if not TOKEN:
    critical_error = "CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing!"
    logger.critical(critical_error)
    raise ValueError(critical_error)

if not GEMINI_KEYS:
    critical_error = "CRITICAL ERROR: At least one GEMINI_KEY must be provided!"
    logger.critical(critical_error)
    raise ValueError(critical_error)

# ۴. سیستم چرخشی پیشرفته مدیریت کلیدهای هوش مصنوعی (API Key Rotator)
class APIKeyRotator:
    def __init__(self, keys):
        self.keys = keys
        self.index = 0
        self.lock = asyncio.Lock()

    async def get_next_client(self) -> genai.Client:
        async with self.lock:
            key = self.keys[self.index]
            # چرخش ایندکس بین کلیدها
            self.index = (self.index + 1) % len(self.keys)
            logger.info(f"Rotating to API Key Index: {self.index} to balance load.")
            return genai.Client(api_key=key)

rotator = APIKeyRotator(GEMINI_KEYS)

# ۵. سیستم مدیریت حافظه و تاریخچه گفتگو به تفکیک کاربر (Session Handler)
class UserSessionManager:
    def __init__(self):
        # نگهداری سوابق چت به صورت ساختار یافته
        self.history = defaultdict(list)
        # سیستم ضد اسپم (Anti-Flood Rate Limiting) برای جلوگیری از مسدود سازی تلگرام
        self.last_request = defaultdict(lambda: datetime.min)
        # دستورالعمل سیستم فوق‌العاده قوی برای تخصصی کردن پاسخ‌های جمینای در حوزه کدنویسی
        self.system_instruction = (
            "You are a Senior Software Engineer, Software Architect, and Elite Code Debugger "
            "with over 20 years of experience. Your mission is to analyze complex code, discover "
            "hidden bugs, optimize memory leaks, and write clean, production-ready, efficient code. "
            "Always explain the 'why' behind your fixes using professional tech terminology. "
            "Format code blocks properly using markdown with the appropriate language specified."
        )

    def get_history(self, user_id: int):
        return self.history[user_id]

    def add_to_history(self, user_id: int, role: str, text: str):
        self.history[user_id].append({"role": role, "parts": [{"text": text}]})
        # نگهداری حداکثر ۲۰ پیام آخر برای مدیریت مصرف توکن و پردازش بهینه
        if len(self.history[user_id]) > 20:
            self.history[user_id] = self.history[user_id][-20:]

    def clear_history(self, user_id: int):
        if user_id in self.history:
            del self.history[user_id]

    def is_flooding(self, user_id: int) -> bool:
        # محدودیت ۳ ثانیه فاصله بین هر درخواست کاربر برای امنیت سرور
        now = datetime.now()
        if now - self.last_request[user_id] < timedelta(seconds=3):
            return True
        self.last_request[user_id] = now
        return False

session_manager = UserSessionManager()

# ۶. مقداردهی اولیه ربات با تنظیمات امنیتی ساختار ناهمگام (Async Bot Initialization)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# دستور /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"سلام *{user_name}* گرامی! 🚀\n\n"
        "به ربات تخصصی مهندسی نرم‌افزار و هوش مصنوعی توسعه‌دهندگان خوش آمدید.\n\n"
        "🔹 **قابلیت‌ها:**\n"
        "• تحلیل و دیباگ کدهای پیچیده کامپایلری\n"
        "• بهینه‌سازی کدهای چندرشته‌ای و معماری سیستم\n"
        "• خواندن اسکرین‌شات ارورها و حل باگ خودکار\n\n"
        "📝 برای شروع، کد یا سوال فنی خود را بفرستید. برای پاکسازی حافظه چت دستور /clear را بزنید."
    )
    await message.answer(welcome_text)

# دستور /clear برای ریست حافظه
@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    session_manager.clear_history(message.from_user.id)
    await message.answer("🧹 *حافظه چت شما با موفقیت پاک شد.* ربات آماده چالش‌های جدید است!")

# ۷. پردازنده هوشمند درخواست‌های متنی (Text Code Processor)
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text_query(message: types.Message):
    user_id = message.from_user.id
    
    # مکانیزم امنیتی ضد اسپم تلگرام
    if session_manager.is_flooding(user_id):
        await message.answer("⚠️ لطفاً کمی آرام‌تر! برای پایداری سرور، بین پیام‌ها ۳ ثانیه فاصله بگذارید.")
        return

    # ارسال وضعیت "در حال تایپ" به تلگرام جهت ایجاد تجربه کاربری عالی
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    status_msg = await message.answer("🤖 *در حال تحلیل کدهای شما توسط مغز هوش مصنوعی...*")

    try:
        # دریافت کلاینت بعدی از چرخنده کدهای گوگل
        client = await rotator.get_next_client()
        
        # بازیابی سوابق چت و چسباندن پیام جدید
        user_text = message.text
        chat_history = session_manager.get_history(user_id)
        
        # تبدیل تاریخچه محلی به قالب رسمی ساختار جمینای نوع داده Content
        contents = []
        for h in chat_history:
            contents.append(genai_types.Content(role=h["role"], parts=[genai_types.Part.from_text(text=h["parts"][0]["text"])]))
        
        # افزودن پیام فعلی کاربر
        contents.append(genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_text)]))

        # فراخوانی API به صورت کاملاً غیرمسدودکننده (Asynchronous Wrapped Exec)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model='gemini-1.5-pro',  # استفاده از قوی‌ترین مدل برای کدهای پیچیده
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=session_manager.system_instruction,
                    temperature=0.2, # کاهش خلاقیت برای افزایش دقت در کدهای فنی
                    max_output_tokens=4000
                )
            )
        )

        ai_response = response.text
        
        # ذخیره در حافظه لوکال سرور برای پیام‌های بعدی
        session_manager.add_to_history(user_id, "user", user_text)
        session_manager.add_to_history(user_id, "model", ai_response)

        # ارسال نهایی پاسخ به تلگرام و پاک کردن پیام وضعیت
        await status_msg.delete()
        
        # اگر پاسخ طولانی بود، تلگرام محدودیت ۴۰۹۶ کاراکتر دارد؛ آن را تکه‌تکه ارسال می‌کنیم
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await message.answer(ai_response[i:i+4000])
        else:
            await message.answer(ai_response)

    except Exception as e:
        logger.error(f"Error while processing text for user {user_id}: {str(e)}")
        await status_msg.edit_text("❌ متأسفانه مشکلی در پردازش کد رخ داد. لطفاً دوباره تلاش کنید.")

# ۸. پردازنده مولتی‌مدیا و بینایی ماشین برای اسکرین‌شات‌ها (Vision Error Processor)
@dp.message(F.photo)
async def handle_photo_query(message: types.Message):
    user_id = message.from_user.id
    
    if session_manager.is_flooding(user_id):
        await message.answer("⚠️ لطفاً بین ارسال درخواست‌ها کمی فاصله بگذارید.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    status_msg = await message.answer("📸 *اسکرین‌شات شما دریافت شد. در حال اسکن خطاهای تصویری...*")

    try:
        # ۱. دانلود فایل تصویر از سرورهای تلگرام در مموری بایت‌ها بدون ذخیره روی هارد دیسک (امنیت و سرعت بالاترا)
        photo = message.photo[-1] # انتخاب باکیفیت‌ترین نسخه عکس
        file_info = await bot.get_file(photo.file_id)
        
        file_buffer = BytesIO()
        await bot.download_file(file_info.file_path, file_buffer)
        file_buffer.seek(0)
        
        # ۲. باز کردن عکس با PIL Pillow
        img = Image.open(file_buffer)

        # کلاینت هوش مصنوعی چرخشی
        client = await rotator.get_next_client()
        
        caption = message.caption if message.caption else "این اسکرین‌شات از باگ یا محیط کدهای من است. آن را تحلیل کن و دقیقاً بگو مشکل کجاست و چطور حل می‌شود."

        # ۳. ارسال همزمان عکس و متن به مدل مولتی‌مدیال
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model='gemini-1.5-flash', # مدل فلش برای کارهای دیداری فوق‌العاده سریع و دقیق عمل می‌کند
                contents=[img, caption],
                config=genai_types.GenerateContentConfig(
                    system_instruction=session_manager.system_instruction,
                    temperature=0.3
                )
            )
        )

        ai_response = response.text
        
        # اضافه کردن خلاصه به تاریخچه متنی کاربر
        session_manager.add_to_history(user_id, "user", f"[ارسال تصویر با موضوع]: {caption}")
        session_manager.add_to_history(user_id, "model", ai_response)

        await status_msg.delete()
        
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await message.answer(ai_response[i:i+4000])
        else:
            await message.answer(ai_response)

    except Exception as e:
        logger.error(f"Error while processing photo for user {user_id}: {str(e)}")
        await status_msg.edit_text("❌ خطایی در خواندن تصویر یا پردازش آن توسط هوش مصنوعی رخ داد.")

# ۹. تابع اصلی راه اندازی کل سیستم با تضمین مدیریت خطاهای پولینگ
async def main():
    logger.info("Initializing Bot Polling Session...")
    try:
        # حذف هرگونه وب‌هوک قدیمی برای جلوگیری از اختلال در اتصال
        await bot.delete_webhook(drop_pending_updates=True)
        # استارت زدن حلقه اصلی اجرای ربات
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot execution stopped due to polling error: {str(e)}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    # اجرای پروژه در ساختار لوپ پایتون
    asyncio.run(main())
    

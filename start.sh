#!/bin/bash
python -c "
import os, time, telebot
TOKEN = os.environ.get('TELEGRAM_TOKEN')
RENDER_URL = os.environ.get('RENDER_URL')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
time.sleep(2)
result = bot.set_webhook(url=f'{RENDER_URL}/{TOKEN}')
print(f'Webhook set: {result}', flush=True)
"
gunicorn bot:app --bind 0.0.0.0:$PORT

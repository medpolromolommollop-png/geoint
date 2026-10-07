# -*- coding: utf-8 -*-
import os
import io
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import exifread
from aiohttp import web

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8951287292:AAGp2htMMyRI_SGUQYBqqc3yUWQ_5_Sn0s4')

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TEMP_DIR = 'temp_photos'
os.makedirs(TEMP_DIR, exist_ok=True)

# ... (все функции convert_to_degrees, extract_exif_pil, extract_exif_raw, get_gps_coords, get_datetime, get_device остаются без изменений) ...

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("📸 Кинь фото как *файл* — вытащу метаданные.", parse_mode='Markdown')

@dp.message_handler(content_types=['photo', 'document'])
async def handle_photo(message: types.Message):
    # ... (весь код обработки фото остаётся без изменений) ...
    pass

# === ДОБАВЛЕНО ДЛЯ RENDER WEB SERVICE ===
async def handle_ping(request):
    return web.Response(text="Bot is alive")

async def main():
    # Запускаем веб-сервер для пингов
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("HTTP сервер запущен на порту 10000")

    # Запускаем бота
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
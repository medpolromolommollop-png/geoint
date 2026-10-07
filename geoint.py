# -*- coding: utf-8 -*-
import os
import io
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import exifread

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8665318629:AAFqMMj2-ploC0M8pJAoqg2s1Us30MilzvY')

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TEMP_DIR = 'temp_photos'
os.makedirs(TEMP_DIR, exist_ok=True)


def convert_to_degrees(value):
    """Конвертация GPS-координат из EXIF в градусы."""
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)


def extract_exif_pil(path):
    """Извлечение EXIF через Pillow."""
    result = {}
    try:
        img = Image.open(path)
        exif_data = img._getexif()
        if not exif_data:
            return result
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'GPSInfo':
                gps = {}
                for gps_id, gps_val in value.items():
                    gps_tag = GPSTAGS.get(gps_id, gps_id)
                    gps[gps_tag] = gps_val
                result['GPSInfo'] = gps
            else:
                result[tag] = value
    except Exception as e:
        result['_error_pil'] = str(e)
    return result


def extract_exif_raw(path):
    """Извлечение EXIF через exifread (глубже, чем Pillow)."""
    result = {}
    try:
        with open(path, 'rb') as f:
            tags = exifread.process_file(f)
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
                    result[tag] = str(value)
    except Exception as e:
        result['_error_exifread'] = str(e)
    return result


def get_gps_coords(exif_pil):
    """Достаём GPS-координаты."""
    if 'GPSInfo' not in exif_pil:
        return None
    gps = exif_pil['GPSInfo']
    try:
        lat = convert_to_degrees(gps['GPSLatitude'])
        lon = convert_to_degrees(gps['GPSLongitude'])
        if gps.get('GPSLatitudeRef') == 'S':
            lat = -lat
        if gps.get('GPSLongitudeRef') == 'W':
            lon = -lon
        return lat, lon
    except Exception:
        return None


def get_datetime(exif_pil):
    """Достаём дату и время съёмки."""
    for key in ('DateTimeOriginal', 'DateTime', 'DateTimeDigitized'):
        if key in exif_pil:
            return str(exif_pil[key])
    return None


def get_device(exif_pil):
    """Достаём модель устройства."""
    make = exif_pil.get('Make', '')
    model = exif_pil.get('Model', '')
    return f'{make} {model}'.strip() or None


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "📸 *Геоинт-хелпер*\n\n"
        "Кинь мне фото — я вытащу ВСЕ метаданные:\n"
        "• GPS-координаты (с картой)\n"
        "• Дату и время съёмки\n"
        "• Модель телефона/камеры\n"
        "• Настройки (ISO, выдержка, диафрагма)\n"
        "• Всё, что зашито в EXIF\n\n"
        "⚠️ Работает только с оригинальным файлом.\n"
        "Telegram сжимает фото и удаляет EXIF.\n"
        "Отправляй *как файл* (скрепка → Файл).",
        parse_mode='Markdown'
    )


@dp.message_handler(content_types=['photo', 'document'])
async def handle_photo(message: types.Message):
    # Скачиваем фото
    if message.photo:
        file_id = message.photo[-1].file_id
        ext = 'jpg'
    else:
        file_id = message.document.file_id
        ext = (message.document.file_name or 'file.jpg').split('.')[-1]

    file = await bot.get_file(file_id)
    path = os.path.join(TEMP_DIR, f'{file_id}.{ext}')
    await file.download(path)

    # Анализ
    exif_pil = extract_exif_pil(path)
    exif_raw = extract_exif_raw(path)
    gps = get_gps_coords(exif_pil)
    dt = get_datetime(exif_pil)
    device = get_device(exif_pil)

    # Формируем ответ
    out = "📊 *Результат анализа*\n\n"

    if gps:
        lat, lon = gps
        out += f"🗺 *GPS:* `{lat:.6f}, {lon:.6f}`\n"
        out += f"🔗 [Google Maps](https://maps.google.com/?q={lat},{lon})\n"
        out += f"🔗 [Yandex Maps](https://yandex.ru/maps/?pt={lon},{lat}&z=18)\n"
        out += f"🔗 [OpenStreetMap](https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon})\n\n"
    else:
        out += "🗺 *GPS:* не найден в метаданных\n\n"

    if dt:
        out += f"🕐 *Время съёмки:* `{dt}`\n"

    if device:
        out += f"📱 *Устройство:* `{device}`\n"

    # Настройки съёмки
    settings = []
    for key, label in [
        ('FNumber', 'Диафрагма'),
        ('ExposureTime', 'Выдержка'),
        ('ISOSpeedRatings', 'ISO'),
        ('FocalLength', 'Фокус'),
        ('Flash', 'Вспышка'),
    ]:
        if key in exif_pil:
            settings.append(f"{label}: {exif_pil[key]}")
    if settings:
        out += "\n⚙️ *Настройки:*\n"
        for s in settings:
            out += f"  • {s}\n"

    # Все EXIF-теги
    out += "\n📋 *Полный EXIF (Pillow):*\n"
    count = 0
    for k, v in exif_pil.items():
        if k == 'GPSInfo':
            continue
        if count >= 30:
            out += f"  ... и ещё {len(exif_pil) - 30}\n"
            break
        out += f"  `{k}`: `{str(v)[:60]}`\n"
        count += 1

    # Дополнительные теги от exifread
    extra = {k: v for k, v in exif_raw.items() if k not in exif_pil}
    if extra:
        out += "\n📋 *Дополнительно (exifread):*\n"
        count = 0
        for k, v in list(extra.items())[:15]:
            out += f"  `{k}`: `{str(v)[:60]}`\n"
            count += 1

    # Проверка на отсутствие метаданных
    if not exif_pil and not exif_raw:
        out += "\n⚠️ *Метаданные отсутствуют полностью.*\n"
        out += "Фото прошло через Telegram/WhatsApp/Instagram — они вырезают EXIF."
    elif not gps and not dt and not device:
        out += "\n⚠️ *Полезных метаданных мало.*\n"
        out += "Возможно, фото сжато или отредактировано."

    # Обрезка до 4000 символов
    if len(out) > 4000:
        out = out[:3990] + '...'

    await message.answer(out, parse_mode='Markdown', disable_web_page_preview=True)

    # Удаляем временный файл
    try:
        os.remove(path)
    except Exception:
        pass


if __name__ == '__main__':
    from aiogram import executor
    print('Геоинт-хелпер запущен')
    executor.start_polling(dp, skip_updates=True)
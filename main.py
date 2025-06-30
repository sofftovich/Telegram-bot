import os
import asyncio
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

POST_INTERVAL = 60 * 60 * 2  # 2 часа

def parse_interval(interval_str):
    """Парсит интервал в формате: 1d 2h 30m или просто число (часы)"""
    if interval_str.isdigit():
        return int(interval_str) * 3600  # Если просто число - считаем часами
    
    total_seconds = 0
    days = re.search(r'(\d+)d', interval_str)
    hours = re.search(r'(\d+)h', interval_str)
    minutes = re.search(r'(\d+)m', interval_str)
    
    if days:
        total_seconds += int(days.group(1)) * 24 * 3600
    if hours:
        total_seconds += int(hours.group(1)) * 3600
    if minutes:
        total_seconds += int(minutes.group(1)) * 60
    
    return total_seconds if total_seconds > 0 else None

def format_interval(seconds):
    """Форматирует секунды в читаемый вид"""
    days = seconds // (24 * 3600)
    hours = (seconds % (24 * 3600)) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    
    return " ".join(parts) if parts else "0м"

SIGNATURE = '<a href="https://t.me/+oBc3uUiG9Y45ZDM6">Femboys</a>'

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

QUEUE_FILE = "queue.json"

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r") as f:
        return json.load(f)

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f)

@dp.message(F.content_type == "text")
async def handle_commands(message: Message):
    global POST_INTERVAL, CHANNEL_ID  # объявляем глобальные переменные в начале функции
    text = message.text.lower()
    
    if text == "/help":
        queue = load_queue()
        queue_status = f"В очереди: {len(queue)} фото" if queue else "Очередь пуста"
        channel_info = f"ID: {CHANNEL_ID}" if CHANNEL_ID else "Не настроен"
        help_text = f"""
🤖 <b>Бот для автопостинга фото</b>

📊 <b>Статус:</b> {queue_status}
⏰ <b>Интервал:</b> {format_interval(POST_INTERVAL)}
📢 <b>Канал:</b> {channel_info}

<b>📋 Основные команды:</b>
/help - показать это сообщение
/status - полный статус бота
/post - опубликовать одно фото сейчас

<b>⏰ Управление интервалом:</b>
/interval 2h - каждые 2 часа
/interval 1d 6h - каждые 1 день 6 часов
/interval 30m - каждые 30 минут
/interval 1 - каждый час (старый формат)

/📢 Управление каналом:
/channel - показать текущий канал
/setchannel -1001234567890 - установить ID канала

<b>🗂 Управление очередью:</b>
/clear - очистить всю очередь
/queue - показать все фото в очереди
/remove 1 - удалить фото по номеру

📸 Просто отправьте фото, чтобы добавить его в очередь
        """
        await message.reply(help_text)
    
    elif text == "/status":
        queue = load_queue()
        queue_status = f"В очереди: {len(queue)} фото" if queue else "Очередь пуста"
        channel_info = f"ID: {CHANNEL_ID}" if CHANNEL_ID else "❌ Не настроен"
        status_text = f"""
📊 <b>Статус бота:</b>

📸 <b>Очередь:</b> {queue_status}
⏰ <b>Интервал:</b> {format_interval(POST_INTERVAL)}
📢 <b>Канал:</b> {channel_info}
🤖 <b>Автопостинг:</b> {'✅ Активен' if CHANNEL_ID else '❌ Неактивен (нет канала)'}
        """
        await message.reply(status_text)
    
    elif text == "/post":
        queue = load_queue()
        if queue:
            file_id = queue.pop(0)
            try:
                await bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=SIGNATURE)
                save_queue(queue)
                await message.reply("✅ Фото отправлено в канал!")
            except Exception as e:
                queue.insert(0, file_id)
                save_queue(queue)
                await message.reply(f"❌ Ошибка при отправке: {e}")
        else:
            await message.reply("❌ Очередь пуста!")
    
    elif text.startswith("/interval "):
        try:
            interval_part = text.split(maxsplit=1)[1]
            new_interval = parse_interval(interval_part)
            
            if new_interval is None or new_interval < 60:
                await message.reply("❌ Интервал должен быть больше 1 минуты")
                return
                
            POST_INTERVAL = new_interval
            await message.reply(f"✅ Интервал изменен на {format_interval(POST_INTERVAL)}")
        except (IndexError, ValueError):
            await message.reply("""❌ Неправильный формат. Примеры:
/interval 2h - каждые 2 часа
/interval 1d 6h 30m - каждые 1 день 6 часов 30 минут
/interval 30m - каждые 30 минут""")
    
    elif text == "/clear":
        save_queue([])
        await message.reply("✅ Очередь очищена!")
    
    elif text == "/channel":
        if CHANNEL_ID:
            await message.reply(f"📢 Текущий канал: {CHANNEL_ID}")
        else:
            await message.reply("❌ Канал не настроен. Используйте /setchannel <ID>")
    
    elif text.startswith("/setchannel "):
        try:
            new_channel = text.split()[1]
            
            # Проверяем формат ID канала
            if not (new_channel.startswith('-') and new_channel[1:].isdigit()):
                await message.reply("❌ Неправильный формат ID канала. Должен начинаться с '-' и содержать только цифры")
                return
            
            CHANNEL_ID = new_channel
            await message.reply(f"✅ Канал изменен на: {CHANNEL_ID}")
            
        except IndexError:
            await message.reply("❌ Укажите ID канала. Пример: /setchannel -1001234567890")
    
    elif text == "/queue":
        queue = load_queue()
        if not queue:
            await message.reply("📭 Очередь пуста")
        else:
            queue_text = f"📋 <b>Очередь ({len(queue)} фото):</b>\n\n"
            for i, file_id in enumerate(queue[:10], 1):
                queue_text += f"{i}. {file_id[:20]}...\n"
            
            if len(queue) > 10:
                queue_text += f"\n... и еще {len(queue) - 10} фото"
            
            queue_text += "\n\n💡 Используйте /remove <номер> для удаления"
            await message.reply(queue_text)
    
    elif text.startswith("/remove "):
        try:
            queue = load_queue()
            index = int(text.split()[1]) - 1
            
            if 0 <= index < len(queue):
                removed = queue.pop(index)
                save_queue(queue)
                await message.reply(f"✅ Фото #{index + 1} удалено из очереди\nОсталось: {len(queue)}")
            else:
                await message.reply(f"❌ Неверный номер. В очереди {len(queue)} фото")
                
        except (IndexError, ValueError):
            await message.reply("❌ Укажите номер фото. Пример: /remove 1")

@dp.message(F.photo)
async def handle_photo(message: Message):
    file_id = message.photo[-1].file_id
    queue = load_queue()
    queue.append(file_id)
    save_queue(queue)
    await message.reply(f"✅ Фото добавлено в очередь! (Всего в очереди: {len(queue)})")

async def scheduled_posting():
    print(f"🤖 Запущен автопостинг. Интервал: {format_interval(POST_INTERVAL)}")
    print(f"📋 ID канала: {CHANNEL_ID}")
    
    while True:
        queue = load_queue()
        if queue:
            file_id = queue.pop(0)
            try:
                await bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=SIGNATURE)
                save_queue(queue)
                print(f"✅ Фото отправлено в канал. Осталось в очереди: {len(queue)}")
            except Exception as e:
                queue.insert(0, file_id)
                save_queue(queue)
                print(f"❌ Ошибка при отправке: {e}")
                print("💡 Проверьте права бота в канале и правильность ID канала")
        else:
            print("📭 Очередь пуста. Ожидание новых фото...")
        
        await asyncio.sleep(POST_INTERVAL)

async def main():
    print("🚀 Запуск бота...")
    print(f"🔑 Токен бота: {TOKEN[:10]}...")
    print(f"📢 ID канала: {CHANNEL_ID}")
    
    asyncio.create_task(scheduled_posting())
    
    print("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

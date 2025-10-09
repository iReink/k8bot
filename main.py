import asyncio
import random
import logging
import configparser
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from db import Database

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Чтение токена из token.ini ---
config = configparser.ConfigParser()
config.read("token.ini")
API_TOKEN = config.get("bot", "token")

# --- Инициализация бота и базы ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
db = Database()

# --- Массив приветствий ---
GREETINGS = [
    "Hello, {nick}! How are you today?",
    "Good to see you, {nick}. How is your day going?",
    "Welcome, {nick}! Hope you are having a productive day.",
    "Hi, {nick}! Excited to see you here. How are things?",
    "Greetings, {nick}! Ready to practice some English today?"
]




# --- Обработчик всех сообщений ---
@dp.message()
async def handle_message(message: types.Message):
    chat_name = getattr(message.chat, "title", message.chat.full_name)

    # --- Новый участник ---
    if message.new_chat_members:
        for new_user in message.new_chat_members:
            nick = f"@{new_user.username}" if new_user.username else new_user.full_name
            db.add_user(message.chat.id, new_user.id, new_user.full_name, nick)
            logger.info(f"Added new user {nick} ({new_user.id}) in chat '{chat_name}'")
            greeting = random.choice(GREETINGS).format(nick=nick)
            await message.answer(greeting)
            logger.info(f"Greeted user {nick} in chat '{chat_name}'")
        return

    # --- Определение типа сообщения ---
    msg_type = None
    text = None

    if message.text:
        msg_type = "text"
        text = message.text
    elif message.photo:
        msg_type = "photo"
        text = message.caption or ""
    elif message.voice:
        msg_type = "voice"
        text = message.caption or ""
    elif message.video:
        msg_type = "video"
        text = message.caption or ""
    elif message.sticker:
        msg_type = "sticker"
        text = message.sticker.emoji or ""
    elif message.document:
        msg_type = "document"
        text = message.caption or ""
    elif message.animation:
        msg_type = "gif"
        text = message.caption or ""
    elif message.audio:
        msg_type = "audio"
        text = message.caption or ""
    else:
        msg_type = "other"

    # --- Проверка и добавление пользователя ---
    if not db.user_exists(message.chat.id, message.from_user.id):
        nick = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        db.add_user(message.chat.id, message.from_user.id, message.from_user.full_name, nick)
        logger.info(f"Auto-added user {nick} ({message.from_user.id}) in chat '{chat_name}'")

    # --- Сохранение сообщения ---
    now = datetime.now()
    is_forwarded = message.forward_from is not None or message.forward_sender_name is not None
    db.add_message(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        message_id=message.message_id,
        text=text,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        msg_type=msg_type,
        is_forwarded=is_forwarded
    )

    logger.info(
        f"Saved {msg_type} message {message.message_id} from user {message.from_user.id} in chat '{chat_name}'"
    )



# --- Запуск бота ---
async def main():
    try:
        logger.info("Bot is starting...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Error while running bot: {e}")
    finally:
        await bot.session.close()
        db.close()
        logger.info("Bot stopped and database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())

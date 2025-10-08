import asyncio
import random
import logging
from datetime import datetime
import configparser

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types.message import ContentType
from db import Database

# --- Чтение токена из token.ini ---
config = configparser.ConfigParser()
config.read("token.ini")
API_TOKEN = config.get("bot", "token")

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Инициализация ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
db = Database()

# --- Массив приветствий ---
GREETINGS = [
    "Hello, {nick}! How are you today?",
    "We are greeting you, {nick}. How is your day going?",
    "Welcome, {nick}! Hope you are having a productive day.",
    "Hi, {nick}! Excited to see you here. How are things?",
    "Greetings, {nick}! Ready to practice some English today?"
]

# --- Хелпер отправки случайного приветствия ---
async def greet_user(message: types.Message):
    nick = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    chat_name = getattr(message.chat, "title", message.chat.full_name)
    greeting = random.choice(GREETINGS).format(nick=nick)
    await message.answer(greeting)
    logger.info(f"Greeted user {nick} in chat '{chat_name}'")

# --- Обработчик нового участника ---
@dp.message(content_types=ContentType.NEW_CHAT_MEMBERS)
async def new_member(message: types.Message):
    chat_name = getattr(message.chat, "title", message.chat.full_name)
    for new_user in message.new_chat_members:
        nick = f"@{new_user.username}" if new_user.username else new_user.full_name
        db.add_user(message.chat.id, new_user.id, new_user.full_name, nick)
        logger.info(f"Added new user {nick} ({new_user.id}) in chat '{chat_name}'")
        await greet_user(message)

# --- Обработчик всех текстовых сообщений и текстов с подписью ---
@dp.message(lambda m: m.content_type in [ContentType.TEXT, ContentType.PHOTO])
async def handle_message(message: types.Message):
    chat_name = getattr(message.chat, "title", message.chat.full_name)
    # Определяем текст для сохранения
    if message.content_type == ContentType.TEXT:
        text = message.text
    elif message.content_type == ContentType.PHOTO and message.caption:
        text = message.caption
    else:
        return  # Игнорируем все остальное

    # Проверяем наличие пользователя в базе
    if not db.user_exists(message.chat.id, message.from_user.id):
        nick = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        db.add_user(message.chat.id, message.from_user.id, message.from_user.full_name, nick)
        logger.info(f"Auto-added user {nick} ({message.from_user.id}) in chat '{chat_name}'")

    # Сохраняем сообщение
    now = datetime.now()
    db.add_message(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        message_id=message.message_id,
        text=text,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S")
    )
    logger.info(f"Saved message {message.message_id} from user {message.from_user.id} in chat '{chat_name}'")

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

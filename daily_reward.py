import asyncio
from datetime import datetime, timedelta
import random
from db import Database

# --- Настройки ---
REWARD_HOUR = 21       # час награждения (0-23)
REWARD_MINUTE = 0      # минуты
MOST_ACTIVE_REWARD = 10
LONGEST_MESSAGE_REWARD = 10

# --- Поздравительные фразы ---
MOST_ACTIVE_MESSAGES = [
    "{nick}, congratulations! You have the highest daily message count. You get {most_active_reward} koins.",
    "Hooray, {nick}! You've written the most messages in a day. You've earned {most_active_reward} koins.",
    "Wow, {nick}! You hold the record for the most messages in a day. You deserve {most_active_reward} koins."
]

LONGEST_MESSAGE_MESSAGES = [
    "Congrats, {nick}. You have written the longest message in a day. Your prize is {longest_message_reward} koins.",
    "{nick}, you wrote the longest message of the day! We're thrilled with your English! You get {longest_message_reward} koins."
]

# --- Корутина награждения ---
async def daily_reward_task(bot):
    db = Database()
    while True:
        now = datetime.now()
        reward_time_today = now.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        # если текущее время уже после награждения, рассчитываем на завтра
        if now >= reward_time_today:
            reward_time_today += timedelta(days=1)

        # сколько ждать до следующего награждения
        wait_seconds = (reward_time_today - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # --- диапазон вчера 23:00 -> сегодня 23:00 ---
        end_time = reward_time_today
        start_time = end_time - timedelta(days=1)

        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        # --- НАГРАЖДЕНИЕ ЗА САМЫЙ АКТИВНЫЙ ДЕНЬ ---
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT u.chat_id, u.user_id, u.nick, COUNT(m.message_id) as msg_count
            FROM messages m
            JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
            WHERE m.date || ' ' || m.time BETWEEN ? AND ?
            GROUP BY u.chat_id, u.user_id
            ORDER BY msg_count DESC
            LIMIT 1
        """, (start_str, end_str))
        most_active = cursor.fetchone()

        if most_active:
            chat_id, user_id, nick, _ = most_active
            db.add_koins(chat_id, user_id, MOST_ACTIVE_REWARD)
            db.log_reward(chat_id, user_id, "daily_most_active", MOST_ACTIVE_REWARD)
            message_text = random.choice(MOST_ACTIVE_MESSAGES).format(
                nick=nick, most_active_reward=MOST_ACTIVE_REWARD
            )
            await bot.send_message(chat_id, message_text)

        # --- НАГРАЖДЕНИЕ ЗА САМОЕ ДЛИННОЕ СООБЩЕНИЕ ---
        cursor.execute("""
            SELECT u.chat_id, u.user_id, u.nick, LENGTH(m.message_text) as msg_length
            FROM messages m
            JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
            WHERE m.date || ' ' || m.time BETWEEN ? AND ?
            ORDER BY msg_length DESC
            LIMIT 1
        """, (start_str, end_str))
        longest_message = cursor.fetchone()

        if longest_message:
            chat_id, user_id, nick, _ = longest_message
            db.add_koins(chat_id, user_id, LONGEST_MESSAGE_REWARD)
            db.log_reward(chat_id, user_id, "daily_longest_message", LONGEST_MESSAGE_REWARD)
            message_text = random.choice(LONGEST_MESSAGE_MESSAGES).format(
                nick=nick, longest_message_reward=LONGEST_MESSAGE_REWARD
            )
            await bot.send_message(chat_id, message_text)

        # --- Ждём следующий день ---
        await asyncio.sleep(1)  # небольшой sleep для предотвращения мгновенного повторного запуска

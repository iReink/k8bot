import asyncio
from datetime import datetime, timedelta
import random
from db import Database

# --- Настройки ---
REWARD_HOUR = 21
REWARD_MINUTE = 3
WEEKLY_REWARD = 20

# --- Поздравительные фразы ---
MOST_ACTIVE_MESSAGES = [
    "{nick} wrote the most messages this week. We give you {most_active_reward} koins."
]

LONGEST_MESSAGE_MESSAGES = [
    "The longest message of the week was written by {nick}."
]

# --- Корутина еженедельной награды ---
async def weekly_reward_task(bot):
    db = Database()
    last_reward_date = None  # дата последней награды

    while True:
        now = datetime.now()

        # следующее воскресенье
        reward_time = now.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)
        days_ahead = 6 - reward_time.weekday()  # 0 = Monday
        if days_ahead < 0:
            days_ahead += 7
        reward_time += timedelta(days=days_ahead)

        # если уже после награды — на следующее воскресенье
        if now >= reward_time:
            reward_time += timedelta(weeks=1)

        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # --- защита от двойной награды ---
        today = datetime.now().date()
        if last_reward_date == today:
            await asyncio.sleep(60)
            continue

        last_reward_date = today  # запоминаем дату, чтобы не выдать награду снова

        # диапазон сообщений
        end_time = reward_time
        start_time = end_time - timedelta(weeks=1)

        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor = db.conn.cursor()

        # --- Самый активный ---
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
            db.add_koins(chat_id, user_id, WEEKLY_REWARD)
            db.log_reward(chat_id, user_id, "weekly_most_active", WEEKLY_REWARD)
            message_text = random.choice(MOST_ACTIVE_MESSAGES).format(
                nick=nick, most_active_reward=WEEKLY_REWARD
            )
            await bot.send_message(chat_id, message_text)

        # --- Самое длинное сообщение ---
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
            db.add_koins(chat_id, user_id, WEEKLY_REWARD)
            db.log_reward(chat_id, user_id, "weekly_longest_message", WEEKLY_REWARD)
            message_text = random.choice(LONGEST_MESSAGE_MESSAGES).format(
                nick=nick, longest_message_reward=WEEKLY_REWARD
            )
            await bot.send_message(chat_id, message_text)

        # чтобы не сработало дважды из-за миллисекунд
        await asyncio.sleep(60)


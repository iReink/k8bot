import asyncio
from datetime import datetime, timedelta
import calendar
import random
from db import Database

# --- Настройки ---
REWARD_HOUR = 21
REWARD_MINUTE = 5
MONTHLY_REWARD = 50

# --- Поздравительные фразы ---
MOST_ACTIVE_MESSAGES = [
    "{nick} was the most active participant this month. He/She wrote {count} messages. Your award is {most_active_reward} koins."
]

LONGEST_MESSAGE_MESSAGES = [
    "The longest message this month came from {nick}."
]

# --- Корутина ежемесячной награды ---
async def monthly_reward_task(bot):
    db = Database()
    while True:
        now = datetime.now()

        # Последний день месяца
        last_day = calendar.monthrange(now.year, now.month)[1]
        reward_time = now.replace(day=last_day, hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        if now >= reward_time:
            # Переходим на следующий месяц
            if now.month == 12:
                reward_time = reward_time.replace(year=now.year+1, month=1, day=31)
            else:
                next_month = now.month + 1
                last_day_next_month = calendar.monthrange(now.year, next_month)[1]
                reward_time = reward_time.replace(month=next_month, day=last_day_next_month)

        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Диапазон сообщений: с прошлого награждения до текущего
        # Предположим, что награда в прошлом месяце была в то же время
        start_time = reward_time - timedelta(days=calendar.monthrange(reward_time.year, reward_time.month-1 if reward_time.month>1 else 12)[1])
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = reward_time.strftime("%Y-%m-%d %H:%M:%S")

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
            chat_id, user_id, nick, count = most_active  # теперь count = количество сообщений
            db.add_koins(chat_id, user_id, MONTHLY_REWARD)
            db.log_reward(chat_id, user_id, "monthly_most_active", MONTHLY_REWARD)
            message_text = random.choice(MOST_ACTIVE_MESSAGES).format(
                nick=nick,
                most_active_reward=MONTHLY_REWARD,
                count=count  # передаем количество сообщений
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
            db.add_koins(chat_id, user_id, MONTHLY_REWARD)
            db.log_reward(chat_id, user_id, "monthly_longest_message", MONTHLY_REWARD)
            message_text = random.choice(LONGEST_MESSAGE_MESSAGES).format(
                nick=nick, longest_message_reward=MONTHLY_REWARD
            )
            await bot.send_message(chat_id, message_text)

        await asyncio.sleep(60)

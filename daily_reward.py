import asyncio
from datetime import datetime, timedelta
from db import Database

# --- Настройки ---
REWARD_HOUR = 23       # час награждения (0-23)
REWARD_MINUTE = 37      # минуты

# награды за активность
FIRST_PLACE_REWARD = 3
SECOND_PLACE_REWARD = 2
THIRD_PLACE_REWARD = 1

# награда за длину сообщения
LONGEST_MESSAGE_REWARD = 1


# --- Формат сообщений ---
MOST_ACTIVE_MESSAGES = [
    "1st place — {nick} ({count1} messages, +{reward1} koins)",
    "2nd place — {nick} ({count2} messages, +{reward2} koins)",
    "3rd place — {nick} ({count3} messages, +{reward3} koin)"
]

LONGEST_MESSAGE_MESSAGE = (
    "The longest message in a day:\n"
    "{nick} ({count} characters, +{reward} koin)"
)


# --- Корутина ежедневного награждения ---
async def daily_reward_task(bot):
    db = Database()
    last_reward_date = None  # защита от двойной награды

    while True:
        now = datetime.now()
        reward_time_today = now.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        # если текущее время уже после награждения — переносим на завтра
        if now >= reward_time_today:
            reward_time_today += timedelta(days=1)

        # ожидание до следующего награждения
        wait_seconds = (reward_time_today - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # защита от двойного срабатывания
        today = datetime.now().date()
        if last_reward_date == today:
            await asyncio.sleep(60)
            continue
        last_reward_date = today

        # --- диапазон за последние 24 часа ---
        end_time = reward_time_today
        start_time = end_time - timedelta(days=1)

        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor = db.conn.cursor()

        # --- ТОП-3 по количеству сообщений ---
        cursor.execute("""
            SELECT u.chat_id, u.user_id, u.nick, COUNT(m.message_id) as msg_count
            FROM messages m
            JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
            WHERE m.date || ' ' || m.time BETWEEN ? AND ?
            GROUP BY u.chat_id, u.user_id
            ORDER BY msg_count DESC
            LIMIT 3
        """, (start_str, end_str))
        top_users = cursor.fetchall()

        if top_users:
            rewards = [FIRST_PLACE_REWARD, SECOND_PLACE_REWARD, THIRD_PLACE_REWARD]
            for idx, user_data in enumerate(top_users):
                chat_id, user_id, nick, msg_count = user_data
                reward = rewards[idx] if idx < len(rewards) else 0
                if reward <= 0:
                    continue

                db.add_koins(chat_id, user_id, reward)
                db.log_reward(chat_id, user_id, f"daily_most_active_place_{idx+1}", reward)

                message_text = MOST_ACTIVE_MESSAGES[idx].format(
                    nick=nick,
                    count1=msg_count, count2=msg_count, count3=msg_count,
                    reward1=reward, reward2=reward, reward3=reward
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
            chat_id, user_id, nick, msg_length = longest_message
            db.add_koins(chat_id, user_id, LONGEST_MESSAGE_REWARD)
            db.log_reward(chat_id, user_id, "daily_longest_message", LONGEST_MESSAGE_REWARD)

            message_text = LONGEST_MESSAGE_MESSAGE.format(
                nick=nick, count=msg_length, reward=LONGEST_MESSAGE_REWARD
            )
            await bot.send_message(chat_id, message_text)

        # ждём немного перед следующей итерацией
        await asyncio.sleep(60)

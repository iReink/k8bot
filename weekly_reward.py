import asyncio
from datetime import datetime, timedelta
import random
from db import Database

# --- Настройки ---
REWARD_HOUR = 21
REWARD_MINUTE = 3

# награды за 1–5 место
WEEKLY_REWARDS = [5, 4, 3, 2, 1]

# --- Фразы для награждения ---
PLACE_MESSAGES = [
    "1st place — {nick} ({count} messages, +{reward} koins)",
    "2nd place — {nick} ({count} messages, +{reward} koins)",
    "3rd place — {nick} ({count} messages, +{reward} koins)",
    "4th place — {nick} ({count} messages, +{reward} koins)",
    "5th place — {nick} ({count} messages, +{reward} koins)",
]


# --- Корутина еженедельной награды ---
async def weekly_reward_task(bot):
    db = Database()
    last_reward_date = None  # защита от повторной награды

    while True:
        now = datetime.now()

        # следующее воскресенье
        reward_time = now.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)
        days_ahead = 6 - reward_time.weekday()  # 0 = Monday
        if days_ahead < 0:
            days_ahead += 7
        reward_time += timedelta(days=days_ahead)

        # если уже после награды — переносим на следующее воскресенье
        if now >= reward_time:
            reward_time += timedelta(weeks=1)

        # ждём до времени награды
        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # защита от повторной награды в тот же день
        today = datetime.now().date()
        if last_reward_date == today:
            await asyncio.sleep(60)
            continue
        last_reward_date = today

        # диапазон сообщений за неделю
        end_time = reward_time
        start_time = end_time - timedelta(weeks=1)

        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor = db.conn.cursor()

        # --- Топ-5 по сообщениям ---
        cursor.execute("""
            SELECT u.chat_id, u.user_id, u.nick, COUNT(m.message_id) as msg_count
            FROM messages m
            JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
            WHERE m.date || ' ' || m.time BETWEEN ? AND ?
            GROUP BY u.chat_id, u.user_id
            ORDER BY msg_count DESC
            LIMIT 5
        """, (start_str, end_str))

        top_users = cursor.fetchall()

        if top_users:
            chat_id = top_users[0][0]
            await bot.send_message(chat_id, "🏆 **Weekly activity results:**")

            for i, user in enumerate(top_users):
                if i >= len(WEEKLY_REWARDS):
                    break
                chat_id, user_id, nick, msg_count = user
                reward = WEEKLY_REWARDS[i]

                db.add_koins(chat_id, user_id, reward)
                db.log_reward(chat_id, user_id, "weekly_most_active", reward)

                message_text = PLACE_MESSAGES[i].format(
                    nick=nick, count=msg_count, reward=reward
                )
                await bot.send_message(chat_id, message_text)

        # чтобы не повторялось мгновенно
        await asyncio.sleep(60)

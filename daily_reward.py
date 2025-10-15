import asyncio
from datetime import datetime, timedelta
from db import Database

# --- Настройки ---
REWARD_HOUR = 21
REWARD_MINUTE = 0

# награды за 1–3 места
DAILY_REWARDS = [3, 2, 1]


async def daily_reward_task(bot):
    db = Database()
    last_reward_date = None  # защита от повторной награды

    while True:
        now = datetime.now()
        reward_time = now.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        # если текущее время уже позже награды — перенести на завтра
        if now >= reward_time:
            reward_time += timedelta(days=1)

        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # защита от повторной награды за тот же день
        today = reward_time.date()
        if last_reward_date == today:
            await asyncio.sleep(60)
            continue
        last_reward_date = today

        start_str = reward_time.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        end_str = reward_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor = db.conn.cursor()

        # получаем список всех чатов
        cursor.execute("SELECT DISTINCT chat_id FROM messages")
        chats = [row[0] for row in cursor.fetchall()]

        for chat_id in chats:
            # --- Топ-3 по количеству сообщений ---
            cursor.execute("""
                SELECT u.user_id, u.nick, COUNT(m.message_id) as msg_count
                FROM messages m
                JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
                WHERE m.chat_id = ? AND m.date || ' ' || m.time BETWEEN ? AND ?
                GROUP BY u.user_id
                ORDER BY msg_count DESC
                LIMIT 3
            """, (chat_id, start_str, end_str))
            top_users = cursor.fetchall()

            if top_users:
                message_lines = ["The highest daily message count:"]

                def ordinal(n):
                    if 10 <= n % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
                    return f"{n}{suffix}"

                for i, user in enumerate(top_users):
                    user_id, nick, msg_count = user
                    reward = DAILY_REWARDS[i] if i < len(DAILY_REWARDS) else 0
                    db.add_koins(chat_id, user_id, reward)
                    db.log_reward(chat_id, user_id, "daily_most_active", reward)

                    place_str = ordinal(i + 1)
                    koin_word = "koin" if reward == 1 else "koins"
                    message_lines.append(f"{place_str} place — {nick} ({msg_count} messages, +{reward} {koin_word})")

                await bot.send_message(chat_id, "\n".join(message_lines))

        await asyncio.sleep(60)

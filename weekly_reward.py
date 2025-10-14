import asyncio
from datetime import datetime, timedelta
from db import Database

# --- Настройки ---
REWARD_HOUR = 21
REWARD_MINUTE = 3

# награды за 1–5 места
WEEKLY_REWARDS = [5, 4, 3, 2, 1]

# награда за самое длинное сообщение
LONGEST_MESSAGE_REWARD = 5

def ordinal(n):
    # преобразование числа в порядковое: 1 → 1st, 2 → 2nd, 3 → 3rd, 4 → 4th
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# --- Корутина еженедельной награды ---
async def weekly_reward_task(bot):
    db = Database()
    last_reward_date = None  # защита от повторной награды

    while True:
        now = datetime.now()

        # следующее воскресенье
        reward_time = now.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)
        days_ahead = 6 - reward_time.weekday()
        if days_ahead < 0:
            days_ahead += 7
        reward_time += timedelta(days=days_ahead)

        if now >= reward_time:
            reward_time += timedelta(weeks=1)

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
        message_lines = []

        if top_users:
            message_lines.append("The highest weekly message count:")
            chat_id = top_users[0][0]

            for i, user in enumerate(top_users):
                chat_id, user_id, nick, msg_count = user
                reward = WEEKLY_REWARDS[i] if i < len(WEEKLY_REWARDS) else 0

                db.add_koins(chat_id, user_id, reward)
                db.log_reward(chat_id, user_id, f"weekly_most_active_place_{i+1}", reward)

                place_str = ordinal(i + 1)
                message_lines.append(f"{place_str} place — {nick} ({msg_count} messages, +{reward} koins)")

            # --- Самое длинное сообщение недели (по словам) ---
            cursor.execute("""
                SELECT u.chat_id, u.user_id, u.nick, 
                       LENGTH(m.message_text) - LENGTH(REPLACE(m.message_text, ' ', '')) + 1 AS word_count
                FROM messages m
                JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
                WHERE m.date || ' ' || m.time BETWEEN ? AND ?
                ORDER BY word_count DESC
                LIMIT 1
            """, (start_str, end_str))

            longest_message = cursor.fetchone()
            if longest_message:
                chat_id, user_id, nick, word_count = longest_message
                db.add_koins(chat_id, user_id, LONGEST_MESSAGE_REWARD)
                db.log_reward(chat_id, user_id, "weekly_longest_message", LONGEST_MESSAGE_REWARD)

                message_lines.append("")
                message_lines.append("📝 The longest message in a week:")
                message_lines.append(f"{nick} ({word_count} words, +{LONGEST_MESSAGE_REWARD} koins)")

            # Отправка одного сообщения
            text = "\n".join(message_lines)
            await bot.send_message(chat_id, text)

        await asyncio.sleep(60)

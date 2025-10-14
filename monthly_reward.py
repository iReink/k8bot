import asyncio
from datetime import datetime, timedelta
import calendar
from db import Database

REWARD_HOUR = 21
REWARD_MINUTE = 5
MONTHLY_REWARDS = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
LONGEST_MESSAGE_REWARD = 10


async def monthly_reward_task(bot):
    db = Database()
    last_reward_month = None

    while True:
        now = datetime.now()

        last_day = calendar.monthrange(now.year, now.month)[1]
        reward_time = now.replace(day=last_day, hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        if now >= reward_time:
            next_month = 1 if now.month == 12 else now.month + 1
            next_year = now.year + 1 if now.month == 12 else now.year
            last_day_next = calendar.monthrange(next_year, next_month)[1]
            reward_time = reward_time.replace(year=next_year, month=next_month, day=last_day_next)

        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        this_month = (reward_time.year, reward_time.month)
        if last_reward_month == this_month:
            await asyncio.sleep(60)
            continue
        last_reward_month = this_month

        start_time = reward_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = reward_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor = db.conn.cursor()
        cursor.execute("SELECT DISTINCT chat_id FROM messages")
        chats = [row[0] for row in cursor.fetchall()]

        def ordinal(n):
            if 10 <= n % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            return f"{n}{suffix}"

        for chat_id in chats:
            # --- Топ-10 по сообщениям ---
            cursor.execute("""
                SELECT u.user_id, u.nick, COUNT(m.message_id) as msg_count
                FROM messages m
                JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
                WHERE m.chat_id = ? AND m.date || ' ' || m.time BETWEEN ? AND ?
                GROUP BY u.user_id
                ORDER BY msg_count DESC
                LIMIT 10
            """, (chat_id, start_str, end_str))
            top_users = cursor.fetchall()

            message_lines = []

            if top_users:
                message_lines.append("The highest monthly message count:")
                for i, user in enumerate(top_users):
                    user_id, nick, msg_count = user
                    reward = MONTHLY_REWARDS[i] if i < len(MONTHLY_REWARDS) else 0
                    db.add_koins(chat_id, user_id, reward)
                    db.log_reward(chat_id, user_id, "monthly_most_active", reward)

                    place_str = ordinal(i + 1)
                    koin_word = "koin" if reward == 1 else "koins"
                    message_lines.append(f"{place_str} place — {nick} ({msg_count} messages, +{reward} {koin_word})")

            # --- Самое длинное сообщение ---
            cursor.execute("""
                SELECT u.user_id, u.nick, LENGTH(m.message_text) - LENGTH(REPLACE(m.message_text, ' ', '')) + 1 as word_count
                FROM messages m
                JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
                WHERE m.chat_id = ? AND m.date || ' ' || m.time BETWEEN ? AND ?
                ORDER BY word_count DESC
                LIMIT 1
            """, (chat_id, start_str, end_str))
            longest_message = cursor.fetchone()

            if longest_message:
                user_id, nick, word_count = longest_message
                db.add_koins(chat_id, user_id, LONGEST_MESSAGE_REWARD)
                db.log_reward(chat_id, user_id, "monthly_longest_message", LONGEST_MESSAGE_REWARD)
                message_lines.append("\nThe longest message in a month:")
                message_lines.append(f"{nick} ({word_count} words, +{LONGEST_MESSAGE_REWARD} koins)")

            if message_lines:
                await bot.send_message(chat_id, "\n".join(message_lines))

        await asyncio.sleep(60)

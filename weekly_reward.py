import asyncio
from datetime import datetime, timedelta
from db import Database

REWARD_HOUR = 21
REWARD_MINUTE = 2
WEEKLY_REWARDS = [5, 4, 3, 2, 1]
LONGEST_MESSAGE_REWARD = 5


async def weekly_reward_task(bot):
    db = Database()
    last_reward_week = None

    while True:
        now = datetime.now()

        # ближайшее воскресенье
        days_until_sunday = (6 - now.weekday()) % 7
        reward_time = now + timedelta(days=days_until_sunday)
        reward_time = reward_time.replace(hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        if now >= reward_time:
            reward_time += timedelta(weeks=1)

        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        this_week = reward_time.isocalendar()[1]
        if last_reward_week == this_week:
            await asyncio.sleep(60)
            continue
        last_reward_week = this_week

        start_time = reward_time - timedelta(days=7)
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
            # --- Топ-5 по активности ---
            cursor.execute("""
                SELECT u.user_id, u.nick, COUNT(m.message_id) as msg_count
                FROM messages m
                JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
                WHERE m.chat_id = ? AND m.date || ' ' || m.time BETWEEN ? AND ?
                GROUP BY u.user_id
                ORDER BY msg_count DESC
                LIMIT 5
            """, (chat_id, start_str, end_str))
            top_users = cursor.fetchall()

            message_lines = []

            if top_users:
                message_lines.append("The highest weekly message count:")
                for i, user in enumerate(top_users):
                    user_id, nick, msg_count = user
                    reward = WEEKLY_REWARDS[i] if i < len(WEEKLY_REWARDS) else 0
                    db.add_koins(chat_id, user_id, reward)
                    db.log_reward(chat_id, user_id, "weekly_most_active", reward)

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
                db.log_reward(chat_id, user_id, "weekly_longest_message", LONGEST_MESSAGE_REWARD)
                message_lines.append("\nThe longest message in a week:")
                message_lines.append(f"{nick} ({word_count} words, +{LONGEST_MESSAGE_REWARD} koins)")

            if message_lines:
                await bot.send_message(chat_id, "\n".join(message_lines))

        await asyncio.sleep(60)

import asyncio
from datetime import datetime, timedelta
import calendar
from db import Database

# --- Настройки ---
REWARD_HOUR = 21
REWARD_MINUTE = 5

# награды за 1–10 место
MONTHLY_REWARDS = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

# награда за самое длинное сообщение месяца
LONGEST_MESSAGE_REWARD = 10


# --- Корутина ежемесячной награды ---
async def monthly_reward_task(bot):
    db = Database()
    last_reward_month = None  # защита от повторной награды

    while True:
        now = datetime.now()

        # последний день текущего месяца
        last_day = calendar.monthrange(now.year, now.month)[1]
        reward_time = now.replace(day=last_day, hour=REWARD_HOUR, minute=REWARD_MINUTE, second=0, microsecond=0)

        # если время уже прошло — переходим на конец следующего месяца
        if now >= reward_time:
            next_month = 1 if now.month == 12 else now.month + 1
            next_year = now.year + 1 if now.month == 12 else now.year
            last_day_next_month = calendar.monthrange(next_year, next_month)[1]
            reward_time = reward_time.replace(year=next_year, month=next_month, day=last_day_next_month)

        # ждём до времени награды
        wait_seconds = (reward_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # защита от повторной награды в том же месяце
        this_month = (reward_time.year, reward_time.month)
        if last_reward_month == this_month:
            await asyncio.sleep(60)
            continue
        last_reward_month = this_month

        # диапазон сообщений за месяц
        start_time = reward_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = reward_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor = db.conn.cursor()

        # --- Топ-10 по активности ---
        cursor.execute("""
            SELECT u.chat_id, u.user_id, u.nick, COUNT(m.message_id) AS msg_count
            FROM messages m
            JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
            WHERE m.date || ' ' || m.time BETWEEN ? AND ?
            GROUP BY u.chat_id, u.user_id
            ORDER BY msg_count DESC
            LIMIT 10
        """, (start_str, end_str))

        top_users = cursor.fetchall()

        # --- Самое длинное сообщение месяца ---
        cursor.execute("""
            SELECT u.chat_id, u.user_id, u.nick, m.text, LENGTH(m.text) - LENGTH(REPLACE(m.text, ' ', '')) + 1 AS word_count
            FROM messages m
            JOIN users u ON m.chat_id = u.chat_id AND m.user_id = u.user_id
            WHERE m.date || ' ' || m.time BETWEEN ? AND ?
            ORDER BY word_count DESC
            LIMIT 1
        """, (start_str, end_str))

        longest_msg = cursor.fetchone()

        if not top_users and not longest_msg:
            await asyncio.sleep(60)
            continue

        chat_id = top_users[0][0] if top_users else longest_msg[0]
        message_lines = ["🌟 **Monthly results:**"]

        # --- Формирование списка топ-10 ---
        if top_users:
            message_lines.append("\n**Top active users:**")
            for i, user in enumerate(top_users):
                if i >= len(MONTHLY_REWARDS):
                    break
                chat_id, user_id, nick, msg_count = user
                reward = MONTHLY_REWARDS[i]

                db.add_koins(chat_id, user_id, reward)
                db.log_reward(chat_id, user_id, "monthly_most_active", reward)

                place = f"{i+1}st" if i == 0 else f"{i+1}nd" if i == 1 else f"{i+1}rd" if i == 2 else f"{i+1}th"
                message_lines.append(f"{place} place — {nick} ({msg_count} messages, +{reward} koins)")

        # --- Самое длинное сообщение ---
        if longest_msg:
            chat_id, user_id, nick, text, word_count = longest_msg
            db.add_koins(chat_id, user_id, LONGEST_MESSAGE_REWARD)
            db.log_reward(chat_id, user_id, "monthly_longest_message", LONGEST_MESSAGE_REWARD)
            message_lines.append(
                f"\n📝 Longest message — {nick} ({word_count} words, +{LONGEST_MESSAGE_REWARD} koins)"
            )

        # отправляем всё одним сообщением
        await bot.send_message(chat_id, "\n".join(message_lines))

        # чтобы не сработало дважды подряд
        await asyncio.sleep(60)

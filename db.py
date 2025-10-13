import sqlite3
import re

DB_PATH = "stats.db"

# --- Сообщения от них будут игнорироваться ---


class Database:
    ignored_users = [749027951]

    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

    # --- Пользователи ---
    def add_user(self, chat_id: int, user_id: int, name: str, nick: str):
        if nick and not nick.startswith("@"):
            nick = f"@{nick}"
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (chat_id, user_id, name, nick)
            VALUES (?, ?, ?, ?)
        """, (chat_id, user_id, name, nick))
        self.conn.commit()

    def user_exists(self, chat_id: int, user_id: int) -> bool:
        self.cursor.execute("""
            SELECT 1 FROM users WHERE chat_id=? AND user_id=?
        """, (chat_id, user_id))
        return self.cursor.fetchone() is not None

    # --- Сообщения ---
    def add_message(self, chat_id, user_id, message_id, text, date, time, msg_type, is_forwarded=False):
        # Игнорировать пересланные сообщения
        if is_forwarded:
            print(f"⏩ Ignored forwarded message from user {user_id}")
            return

        # Игнорировать определённых пользователей
        if user_id in self.ignored_users:
            print(f"🚫 Ignored message from ignored user {user_id}")
            return

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO messages 
            (chat_id, user_id, message_id, message_text, date, time, type, is_english)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, message_id, text, date, time, msg_type, self.is_english(text))
        )
        self.conn.commit()

    # --- Проверка текста на английский ---
    @staticmethod
    def is_english(text: str) -> int:
        cyrillic = len(re.findall(r'[а-яА-Я]', text))
        latin = len(re.findall(r'[a-zA-Z]', text))
        return 1 if latin >= 3 and cyrillic <= 2 else 0

    def close(self):
        self.conn.close()

    def add_koins(self, chat_id: int, user_id: int, amount: int):
        """
        Увеличивает баланс коинов пользователя на указанное значение.

        :param chat_id: ID чата
        :param user_id: ID пользователя
        :param amount: количество коинов для добавления (может быть отрицательным для списания)
        """
        cursor = self.conn.cursor()

        # Проверяем, есть ли пользователь в базе
        cursor.execute(
            "SELECT koins FROM users WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        result = cursor.fetchone()
        if result is None:
            # Если пользователя нет, можно либо создать его, либо просто выйти
            # Здесь создадим его с начальными коинами равными amount
            cursor.execute(
                "INSERT INTO users (chat_id, user_id, name, nick, koins) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, "Unknown", f"@user{user_id}", amount)
            )
            self.conn.commit()
            return

        # Если пользователь есть, увеличиваем коинов
        new_balance = result[0] + amount
        cursor.execute(
            "UPDATE users SET koins = ? WHERE chat_id = ? AND user_id = ?",
            (new_balance, chat_id, user_id)
        )
        self.conn.commit()

    def log_reward(self, chat_id: int, user_id: int, reward: str, amount: int):
        """
        Добавляет запись в таблицу reward_log о начисленной награде.

        :param chat_id: ID чата
        :param user_id: ID пользователя
        :param reward: Тип/название награды (например, 'daily_most_active')
        :param amount: Количество коинов, начисленных за награду
        """
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO reward_log (chat_id, user_id, date, time, reward, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chat_id, user_id, date_str, time_str, reward, amount))
        self.conn.commit()

    # Получить баланс пользователя
    def get_balance(self, chat_id: int, user_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT koins FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        result = cursor.fetchone()
        return result[0] if result else 0

    # Добавить запись в лог магазина
    def log_shop_purchase(self, chat_id: int, user_id: int, item_name: str):
        from datetime import datetime
        now = datetime.now()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO shop_log (chat_id, user_id, date, time, item_name)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), item_name))
        self.conn.commit()



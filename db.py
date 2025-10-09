import sqlite3
import re

DB_PATH = "stats.db"

class Database:
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
    def add_message(self, chat_id, user_id, message_id, text, date, time, msg_type):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO messages 
            (chat_id, user_id, message_id, message_text, date, time, type, is_english)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, message_id, text, date, time, msg_type, self.is_english_text(text))
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

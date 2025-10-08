import sqlite3

# Имя файла базы данных
DB_NAME = "stats.db"

def create_tables():
    # Подключаемся к базе (если файла нет — он создастся автоматически)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица сообщений
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        message_text TEXT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        PRIMARY KEY (chat_id, user_id, message_id)
    );
    """)

    # Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        name TEXT,
        nick TEXT,
        koins INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, user_id)
    );
    """)

    # Сохраняем изменения и закрываем соединение
    conn.commit()
    conn.close()
    print("Таблицы успешно созданы или уже существуют.")

if __name__ == "__main__":
    create_tables()

import sqlite3

DB_NAME = "stats.db"

def create_shop_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица товаров магазина
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_items (
        item_name TEXT PRIMARY KEY,
        price INTEGER NOT NULL,
        response_text TEXT,
        sticker_file_id TEXT
    );
    """)

    # Таблица логов покупок
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_log (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        item_name TEXT NOT NULL,
        amount INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id, date, time, item_name)
    );
    """)

    conn.commit()
    conn.close()
    print("Таблицы 'shop_items' и 'shop_log' успешно созданы или уже существуют.")

if __name__ == "__main__":
    create_shop_tables()

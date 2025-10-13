import sqlite3

DB_NAME = "stats.db"

def create_shop_tables_and_insert_items():
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

    # Таблица логов покупок (без поля amount)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_log (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        item_name TEXT NOT NULL,
        PRIMARY KEY (chat_id, user_id, date, time, item_name)
    );
    """)

    # Добавление товаров в магазин
    shop_items = [
        ("cappuccino", 2, "Here's your cappuccino. Enjoy!", "CAACAgIAAyEFAASjKavKAAILDGjtFSC5Vwt8gdrqVcQioyNYB0fBAAKLhwACSN9pS7dWBha3mj-PNgQ"),
        ("regular coffee", 1, "Your regular coffee is ready", "CAACAgIAAyEFAASjKavKAAILCmjtFQ1XrJF9ogxyMtUFcgT7zA-vAAJqfwACq5JxSz3gXCEUzl2ONgQ"),
        ("pastel de nata", 1, "Good choice! Here's your pastel de nata", "CAACAgIAAyEFAASjKavKAAILDmjtFTSR6C5gEZhkrwXT0XuXQBRBAAKVggACBBZpS4GBz0PyVczoNgQ"),
        ("water with lemon", 0, "Your water with lemon, have a nice day!", None)
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO shop_items (item_name, price, response_text, sticker_file_id)
    VALUES (?, ?, ?, ?);
    """, shop_items)

    conn.commit()
    conn.close()
    print("Таблицы 'shop_items' и 'shop_log' созданы, товары добавлены.")

if __name__ == "__main__":
    create_shop_tables_and_insert_items()

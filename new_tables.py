import sqlite3

DB_NAME = "stats.db"

def remove_amount_from_shop_log():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Создаём новую таблицу без поля amount
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_log_new (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        item_name TEXT NOT NULL,
        PRIMARY KEY (chat_id, user_id, date, time, item_name)
    );
    """)

    # Копируем данные из старой таблицы
    cursor.execute("""
    INSERT OR IGNORE INTO shop_log_new (chat_id, user_id, date, time, item_name)
    SELECT chat_id, user_id, date, time, item_name FROM shop_log;
    """)

    # Удаляем старую таблицу
    cursor.execute("DROP TABLE shop_log;")

    # Переименовываем новую таблицу
    cursor.execute("ALTER TABLE shop_log_new RENAME TO shop_log;")

    conn.commit()
    conn.close()
    print("Поле 'amount' успешно удалено из таблицы 'shop_log'.")

if __name__ == "__main__":
    remove_amount_from_shop_log()

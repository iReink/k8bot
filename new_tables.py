import sqlite3

DB_NAME = "stats.db"

def add_is_english_column():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверяем, есть ли уже столбец is_english
    cursor.execute("PRAGMA table_info(messages);")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_english" not in columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_english INTEGER DEFAULT 0;")
        print("Столбец 'is_english' добавлен в таблицу messages.")
    else:
        print("Столбец 'is_english' уже существует.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_is_english_column()

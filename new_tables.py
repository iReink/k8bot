import sqlite3

DB_NAME = "stats.db"

def add_type_column():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверяем, есть ли уже столбец type
    cursor.execute("PRAGMA table_info(messages);")
    columns = [col[1] for col in cursor.fetchall()]
    if "type" not in columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN type TEXT;")
        print("Столбец 'type' добавлен в таблицу messages.")
    else:
        print("Столбец 'type' уже существует.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_type_column()

import sqlite3

DB_NAME = "stats.db"

def create_reward_log_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reward_log (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        reward TEXT NOT NULL,
        amount INTEGER NOT NULL,
        PRIMARY KEY (chat_id, user_id, date, time, reward)
    );
    """)

    conn.commit()
    conn.close()
    print("Таблица 'reward_log' успешно создана или уже существует.")

if __name__ == "__main__":
    create_reward_log_table()

import sqlite3

DB_NAME = "stats.db"

def update_shop_responses_with_name():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    updates = [
        ("{name}, here's your cappuccino. Enjoy!", "cappuccino"),
        ("{name}, your regular coffee is ready.", "regular coffee"),
        ("Good choice, {name}! Here's your pastel de nata.", "pastel de nata"),
    ]

    for text, item_name in updates:
        cursor.execute("""
        UPDATE shop_items
        SET response_text = ?
        WHERE item_name = ?;
        """, (text, item_name))

    conn.commit()
    conn.close()
    print("Фразы-ответы успешно обновлены с добавлением {name}.")

if __name__ == "__main__":
    update_shop_responses_with_name()

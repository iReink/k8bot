from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from db import Database
from datetime import datetime

db = Database()
router = Router()  # создаём роутер для модуля shop

# --- Вспомогательная функция для правильного окончания ---
def plural_koins(amount: int) -> str:
    return "koin" if amount == 1 else "koins"

# --- Команда /shop ---
@router.message(commands=["shop"])
async def shop_command_handler(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    balance = db.get_balance(chat_id, user_id)

    text = f"K8 coffee shop\n\nYour balance is {balance} {plural_koins(balance)}."

    # Получаем все товары из магазина
    cursor = db.conn.cursor()
    cursor.execute("SELECT item_name, price FROM shop_items")
    items = cursor.fetchall()

    keyboard = InlineKeyboardMarkup(row_width=1)
    for item_name, price in items:
        button_text = f"{item_name} — {price} {plural_koins(price)}"
        keyboard.add(InlineKeyboardButton(text=button_text, callback_data=f"shop_buy:{item_name}"))

    await message.answer(text, reply_markup=keyboard)

# --- Обработка нажатия на кнопку покупки ---
@router.callback_query(lambda c: c.data.startswith("shop_buy:"))
async def shop_buy_callback_handler(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    item_name = callback.data.split(":", 1)[1]

    cursor = db.conn.cursor()
    cursor.execute("SELECT price, response_text, sticker_file_id FROM shop_items WHERE item_name=?", (item_name,))
    item = cursor.fetchone()

    if not item:
        await callback.answer("Item not found!", show_alert=True)
        return

    price, response_text, sticker_file_id = item
    balance = db.get_balance(chat_id, user_id)

    if balance < price:
        await callback.answer(
            "Not enough coins! Be more active in chat to earn more.", show_alert=True
        )
        return

    # списываем баланс
    db.deduct_balance(chat_id, user_id, price)

    # удаляем сообщение с магазином
    await callback.message.delete()

    # отправляем ответ и/или стикер
    if response_text:
        await callback.message.answer(response_text)
    if sticker_file_id:
        await callback.message.answer_sticker(sticker_file_id)

    # логируем покупку
    now = datetime.now()
    db.log_shop_purchase(chat_id, user_id, item_name)

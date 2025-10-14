from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import Database
from datetime import datetime
from aiogram.filters import Command
from aiogram import F

def register_shop_handlers(dp):
    @dp.message(F.text.startswith("/shop"))
    async def shop_command_handler(message: types.Message):
        db = Database()
        chat_id = message.chat.id
        user_id = message.from_user.id

        balance = db.get_balance(chat_id, user_id)

        # --- Функция для правильного множества koin/koins ---
        def plural_koins(amount):
            return "koin" if amount == 1 else "koins"

        text = f"<b>K8 coffee shop</b>\nYour balance is {balance} {plural_koins(balance)}."

        # --- Получаем товары из магазина ---
        cursor = db.conn.cursor()
        cursor.execute("SELECT item_name, price FROM shop_items")
        items = cursor.fetchall()

        # --- Формируем клавиатуру сразу как список списков ---
        buttons = [
            [InlineKeyboardButton(text=f"{item_name} — {price} {plural_koins(price)}",
                                  callback_data=f"shop_buy:{item_name}")]
            for item_name, price in items
        ]

        # если товаров нет, кнопок не будет, но объект создаём корректно
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


    @dp.callback_query(lambda c: c.data and c.data.startswith("shop_buy:"))
    async def shop_buy_callback(callback_query: types.CallbackQuery):
        db = Database()
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        item_name = callback_query.data.split("shop_buy:")[1]

        # получаем цену и текст ответа
        cursor = db.conn.cursor()
        cursor.execute("SELECT price, response_text, sticker_file_id FROM shop_items WHERE item_name = ?", (item_name,))
        result = cursor.fetchone()

        if not result:
            await callback_query.answer("Item not found!", show_alert=True)
            return

        price, response_text, sticker_file_id = result
        balance = db.get_balance(chat_id, user_id)

        def plural_koins(amount):
            return "koin" if amount == 1 else "koins"

        if balance < price:
            await callback_query.answer(
                "Not enough koins! Be more active in the chat to earn more.",
                show_alert=True
            )
            return

        # списываем коины
        db.add_koins(chat_id, user_id, -price)
        now = datetime.now()
        db.log_shop_purchase(chat_id, user_id, item_name)

        # удаляем сообщение с магазином
        await callback_query.message.delete()

        # отправляем текст и стикер (если есть)
        # получаем имя пользователя
        name = db.get_name(chat_id, user_id)
        # если в тексте есть {name}, подставляем его
        if response_text:
            response_text = response_text.format(name=name)
            await callback_query.message.answer(response_text)

        if sticker_file_id:
            await callback_query.message.answer_sticker(sticker_file_id)

        await callback_query.answer(f"You bought {item_name} for {price} {plural_koins(price)}!")

import os
import asyncio
import re
from html import escape
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

import db

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID"))
PROXY = os.getenv("PROXY")  # нужен, если Telegram API заблокирован


def session():
    return AiohttpSession(proxy=PROXY) if PROXY else None


bot = Bot(os.getenv("ADMIN_BOT_TOKEN"), session=session(), default=DefaultBotProperties(parse_mode="HTML"))
user_bot = Bot(os.getenv("USER_BOT_TOKEN"), session=session()) 
dp = Dispatcher()


dp.message.filter(F.from_user.id == ADMIN_ID)
dp.callback_query.filter(F.from_user.id == ADMIN_ID)

STATUSES = {
    "new": "🆕 Новый",
    "accepted": "👨‍🍳 Готовится",
    "done": "✅ Выполнен",
    "canceled": "❌ Отменён",
}


MESSAGES = {
    "accepted": "Заказ №{} принят и уже готовится 🔥",
    "done": "Заказ №{} выполнен. Приятного аппетита!",
    "canceled": "Заказ №{} отменён. Мы скоро с вами свяжемся.",
}


def order_text(order):
    lines = [f"Заказ №{order['id']} · {STATUSES[order['status']]}", order["date"], ""]
    for item in order["items"]:
        lines.append(f"• {item['name']} × {item['qty']} — {item['price'] * item['qty']} ₽")
    lines += [
        "",
        f"Итого: {order['total']} ₽",
        "",
        f"👤 {order['name']}, {order['phone']}",
        f"📍 {order['address']}",
    ]
    if order["comment"]:
        lines.append(f"💬 {order['comment']}")
    text = escape("\n".join(lines))
    username = order.get("user_username")
    if username and re.fullmatch(r"[A-Za-z0-9_]{1,32}", username):
        text += f'\n\n<a href="https://t.me/{username}">Написать покупателю в Telegram</a>'
    elif order.get("user_id"):
        text += f'\n\n<a href="tg://user?id={int(order["user_id"])}">Написать покупателю в Telegram</a>'
    return text


def order_buttons(order):
    if order["status"] == "new":
        buttons = [("Принять", "accepted"), ("Отменить", "canceled")]
    elif order["status"] == "accepted":
        buttons = [("Выполнен", "done")]
    else:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, callback_data=f"{order['id']}:{status}") for text, status in buttons
    ]])


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Сюда приходят новые заказы.\n\n/orders — активные заказы\n/stats — статистика за сегодня")


@dp.message(Command("orders"))
async def active_orders(message: Message):
    orders = db.active_orders()
    if not orders:
        await message.answer("Активных заказов нет")
    for order in orders:
        await message.answer(order_text(order), reply_markup=order_buttons(order))


@dp.message(Command("stats"))
async def stats(message: Message):
    orders = db.today_orders()
    total = sum(o["total"] for o in orders)
    await message.answer(f"Сегодня: {len(orders)} заказов на {total} ₽")


@dp.callback_query()
async def change_status(callback: CallbackQuery):
    order_id, status = callback.data.split(":")
    order = db.set_status(int(order_id), status)

    await callback.message.edit_text(order_text(order), reply_markup=order_buttons(order))
    await callback.answer(STATUSES[status])

    if order["user_id"]:
        await user_bot.send_message(order["user_id"], MESSAGES[status].format(order["id"]))


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

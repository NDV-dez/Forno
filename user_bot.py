import os
import json
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp
from dotenv import load_dotenv

load_dotenv()

WEB_APP_URL = os.getenv("WEB_APP_URL")  # HTTPS-адрес, где запущен main.py
PROXY = os.getenv("PROXY")  # нужен, если Telegram API заблокирован
bot = Bot(os.getenv("USER_BOT_TOKEN"), session=AiohttpSession(proxy=PROXY) if PROXY else None)
dp = Dispatcher()

with open("shop.json", encoding="utf-8") as f:
    shop = json.load(f)


@dp.message(Command("start"))
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍕 Открыть меню", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer(
        f"Привет! Это {shop['name']}.\n{shop['description']}\n\nНажмите кнопку ниже, чтобы сделать заказ.",
        reply_markup=keyboard,
    )


async def main():
    # Кнопка «Меню» рядом с полем ввода
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Меню", web_app=WebAppInfo(url=WEB_APP_URL)))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

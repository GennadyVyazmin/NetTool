import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo

from app.config import get_settings


logging.basicConfig(level=logging.INFO)

settings = get_settings()
bot = Bot(token=settings.bot_token)
dispatcher = Dispatcher()


@dispatcher.message(CommandStart())
async def start_handler(message: Message) -> None:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Open NetTool",
                    web_app=WebAppInfo(url=settings.public_webapp_url),
                )
            ]
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "Open NetTool to run ping, traceroute, port checks, geo lookup, and manage favorites.",
        reply_markup=keyboard,
    )


async def main() -> None:
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

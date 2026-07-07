from aiogram import Dispatcher

from bot.handlers import callbacks, commands, voice


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(voice.router)

"""Aiogram middleware."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.handlers.deps import AppContext


class AppContextMiddleware(BaseMiddleware):
    def __init__(self, app: AppContext) -> None:
        self._app = app

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["app"] = self._app
        return await handler(event, data)

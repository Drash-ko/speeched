"""Bot command handlers."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import (
    DEFAULT_UI_LANGUAGE,
    RECOGNITION_LANGUAGES,
    UI_LANGUAGES,
    WHISPER_MODELS,
)
from bot.handlers.deps import AppContext
from bot.i18n import (
    menu_texts,
    private_keyboard,
    speech_language_label,
    t,
    ui_language_label,
    whisper_model_label,
)

logger = logging.getLogger(__name__)
router = Router(name="commands")

MODEL_CALLBACK_PREFIX = "set_whisper:"
LANGUAGE_CALLBACK_PREFIX = "set_lang:"
UI_LANG_CALLBACK_PREFIX = "set_ui:"
SUMMARY_CALLBACK_PREFIX = "set_summary:"
BOT_TOGGLE_PREFIX = "bot_toggle:"
RECOG_NAV_PREFIX = "recog_nav:"
RECOG_MODEL_PREFIX = "recog_w:"
RECOG_LANG_PREFIX = "recog_l:"
RECOG_SUMMARY_PREFIX = "recog_s:"


def _back_button(ui_lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=t("btn_back", ui_lang),
        callback_data=f"{RECOG_NAV_PREFIX}main",
    )


def _model_keyboard(current: str, ui_lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        f"{'✓ ' if model == current else ''}"
                        f"{whisper_model_label(model, ui_lang)}"
                    ),
                    callback_data=f"{MODEL_CALLBACK_PREFIX}{model}",
                )
            ]
            for model in WHISPER_MODELS
        ]
    )


def _speech_language_keyboard(current: str, ui_lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        f"{'✓ ' if lang == current else ''}"
                        f"{speech_language_label(lang, ui_lang)}"
                    ),
                    callback_data=f"{LANGUAGE_CALLBACK_PREFIX}{lang}",
                )
            ]
            for lang in RECOGNITION_LANGUAGES
        ]
    )


def _recognition_main_text(
    current_model: str,
    current_lang: str,
    show_summary: bool,
    ui_lang: str,
) -> str:
    summary_state = t("on" if show_summary else "off", ui_lang)
    return (
        f"<b>{t('recognition_title', ui_lang)}</b>\n"
        f"{t('model_title', ui_lang)}: "
        f"<b>{whisper_model_label(current_model, ui_lang)}</b>\n"
        f"{t('speech_lang_title', ui_lang)}: "
        f"<b>{speech_language_label(current_lang, ui_lang)}</b>\n"
        f"{t('settings_show_summary', ui_lang)}: <b>{summary_state}</b>\n\n"
        f"{t('recognition_choose', ui_lang)}"
    )


def _recognition_main_keyboard(show_summary: bool, ui_lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("menu_model", ui_lang),
                    callback_data=f"{RECOG_NAV_PREFIX}model",
                ),
                InlineKeyboardButton(
                    text=t("menu_language", ui_lang),
                    callback_data=f"{RECOG_NAV_PREFIX}lang",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✓ ' if show_summary else ''}{t('on', ui_lang)}",
                    callback_data=f"{RECOG_SUMMARY_PREFIX}on",
                ),
                InlineKeyboardButton(
                    text=f"{'✓ ' if not show_summary else ''}{t('off', ui_lang)}",
                    callback_data=f"{RECOG_SUMMARY_PREFIX}off",
                ),
            ],
        ]
    )


def _recognition_model_text(current_model: str, ui_lang: str) -> str:
    return (
        f"<b>{t('model_title', ui_lang)}</b>: "
        f"<b>{whisper_model_label(current_model, ui_lang)}</b>\n"
        f"{t('model_choose', ui_lang)}"
    )


def _recognition_model_keyboard(current_model: str, ui_lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{'✓ ' if model == current_model else ''}"
                    f"{whisper_model_label(model, ui_lang)}"
                ),
                callback_data=f"{RECOG_MODEL_PREFIX}{model}",
            )
        ]
        for model in WHISPER_MODELS
    ]
    rows.append([_back_button(ui_lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _recognition_lang_text(current_lang: str, ui_lang: str) -> str:
    return (
        f"<b>{t('speech_lang_title', ui_lang)}</b>: "
        f"<b>{speech_language_label(current_lang, ui_lang)}</b>\n"
        f"{t('speech_lang_choose', ui_lang)}"
    )


def _recognition_lang_keyboard(current_lang: str, ui_lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{'✓ ' if lang == current_lang else ''}"
                    f"{speech_language_label(lang, ui_lang)}"
                ),
                callback_data=f"{RECOG_LANG_PREFIX}{lang}",
            )
        ]
        for lang in RECOGNITION_LANGUAGES
    ]
    rows.append([_back_button(ui_lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _bot_keyboard(enabled: bool, ui_lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✓ ' if enabled else ''}{t('on', ui_lang)}",
                    callback_data=f"{BOT_TOGGLE_PREFIX}on",
                ),
                InlineKeyboardButton(
                    text=f"{'✓ ' if not enabled else ''}{t('off', ui_lang)}",
                    callback_data=f"{BOT_TOGGLE_PREFIX}off",
                ),
            ]
        ]
    )


def _bot_status_text(enabled: bool, ui_lang: str) -> str:
    state = t("on" if enabled else "off", ui_lang)
    return (
        f"{t('group_bot_state', ui_lang)} <b>{state}</b>\n"
        f"{t('group_bot_hint', ui_lang)}"
    )


def _settings_text(ui_lang: str, show_summary: bool) -> str:
    summary_state = t("on" if show_summary else "off", ui_lang)
    return (
        f"<b>{t('settings_title', ui_lang)}</b>\n\n"
        f"{t('settings_ui_lang', ui_lang)}: "
        f"<b>{ui_language_label(ui_lang, ui_lang)}</b>\n"
        f"{t('settings_show_summary', ui_lang)}: <b>{summary_state}</b>\n"
        f"<i>{t('settings_show_summary_hint', ui_lang)}</i>"
    )


def _settings_keyboard(ui_lang: str, show_summary: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✓ ' if ui_lang == 'uk' else ''}Українська",
                    callback_data=f"{UI_LANG_CALLBACK_PREFIX}uk",
                ),
                InlineKeyboardButton(
                    text=f"{'✓ ' if ui_lang == 'en' else ''}English",
                    callback_data=f"{UI_LANG_CALLBACK_PREFIX}en",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✓ ' if show_summary else ''}{t('on', ui_lang)}",
                    callback_data=f"{SUMMARY_CALLBACK_PREFIX}on",
                ),
                InlineKeyboardButton(
                    text=f"{'✓ ' if not show_summary else ''}{t('off', ui_lang)}",
                    callback_data=f"{SUMMARY_CALLBACK_PREFIX}off",
                ),
            ],
        ]
    )


def _is_group_chat(message: Message | None) -> bool:
    return bool(
        message and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
    )


async def _user_ui_lang(message: Message, app: AppContext) -> str:
    if message.from_user:
        return await app.settings.get_ui_language(message.from_user.id)
    return DEFAULT_UI_LANGUAGE


async def _show_recognition_main(
    message: Message, app: AppContext, user_id: int, *, edit: bool = False
) -> None:
    ui_lang = await app.settings.get_ui_language(user_id)
    current_model = await app.settings.get_whisper_model(user_id)
    current_lang = await app.settings.get_language(user_id)
    show_summary = await app.settings.get_show_summary(user_id)
    text = _recognition_main_text(current_model, current_lang, show_summary, ui_lang)
    markup = _recognition_main_keyboard(show_summary, ui_lang)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def _show_recognition_model(message: Message, app: AppContext, user_id: int) -> None:
    ui_lang = await app.settings.get_ui_language(user_id)
    current_model = await app.settings.get_whisper_model(user_id)
    await message.edit_text(
        _recognition_model_text(current_model, ui_lang),
        reply_markup=_recognition_model_keyboard(current_model, ui_lang),
    )


async def _show_recognition_lang(message: Message, app: AppContext, user_id: int) -> None:
    ui_lang = await app.settings.get_ui_language(user_id)
    current_lang = await app.settings.get_language(user_id)
    await message.edit_text(
        _recognition_lang_text(current_lang, ui_lang),
        reply_markup=_recognition_lang_keyboard(current_lang, ui_lang),
    )


@router.message(Command("start"))
async def cmd_start(message: Message, app: AppContext) -> None:
    ui_lang = await _user_ui_lang(message, app)
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(t("welcome", ui_lang), reply_markup=private_keyboard(ui_lang))
    else:
        await message.answer(t("welcome", ui_lang))


@router.message(Command("help"))
@router.message(F.text.in_(menu_texts("menu_help")))
async def cmd_help(message: Message, app: AppContext) -> None:
    ui_lang = await _user_ui_lang(message, app)
    await message.answer(t("help", ui_lang))


@router.message(Command("recognition"))
async def cmd_recognition(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return
    if not _is_group_chat(message):
        return
    await _show_recognition_main(message, app, message.from_user.id)


@router.callback_query(F.data.startswith(RECOG_NAV_PREFIX))
async def on_recognition_nav(callback: CallbackQuery, app: AppContext) -> None:
    if not callback.message or not _is_group_chat(callback.message):
        await callback.answer()
        return

    screen = (callback.data or "").removeprefix(RECOG_NAV_PREFIX)
    user_id = callback.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)

    if screen == "main":
        await _show_recognition_main(callback.message, app, user_id, edit=True)
    elif screen == "model":
        await _show_recognition_model(callback.message, app, user_id)
    elif screen == "lang":
        await _show_recognition_lang(callback.message, app, user_id)
    else:
        await callback.answer(t("unknown_option", ui_lang), show_alert=True)
        return

    await callback.answer()


@router.message(Command("model"))
@router.message(F.text.in_(menu_texts("menu_model")))
async def cmd_model(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return
    ui_lang = await app.settings.get_ui_language(message.from_user.id)
    current = await app.settings.get_whisper_model(message.from_user.id)
    await message.answer(
        f"<b>{t('model_title', ui_lang)}</b>: {whisper_model_label(current, ui_lang)}\n"
        f"{t('model_choose', ui_lang)}",
        reply_markup=_model_keyboard(current, ui_lang),
    )


@router.callback_query(F.data.startswith(MODEL_CALLBACK_PREFIX))
async def on_model_select(callback: CallbackQuery, app: AppContext) -> None:
    model = (callback.data or "").removeprefix(MODEL_CALLBACK_PREFIX)
    if model not in WHISPER_MODELS:
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    await app.settings.set_whisper_model(user_id, model)
    label = whisper_model_label(model, ui_lang)
    await callback.answer(label)
    if callback.message:
        await callback.message.edit_text(
            f"{t('model_updated', ui_lang)} <b>{label}</b>."
        )


@router.callback_query(F.data.startswith(RECOG_MODEL_PREFIX))
async def on_recog_model_select(callback: CallbackQuery, app: AppContext) -> None:
    model = (callback.data or "").removeprefix(RECOG_MODEL_PREFIX)
    if model not in WHISPER_MODELS:
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    await app.settings.set_whisper_model(user_id, model)
    await callback.answer(whisper_model_label(model, ui_lang))
    if callback.message:
        await _show_recognition_model(callback.message, app, user_id)


@router.message(Command("language"))
@router.message(F.text.in_(menu_texts("menu_language")))
async def cmd_language(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return
    ui_lang = await app.settings.get_ui_language(message.from_user.id)
    current = await app.settings.get_language(message.from_user.id)
    await message.answer(
        f"<b>{t('speech_lang_title', ui_lang)}</b>: "
        f"{speech_language_label(current, ui_lang)}\n"
        f"{t('speech_lang_choose', ui_lang)}",
        reply_markup=_speech_language_keyboard(current, ui_lang),
    )


@router.callback_query(F.data.startswith(LANGUAGE_CALLBACK_PREFIX))
async def on_language_select(callback: CallbackQuery, app: AppContext) -> None:
    language = (callback.data or "").removeprefix(LANGUAGE_CALLBACK_PREFIX)
    if language not in RECOGNITION_LANGUAGES:
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    await app.settings.set_language(user_id, language)
    label = speech_language_label(language, ui_lang)
    await callback.answer(label)
    if callback.message:
        await callback.message.edit_text(
            f"{t('speech_lang_updated', ui_lang)} <b>{label}</b>."
        )


@router.callback_query(F.data.startswith(RECOG_LANG_PREFIX))
async def on_recog_language_select(callback: CallbackQuery, app: AppContext) -> None:
    language = (callback.data or "").removeprefix(RECOG_LANG_PREFIX)
    if language not in RECOGNITION_LANGUAGES:
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    await app.settings.set_language(user_id, language)
    await callback.answer(speech_language_label(language, ui_lang))
    if callback.message:
        await _show_recognition_lang(callback.message, app, user_id)


@router.message(Command("settings"), F.chat.type == ChatType.PRIVATE)
@router.message(F.text.in_(menu_texts("menu_settings")), F.chat.type == ChatType.PRIVATE)
async def cmd_settings(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return
    user_id = message.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    show_summary = await app.settings.get_show_summary(user_id)
    await message.answer(
        _settings_text(ui_lang, show_summary),
        reply_markup=_settings_keyboard(ui_lang, show_summary),
    )


@router.callback_query(F.data.startswith(UI_LANG_CALLBACK_PREFIX))
async def on_ui_language_select(callback: CallbackQuery, app: AppContext) -> None:
    if callback.message and callback.message.chat.type != ChatType.PRIVATE:
        await callback.answer()
        return

    lang = (callback.data or "").removeprefix(UI_LANG_CALLBACK_PREFIX)
    if lang not in UI_LANGUAGES:
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    await app.settings.set_ui_language(user_id, lang)
    show_summary = await app.settings.get_show_summary(user_id)
    await callback.answer(t("ui_lang_updated", lang))
    if callback.message:
        await callback.message.edit_text(
            _settings_text(lang, show_summary),
            reply_markup=_settings_keyboard(lang, show_summary),
        )
        await callback.message.answer(
            t("welcome", lang),
            reply_markup=private_keyboard(lang),
        )


@router.callback_query(F.data.startswith(SUMMARY_CALLBACK_PREFIX))
async def on_show_summary_select(callback: CallbackQuery, app: AppContext) -> None:
    if callback.message and callback.message.chat.type != ChatType.PRIVATE:
        await callback.answer()
        return

    value = (callback.data or "").removeprefix(SUMMARY_CALLBACK_PREFIX)
    if value not in ("on", "off"):
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    enabled = value == "on"
    await app.settings.set_show_summary(user_id, enabled)
    ui_lang = await app.settings.get_ui_language(user_id)
    await callback.answer(t("show_summary_updated", ui_lang))
    if callback.message:
        await callback.message.edit_text(
            _settings_text(ui_lang, enabled),
            reply_markup=_settings_keyboard(ui_lang, enabled),
        )


@router.callback_query(F.data.startswith(RECOG_SUMMARY_PREFIX))
async def on_recog_summary_select(callback: CallbackQuery, app: AppContext) -> None:
    value = (callback.data or "").removeprefix(RECOG_SUMMARY_PREFIX)
    if value not in ("on", "off"):
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    user_id = callback.from_user.id
    enabled = value == "on"
    await app.settings.set_show_summary(user_id, enabled)
    ui_lang = await app.settings.get_ui_language(user_id)
    await callback.answer(t("show_summary_updated", ui_lang))
    if callback.message:
        await _show_recognition_main(callback.message, app, user_id, edit=True)


@router.message(Command("bot"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_bot_status(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return

    ui_lang = await app.settings.get_ui_language(message.from_user.id)
    enabled = await app.settings.is_group_enabled(message.chat.id)
    await message.answer(
        _bot_status_text(enabled, ui_lang),
        reply_markup=_bot_keyboard(enabled, ui_lang),
    )


@router.callback_query(F.data.startswith(BOT_TOGGLE_PREFIX))
async def on_bot_toggle(callback: CallbackQuery, app: AppContext) -> None:
    if not callback.message or callback.message.chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP,
    ):
        await callback.answer()
        return

    value = (callback.data or "").removeprefix(BOT_TOGGLE_PREFIX)
    if value not in ("on", "off"):
        await callback.answer(t("unknown_option", "uk"), show_alert=True)
        return

    enabled = value == "on"
    user_id = callback.from_user.id
    ui_lang = await app.settings.get_ui_language(user_id)
    await app.settings.set_group_enabled(callback.message.chat.id, enabled)
    logger.info(
        "Group %s bot %s by user %s",
        callback.message.chat.id,
        "enabled" if enabled else "disabled",
        user_id,
    )
    await callback.answer(
        t("group_bot_enabled" if enabled else "group_bot_disabled", ui_lang)
    )
    await callback.message.edit_text(
        _bot_status_text(enabled, ui_lang),
        reply_markup=_bot_keyboard(enabled, ui_lang),
    )


@router.message(Command("boton"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_bot_on(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return

    ui_lang = await app.settings.get_ui_language(message.from_user.id)
    await app.settings.set_group_enabled(message.chat.id, True)
    logger.info(
        "Group %s bot enabled by user %s",
        message.chat.id,
        message.from_user.id,
    )
    await message.answer(t("group_bot_enabled", ui_lang))


@router.message(Command("botoff"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_bot_off(message: Message, app: AppContext) -> None:
    if not message.from_user:
        return

    ui_lang = await app.settings.get_ui_language(message.from_user.id)
    await app.settings.set_group_enabled(message.chat.id, False)
    logger.info(
        "Group %s bot disabled by user %s",
        message.chat.id,
        message.from_user.id,
    )
    await message.answer(t("group_bot_disabled", ui_lang))

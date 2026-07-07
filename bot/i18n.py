"""User-facing UI strings (English default, Ukrainian optional)."""

from __future__ import annotations

from bot.config import DEFAULT_UI_LANGUAGE, UI_LANGUAGES

_STRINGS: dict[str, dict[str, str]] = {
    # Menu
    "menu_help": {"uk": "ℹ️ Довідка", "en": "ℹ️ Help"},
    "menu_model": {"uk": "⚙️ Модель", "en": "⚙️ Model"},
    "menu_language": {"uk": "🌐 Мова", "en": "🌐 Language"},
    "menu_settings": {"uk": "🔧 Налаштування", "en": "🔧 Settings"},
    "input_placeholder": {
        "uk": "Надішліть голосове або кружечок…",
        "en": "Send a voice message or video note…",
    },
    # Welcome & help
    "welcome": {
        "uk": (
            "Привіт! Я перетворюю голосові та кружечки на текст.\n\n"
            "Надішліть повідомлення — я відповім під ним.\n\n"
            "Кнопки меню нижче або команди:\n"
            "/help — як користуватися\n"
            "/model — якість розпізнавання\n"
            "/language — мова розпізнавання\n"
            "/settings — налаштування"
        ),
        "en": (
            "Hi! I turn voice messages and video notes into text.\n\n"
            "Send a message — I'll reply right below it.\n\n"
            "Menu buttons below or commands:\n"
            "/help — how to use\n"
            "/model — recognition quality\n"
            "/language — speech language\n"
            "/settings — preferences"
        ),
    },
    "help": {
        "uk": (
            "<b>Як користуватися</b>\n"
            "Надішліть голосове повідомлення або кружечок — бот відповість під ним.\n\n"
            "<b>Особистий чат</b> — готовий текст з’явиться в тій самій відповіді.\n"
            "<b>Група</b> — /bot (увімкнути або вимкнути), /recognition (модель, мова, переказ).\n\n"
            "<b>Налаштування</b> (/settings) — мова інтерфейсу та короткий переказ."
        ),
        "en": (
            "<b>How to use</b>\n"
            "Send a voice message or video note — the bot replies right below it.\n\n"
            "<b>Private chat</b> — the finished text appears in that same reply.\n"
            "<b>Groups</b> — /bot (enable or disable), /recognition (model, language, summary).\n\n"
            "<b>Settings</b> (/settings) — interface language and brief summary."
        ),
    },
    # Commands (Telegram menu)
    "cmd_start": {"uk": "Запуск", "en": "Start"},
    "cmd_help": {"uk": "Довідка", "en": "Help"},
    "cmd_model": {"uk": "Модель", "en": "Model"},
    "cmd_language": {"uk": "Мова розпізнавання", "en": "Speech language"},
    "cmd_settings": {"uk": "Налаштування", "en": "Settings"},
    "cmd_bot": {"uk": "Бот у групі", "en": "Group bot"},
    "cmd_recognition": {"uk": "Модель і мова", "en": "Model & language"},
    # Model picker
    "model_title": {"uk": "Модель розпізнавання", "en": "Recognition model"},
    "model_choose": {
        "uk": "Оберіть варіант:\n<i>«Найкраща якість» точніша, але повільніша за «Стандартну».</i>",
        "en": "Choose an option:\n<i>«Best quality» is more accurate but slower than «Standard».</i>",
    },
    "model_updated": {"uk": "Модель оновлено:", "en": "Model updated:"},
    "whisper_medium": {"uk": "Стандартна", "en": "Standard"},
    "whisper_large_v3_turbo": {
        "uk": "Найкраща якість (повільніше)",
        "en": "Best quality (slower)",
    },
    "recognition_title": {"uk": "Розпізнавання", "en": "Recognition"},
    "btn_back": {"uk": "◀️ Назад", "en": "◀️ Back"},
    "recognition_choose": {
        "uk": "Оберіть налаштування:",
        "en": "Choose a setting:",
    },
    # Speech language picker
    "speech_lang_title": {"uk": "Мова розпізнавання", "en": "Speech language"},
    "speech_lang_choose": {
        "uk": "Оберіть мову мовлення в аудіо:",
        "en": "Choose the language spoken in the audio:",
    },
    "speech_lang_updated": {"uk": "Мову оновлено:", "en": "Language updated:"},
    "speech_auto": {"uk": "Авто", "en": "Auto"},
    "speech_en": {"uk": "Англійська", "en": "English"},
    "speech_uk": {"uk": "Українська", "en": "Ukrainian"},
    "speech_ru": {"uk": "Російська", "en": "Russian"},
    "ui_lang_uk": {"uk": "Українська", "en": "Ukrainian"},
    "ui_lang_en": {"uk": "Англійська", "en": "English"},
    # Settings
    "settings_title": {"uk": "Налаштування", "en": "Settings"},
    "settings_ui_lang": {"uk": "Мова інтерфейсу", "en": "Interface language"},
    "settings_show_summary": {
        "uk": "Короткий переказ",
        "en": "Brief summary",
    },
    "settings_show_summary_hint": {
        "uk": "ІІ додасть стислий переказ в кінці повідомлення.",
        "en": "AI adds a concise summary at the end of the message.",
    },
    "on": {"uk": "Увімкнено", "en": "On"},
    "off": {"uk": "Вимкнено", "en": "Off"},
    "ui_lang_updated": {"uk": "Мову інтерфейсу оновлено.", "en": "Interface language updated."},
    "show_summary_updated": {"uk": "Налаштування оновлено.", "en": "Setting updated."},
    # Progress
    "stage_download": {"uk": "Завантаження…", "en": "Downloading…"},
    "stage_whisper": {"uk": "Розпізнавання мовлення…", "en": "Recognizing speech…"},
    "stage_llm": {"uk": "Оформлення тексту…", "en": "Polishing text…"},
    "stage_summary": {"uk": "Короткий переказ…", "en": "Writing summary…"},
    "stage_queued": {
        "uk": "У черзі · позиція {position}",
        "en": "Queued · position {position}",
    },
    # Results
    "label_summary": {"uk": "Коротко", "en": "Summary"},
    "transcription_ready": {"uk": "Транскрипція готова.", "en": "Transcription ready."},
    "show_transcription": {"uk": "Показати транскрипцію", "en": "Show transcription"},
    "error_transcription": {
        "uk": "Не вдалося обробити повідомлення. Спробуйте ще раз.",
        "en": "Could not process the message. Please try again.",
    },
    "error_unsupported_chat": {
        "uk": "Підтримуються лише особисті чати та групи.",
        "en": "Only private chats and groups are supported.",
    },
    "warn_llm_skipped": {
        "uk": "Редагування тексту пропущено — показано результат розпізнавання.",
        "en": "Text editing was skipped — showing recognition result only.",
    },
    "warn_summary_skipped": {
        "uk": "Короткий переказ пропущено.",
        "en": "Brief summary was skipped.",
    },
    "warn_empty": {
        "uk": "Мовлення не розпізнано.",
        "en": "No speech was recognized.",
    },
    "empty_transcription": {"uk": "(порожньо)", "en": "(empty)"},
    # Groups
    "group_bot_state": {"uk": "Бот у групі:", "en": "Bot in this group:"},
    "group_bot_hint": {
        "uk": "Натисніть кнопку нижче, щоб увімкнути або вимкнути.",
        "en": "Use the button below to enable or disable.",
    },
    "group_bot_enabled": {"uk": "Бот увімкнено в цій групі.", "en": "Bot enabled in this group."},
    "group_bot_disabled": {"uk": "Бот вимкнено в цій групі.", "en": "Bot disabled in this group."},
    "transcript_expired": {
        "uk": "Транскрипція застаріла. Надішліть повідомлення знову.",
        "en": "Transcript expired. Please resend the message.",
    },
    "button_groups_only": {
        "uk": "Ця кнопка працює лише в групах.",
        "en": "This button works in groups only.",
    },
    "unknown_option": {"uk": "Невідомий варіант.", "en": "Unknown option."},
}

_WHISPER_I18N_KEYS = {
    "medium": "whisper_medium",
    "large-v3-turbo": "whisper_large_v3_turbo",
}

_SPEECH_I18N_KEYS = {
    "auto": "speech_auto",
    "en": "speech_en",
    "uk": "speech_uk",
    "ru": "speech_ru",
}


def normalize_ui_language(lang: str | None) -> str:
    if lang in UI_LANGUAGES:
        return lang
    return DEFAULT_UI_LANGUAGE


def t(key: str, lang: str | None = None, **kwargs: str) -> str:
    ui = normalize_ui_language(lang)
    entry = _STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(ui) or entry.get(DEFAULT_UI_LANGUAGE) or key
    if kwargs:
        return text.format(**kwargs)
    return text


def menu_texts(key: str) -> set[str]:
    return {t(key, lang) for lang in UI_LANGUAGES}


def whisper_model_label(model: str, lang: str | None = None) -> str:
    i18n_key = _WHISPER_I18N_KEYS.get(model)
    if i18n_key:
        return t(i18n_key, lang)
    return model


def speech_language_label(code: str, lang: str | None = None) -> str:
    i18n_key = _SPEECH_I18N_KEYS.get(code)
    if i18n_key:
        return t(i18n_key, lang)
    return code


def ui_language_label(code: str, lang: str | None = None) -> str:
    keys = {"uk": "ui_lang_uk", "en": "ui_lang_en"}
    i18n_key = keys.get(code)
    if i18n_key:
        return t(i18n_key, lang)
    return code


def private_keyboard(lang: str | None = None):
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    ui = normalize_ui_language(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("menu_model", ui)),
                KeyboardButton(text=t("menu_language", ui)),
            ],
            [KeyboardButton(text=t("menu_settings", ui))],
            [KeyboardButton(text=t("menu_help", ui))],
        ],
        resize_keyboard=True,
        input_field_placeholder=t("input_placeholder", ui),
    )


def format_warnings(warning_keys: list[str], lang: str | None = None) -> list[str]:
    return [t(key, lang) for key in warning_keys]


def format_user_transcription(
    *,
    text: str,
    summary: str | None = None,
    warning_keys: list[str],
    ui_lang: str,
) -> str:
    warnings = format_warnings(warning_keys, ui_lang)
    body = text
    if summary:
        body = f"{body}\n\n<b>{t('label_summary', ui_lang)}</b>\n{summary}"
    if warnings:
        notes = "\n".join(f"⚠️ {w}" for w in warnings)
        return f"{body}\n\n{notes}"
    return body

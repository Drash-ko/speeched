"""Local LLM post-processing via llama.cpp HTTP API or CLI subprocess."""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import unicodedata

import httpx

from bot.config import (
    LLM_MODEL_FALLBACKS,
    SUMMARY_WORD_MAX,
    SUMMARY_WORD_MIN,
    SUMMARY_WORD_RATIO,
    settings,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a speech-to-text editor for English, Ukrainian, and Russian. "
    "The input is raw ASR output with recognition errors: wrong words, missing punctuation, "
    "decomposed Unicode (e.g. i + combining diaeresis instead of ї), homoglyphs, and split letters. "
    "Your job is to fix these errors so the text reads naturally. "
    "Normalize Unicode to composed form (NFC). "
    "Aggressively fix phonetic recognition errors: if a word sounds similar to what was likely spoken "
    "but is spelled wrong or doesn't exist, correct it to the actual word. "
    "For Ukrainian/Russian, pay special attention to similar-sounding letters (і/ї, и/і, е/є, etc.) "
    "and correct them based on context. "
    "If a word doesn't fit the surrounding context or meaning, replace it with the word that makes sense. "
    "Never change facts, names, numbers, intent, or tone. "
    "Preserve profanity exactly as spoken — do NOT censor, replace, or modify swear words. "
    "Do not add information, remove content, or rephrase unnecessarily. "
    "The output MUST differ from the input when there are fixable errors. "
    "Return only the corrected text with no explanations or quotes."
)

USER_PROMPT_TEMPLATE = (
    "Fix ASR errors in this transcription. Keep exact meaning and tone "
    "(including profanity if present). Write in {language_hint}.\n\n{text}"
)

SUMMARY_SYSTEM_PROMPT = (
    "You write concise summaries of spoken text — the gist in a few sentences.\n\n"
    "CRITICAL RULES:\n"
    "1. Write ONLY in the same language as the input — never translate.\n"
    "2. Exactly ONE paragraph. No lists, no line breaks.\n"
    "3. Extract the MAIN IDEA — do NOT paraphrase sentence by sentence or repeat the whole text.\n"
    "4. Skip filler, false starts, and repeated phrases. Keep only what matters.\n"
    "5. Match the speaker's person (first person stays first person) and overall tone.\n"
    "6. Preserve key facts: what, why, how, names, platforms, technical terms.\n"
    "7. Do not invent details. Do not copy the opening word-for-word.\n\n"
    "Return only the summary with no preamble or quotes."
)

_LANGUAGE_HINTS = {
    "en": "English",
    "uk": "Ukrainian",
    "ru": "Russian",
    "auto": "the same language as the input text",
}

_RETRYABLE_HTTP = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.NetworkError,
)


class LLMService:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def refine(
        self,
        text: str,
        model_alias: str,
        language: str | None = None,
        *,
        detected_language: str | None = None,
    ) -> str:
        normalized = unicodedata.normalize("NFC", text)
        result = await self._run(
            normalized,
            model_alias,
            language=language,
            detected_language=detected_language,
            system_prompt=SYSTEM_PROMPT,
            user_template=USER_PROMPT_TEMPLATE,
            temperature=0.2,
            task="refine",
        )
        return unicodedata.normalize("NFC", result)

    async def summarize(
        self,
        text: str,
        model_alias: str,
        language: str | None = None,
        *,
        detected_language: str | None = None,
    ) -> str:
        normalized = unicodedata.normalize("NFC", text)
        limits = self._summary_limits(normalized)
        user_template = (
            f"In {{language_hint}}, summarize the main point in {limits['sentence_range']} "
            f"(about {limits['target_words']} words). "
            "Be concise — do not rewrite the whole text.\n\n{{text}}"
        )
        result = await self._run(
            normalized,
            model_alias,
            language=language,
            detected_language=detected_language,
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_template=user_template,
            temperature=0.2,
            task="summarize",
            max_tokens_cap=limits["max_tokens"],
        )
        return self._format_summary(
            result,
            source_text=normalized,
            target_words=limits["target_words"],
            max_sentences=limits["max_sentences"],
        )

    @staticmethod
    def _summary_limits(text: str) -> dict[str, int | str]:
        source_words = max(1, len(text.split()))
        target_words = max(
            SUMMARY_WORD_MIN,
            min(SUMMARY_WORD_MAX, int(source_words * SUMMARY_WORD_RATIO)),
        )
        if source_words <= 80:
            sentence_range = "1–2 sentences"
            max_sentences = 2
        elif source_words <= 250:
            sentence_range = "2–3 sentences"
            max_sentences = 3
        else:
            sentence_range = "3–5 sentences"
            max_sentences = 5
        max_tokens = max(64, min(512, target_words * 3))
        return {
            "target_words": target_words,
            "max_sentences": max_sentences,
            "max_tokens": max_tokens,
            "sentence_range": sentence_range,
        }

    async def _run(
        self,
        text: str,
        model_alias: str,
        *,
        language: str | None,
        detected_language: str | None,
        system_prompt: str,
        user_template: str,
        temperature: float,
        task: str,
        max_tokens_cap: int | None = None,
    ) -> str:
        if not text.strip():
            return text

        language_hint = self._language_hint(language, detected_language, text)

        models_to_try = [model_alias, *LLM_MODEL_FALLBACKS.get(model_alias, [])]
        last_error: Exception | None = None

        for model in models_to_try:
            try:
                if settings.llama_mode == "api":
                    result = await self._chat_api(
                        text,
                        language_hint,
                        system_prompt,
                        user_template,
                        temperature=temperature,
                        max_tokens_cap=max_tokens_cap,
                    )
                else:
                    result = await self._chat_cli(
                        text,
                        language_hint,
                        system_prompt,
                        user_template,
                        temperature=temperature,
                        max_tokens_cap=max_tokens_cap,
                    )
                cleaned = self._clean_output(result)
                if cleaned:
                    logger.info("LLM %s processed text using model alias '%s'", task, model)
                    return cleaned
            except Exception as exc:
                last_error = exc
                logger.warning("LLM model '%s' failed: %s", model, exc)

        if last_error:
            raise last_error
        return text

    @staticmethod
    def _language_hint(
        language: str | None,
        detected_language: str | None,
        text: str,
    ) -> str:
        if language and language != "auto" and language in _LANGUAGE_HINTS:
            return _LANGUAGE_HINTS[language]
        if detected_language and detected_language in _LANGUAGE_HINTS:
            return _LANGUAGE_HINTS[detected_language]
        detected = LLMService._detect_text_language(text)
        if detected:
            return _LANGUAGE_HINTS[detected]
        return _LANGUAGE_HINTS["auto"]

    @staticmethod
    def _detect_text_language(text: str) -> str | None:
        cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
        latin = len(re.findall(r"[A-Za-z]", text))
        if cyrillic > latin:
            uk_chars = len(re.findall(r"[іїєґ]", text, re.IGNORECASE))
            return "uk" if uk_chars else "ru"
        if latin > cyrillic:
            return "en"
        return None

    async def _chat_api(
        self,
        text: str,
        language_hint: str,
        system_prompt: str,
        user_template: str,
        *,
        temperature: float,
        max_tokens_cap: int | None = None,
    ) -> str:
        if not self._client:
            raise RuntimeError("LLM HTTP client is not initialized")

        max_tokens = max(384, len(text) * 2)
        if max_tokens_cap is not None:
            max_tokens = min(max_tokens, max_tokens_cap)

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": user_template.format(
                        language_hint=language_hint, text=text
                    ),
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        url = f"{settings.llama_api_url.rstrip('/')}/v1/chat/completions"
        retries = settings.llm_http_retries
        delay = settings.llm_http_retry_delay

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                response = await self._client.post(url, json=payload)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except _RETRYABLE_HTTP as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    last_error = exc
                else:
                    raise
            if attempt < retries:
                wait = delay * (2 ** (attempt - 1))
                logger.warning(
                    "llama.cpp HTTP error (attempt %s/%s), retry in %.1fs: %s",
                    attempt,
                    retries,
                    wait,
                    last_error,
                )
                await asyncio.sleep(wait)

        if last_error:
            raise last_error
        raise RuntimeError("llama.cpp HTTP request failed")

    async def _chat_cli(
        self,
        text: str,
        language_hint: str,
        system_prompt: str,
        user_template: str,
        *,
        temperature: float,
        max_tokens_cap: int | None = None,
    ) -> str:
        user_content = user_template.format(language_hint=language_hint, text=text)
        prompt = (
            f"<|im_start|>system\n{system_prompt}\n"
            f"<|im_start|>user\n{user_content}\n"
            f"<|im_start|>assistant\n"
        )
        max_tokens = max(384, len(text) * 2)
        if max_tokens_cap is not None:
            max_tokens = min(max_tokens, max_tokens_cap)
        cmd = [
            settings.llama_cli_path,
            "-m",
            settings.llama_model_path,
            "-p",
            prompt,
            "-n",
            str(max_tokens),
            "--temp",
            str(temperature),
            "-c",
            str(settings.llama_ctx_size),
            "-t",
            str(settings.llama_threads),
            "--no-display-prompt",
        ]

        def run() -> str:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"llama-cli failed (code {proc.returncode}): {proc.stderr.strip()}"
                )
            return proc.stdout

        return await asyncio.to_thread(run)

    @staticmethod
    def _clean_output(raw: str) -> str:
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:\w+)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip().strip('"').strip("'")
        return cleaned

    @staticmethod
    def _format_summary(
        raw: str,
        *,
        source_text: str = "",
        target_words: int = 60,
        max_sentences: int = 3,
    ) -> str:
        cleaned = LLMService._clean_output(raw)
        if not cleaned:
            return cleaned

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if len(lines) <= 1:
            paragraph = cleaned.replace("\n", " ").strip()
        else:
            parts: list[str] = []
            for line in lines:
                line = re.sub(r"^[-*•]\s+", "", line)
                line = re.sub(r"^\d+[.)]\s+", "", line)
                if line:
                    parts.append(line)
            paragraph = re.sub(r"\s+", " ", " ".join(parts)).strip()

        if paragraph and paragraph[-1] not in ".!?…":
            paragraph += "."

        summary_words = len(paragraph.split())
        word_cap = max(target_words + 10, int(target_words * 1.3))
        if summary_words > word_cap:
            sentences = re.split(r"(?<=[.!?…])\s+", paragraph)
            paragraph = " ".join(sentences[:max_sentences]).strip()
            if paragraph and paragraph[-1] not in ".!?…":
                paragraph += "."

        if source_text:
            source_words = len(source_text.split())
            if source_words > 20:
                ratio_cap = max(word_cap, int(source_words * SUMMARY_WORD_RATIO * 1.2))
                if len(paragraph.split()) > ratio_cap:
                    sentences = re.split(r"(?<=[.!?…])\s+", paragraph)
                    paragraph = " ".join(sentences[:max_sentences]).strip()
                    if paragraph and paragraph[-1] not in ".!?…":
                        paragraph += "."

        return paragraph

"""
LLM abstraction layer — pluggable providers with rate limiting and retry.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from threading import Lock
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from .config import Settings as _Settings
from .constants import (
    LLM_MAX_RETRIES,
    LLM_PROMPT_MAX_CHARS,
    RATE_LIMITER_DEFAULT_BURST,
    RATE_LIMITER_DEFAULT_RPM,
    LLM_RETRY_BACKOFF_BASE,
    RATE_LIMITER_ACQUIRE_TIMEOUT,
)

logger = logging.getLogger("TACC Resume builder")

# Initialize defaults on Settings class
_Settings.llm_rate_limit_rpm = RATE_LIMITER_DEFAULT_RPM
_Settings.llm_max_burst = RATE_LIMITER_DEFAULT_BURST


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE = "azure"
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMResponse(BaseModel):
    """Structured LLM response."""

    content: str
    reasoning: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMProviderError(Exception):
    """Raised when an LLM provider call fails."""


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter for LLM API calls."""

    def __init__(
        self,
        tokens_per_minute: int = 60,
        max_burst: int = 10,
    ) -> None:
        self.tokens_per_minute = max(tokens_per_minute, 1)
        self.max_burst = max_burst
        self._tokens = float(max_burst)
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def acquire(self, tokens: float = 1.0, timeout: float = 60.0) -> bool:
        """Acquire tokens from the bucket. Blocks until available or timeout."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                wait = (tokens - self._tokens) * (60.0 / self.tokens_per_minute)
                if time.monotonic() + wait > deadline:
                    return False
            time.sleep(min(wait, 0.1))

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.max_burst,
            self._tokens + elapsed * (self.tokens_per_minute / 60.0),
        )
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    @property
    def is_available(self) -> bool:
        return self.available_tokens >= 1.0


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM clients — enables Dependency Injection."""

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        cache_key: str | None = None,
    ) -> str:
        ...


class BaseLLMClient:
    """Abstract LLM client with rate limiting. Override _call_impl for custom providers."""

    def __init__(self, settings: Any) -> None:
        self.settings: _Settings = settings
        self._cache: dict[str, LLMResponse] = {}
        self._provider = LLMProvider(settings.llm_provider)
        self._rate_limiter = TokenBucketRateLimiter(
            tokens_per_minute=settings.llm_rate_limit_rpm,
            max_burst=settings.llm_max_burst,
        )
        self._rate_limiter_enabled = True

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        cache_key: str | None = None,
    ) -> str:
        """Send a chat request and return the content string."""
        if cache_key and cache_key in self._cache:
            logger.debug("LLM cache hit for key: %s", cache_key[:60])
            return self._cache[cache_key].content

        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        resp = self._call_with_retry(messages, max_tokens, temperature)
        if cache_key:
            self._cache[cache_key] = resp
        return resp.content

    def _call_with_retry(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None,
        temperature: float,
    ) -> LLMResponse:
        """Call the LLM with retry logic."""
        last_exc: Exception | None = None
        for attempt in range(1, 5):
            try:
                return self._call_impl(messages, max_tokens or 1000, temperature)
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                last_exc = e
                logger.warning(
                    "LLM call attempt %d/4 failed: %s",
                    attempt,
                    e,
                )
                if attempt < 4:
                    time.sleep(2**attempt)
            except json.JSONDecodeError as e:
                last_exc = e
                logger.warning("LLM JSON decode error attempt %d/4: %s", attempt, e)
                if attempt < 4:
                    time.sleep(1)
        logger.error("LLM call failed after 4 attempts")
        if last_exc:
            traceback.print_exception(type(last_exc), last_exc, last_exc.__traceback__)
        return LLMResponse(content="")

    def _call_impl(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Provider-specific implementation. Dispatches based on provider type."""
        if self._rate_limiter_enabled:
            if not self._rate_limiter.acquire(timeout=30.0):
                logger.warning("Rate limit timeout exceeded, returning empty response")
                return LLMResponse(content="")

        provider = self._provider
        if provider == LLMProvider.OLLAMA:
            return self._call_ollama(messages, max_tokens, temperature)
        elif provider == LLMProvider.LMSTUDIO:
            return self._call_openai_compat(messages, max_tokens, temperature)
        elif provider == LLMProvider.OPENAI:
            return self._call_openai_compat(messages, max_tokens, temperature)
        elif provider == LLMProvider.AZURE:
            return self._call_openai_compat(messages, max_tokens, temperature)
        elif provider == LLMProvider.OPENROUTER:
            return self._call_openai_compat(messages, max_tokens, temperature)
        elif provider == LLMProvider.ANTHROPIC:
            return self._call_openai_compat(messages, max_tokens, temperature)
        elif provider == LLMProvider.GEMINI:
            return self._call_openai_compat(messages, max_tokens, temperature)
        else:
            logger.warning(
                "Unknown provider %s, falling back to OpenAI-compat", provider
            )
            return self._call_openai_compat(messages, max_tokens, temperature)

    def _call_openai_compat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call an OpenAI-compatible chat completions endpoint."""
        url = self._normalize_url(self.settings.llm_url)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.settings.llm_timeout) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))

        choice = resp_data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")
        return LLMResponse(content=content.strip(), reasoning=reasoning, raw=resp_data)

    def _call_ollama(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call the Ollama generate endpoint."""
        base_url = self._normalize_url(self.settings.llm_url)
        parsed = urllib.parse.urlparse(base_url)
        path = parsed.path
        if "/api/chat" not in path:
            base_url = f"{parsed.scheme}://{parsed.netloc}/api/chat"

        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            base_url, data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.settings.llm_timeout) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))

        content = resp_data.get("message", {}).get("content", "")
        reasoning = resp_data.get("reasoning_content", "")
        return LLMResponse(content=content.strip(), reasoning=reasoning, raw=resp_data)

    @staticmethod
    def _normalize_url(raw_url: str) -> str:
        """Ensure URL has the correct v1/chat/completions path for OpenAI-compat."""
        parsed = urllib.parse.urlparse(raw_url)
        path = parsed.path
        if "/v1/chat/completions" not in path:
            base = raw_url.rstrip("/")
            return base + "/v1/chat/completions"
        return raw_url


def extend_settings_with_llm(settings: Any) -> Any:
    """Patch settings object with LLM-specific defaults if missing."""
    if not hasattr(settings, "llm_rate_limit_rpm"):
        settings.llm_rate_limit_rpm = 30
    if not hasattr(settings, "llm_max_burst"):
        settings.llm_max_burst = 5
    return settings
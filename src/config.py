"""
Configuration and settings management.

Centralized config with Pydantic v2 validation.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .constants import (
    DEFAULT_TACC_END_DATE,
    DEFAULT_TACC_START_DATE,
    DEFAULT_FIRST_NAME,
    DEFAULT_LAST_NAME,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_LLM_URL,
    DEFAULT_TEMPLATE,
    MAX_FIRST_NAME_LENGTH,
    MAX_LAST_NAME_LENGTH,
    MAX_LLM_MAX_TOKENS,
    MAX_LLM_TIMEOUT,
    MAX_MAX_BURST,
    MAX_PROJECT_DURATION_DAYS,
    MAX_RATE_LIMIT_RPM,
    MIN_FIRST_NAME_LENGTH,
    MIN_LAST_NAME_LENGTH,
    MIN_LLM_MAX_TOKENS,
    MIN_LLM_TIMEOUT,
    MIN_MAX_BURST,
    MIN_PROJECT_DURATION_DAYS,
    MIN_RATE_LIMIT_RPM,
    SUPPORTED_LLM_PROVIDERS,
    VALID_TEMPLATES,
)


def _load_env_file(path: str) -> dict[str, str]:
    """Load key=value pairs from a .env file."""
    config: dict[str, str] = {}
    if not os.path.exists(path):
        return config
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    return config


def _parse_csv_set(value: str) -> frozenset[str]:
    """Parse comma-separated values into a frozen set (lowercased, stripped)."""
    return frozenset(c.strip().lower() for c in value.split(",") if c.strip())


def _chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split long text into chunks at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    for paragraph in text.split("\n"):
        while len(paragraph) > max_chars:
            split_at = paragraph.rfind(". ", 0, max_chars)
            if split_at == -1:
                split_at = max_chars
            chunks.append(paragraph[: split_at + 1])
            paragraph = paragraph[split_at + 1 :].strip()
        if paragraph:
            chunks.append(paragraph)
    return chunks


def parse_date(date_str: str) -> datetime | None:
    """Parse a date string using known formats."""
    from datetime import datetime

    DEFAULT_DATE_FORMATS = ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d")
    for fmt in DEFAULT_DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def get_customer_group(name: str) -> str:
    """Extract the base customer group name (before parens / hyphens)."""
    if not name:
        return "Unknown"
    import re

    match = re.match(r"^([^()\-#]+)", name)
    return match.group(1).strip() if match else name.strip()


def load_json(path: str) -> list[dict[str, Any]]:
    """Load JSON data from a file."""
    import json

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Settings(BaseModel):
    """Centralized configuration loaded from .env with Pydantic validation."""

    # TACC
    tacc_email: str = Field(default="", description="TACC account email")
    tacc_password: str = Field(default="", description="TACC account password")
    tacc_start_date: str = Field(
        default=DEFAULT_TACC_START_DATE, description="Start date for timesheet fetch"
    )
    tacc_end_date: str = Field(
        default=DEFAULT_TACC_END_DATE, description="End date for timesheet fetch"
    )

    # Personal
    first_name: str = Field(
        default=DEFAULT_FIRST_NAME,
        min_length=MIN_FIRST_NAME_LENGTH,
        max_length=MAX_FIRST_NAME_LENGTH,
    )
    last_name: str = Field(
        default=DEFAULT_LAST_NAME,
        min_length=MIN_LAST_NAME_LENGTH,
        max_length=MAX_LAST_NAME_LENGTH,
    )
    title: str = Field(default="auto")
    email: str = Field(default="")
    phone: str = Field(default="")
    location: str = Field(default="")
    linkedin: str = Field(default="")

    # Resume
    min_project_duration_days: int = Field(
        default=30, ge=MIN_PROJECT_DURATION_DAYS, le=MAX_PROJECT_DURATION_DAYS
    )
    output_dir: str = Field(default="output")
    input_path: str = Field(default="input/tacc.json")

    # Exclusions
    excluded_customers: frozenset[str] = Field(default_factory=frozenset)
    technology_blacklist: frozenset[str] = Field(default_factory=frozenset)

    # LLM
    use_llm: bool = Field(default=False)
    llm_url: str = Field(default=DEFAULT_LLM_URL)
    llm_model: str = Field(default=DEFAULT_LLM_MODEL)
    llm_provider: str = Field(default=DEFAULT_LLM_PROVIDER)
    llm_api_key: str = Field(default="")
    llm_timeout: int = Field(default=DEFAULT_LLM_TIMEOUT, ge=MIN_LLM_TIMEOUT, le=MAX_LLM_TIMEOUT)
    llm_max_tokens: int = Field(
        default=DEFAULT_LLM_MAX_TOKENS, ge=MIN_LLM_MAX_TOKENS, le=MAX_LLM_MAX_TOKENS
    )

    # Template
    resume_template: str = Field(default=DEFAULT_TEMPLATE, description="Resume template name")
    # Education (optional)
    education: str = Field(default="")

    @field_validator("resume_template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        if v.lower() not in VALID_TEMPLATES:
            raise ValueError(
                f"Unknown template: {v}. Must be one of: {', '.join(sorted(VALID_TEMPLATES))}"
            )
        return v.lower()

    @field_validator("llm_url")
    @classmethod
    def validate_llm_url(cls, v: str) -> str:
        """Ensure LLM URL is a valid HTTP/HTTPS URL."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError(f"LLM URL must start with http:// or https://, got: {v}")
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider is supported."""
        from .llm import LLMProvider

        valid_providers = SUPPORTED_LLM_PROVIDERS
        if v.lower() not in valid_providers:
            raise ValueError(
                f"Unsupported LLM provider: {v}. "
                f"Must be one of: {', '.join(sorted(valid_providers))}"
            )
        return v.lower()

    @field_validator("tacc_start_date", "tacc_end_date")
    @classmethod
    def validate_date_string(cls, v: str) -> str:
        """Validate that date strings are parseable."""
        if v:
            parsed = parse_date(v)
            if parsed is None:
                import warnings

                warnings.warn(f"Date string '{v}' could not be parsed with known formats")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation if provided."""
        if v and "@" not in v:
            raise ValueError(f"Invalid email address: {v}")
        return v

    @field_validator("excluded_customers", "technology_blacklist", mode="before")
    @classmethod
    def validate_frozenset(cls, v: Any) -> frozenset:
        """Ensure frozenset fields accept list/tuple inputs."""
        if isinstance(v, (list, tuple, set)):
            return frozenset(str(x).lower().strip() for x in v if x)
        if isinstance(v, frozenset):
            return v
        return frozenset()

    @classmethod
    def from_env(cls, path: str = ".env") -> "Settings":
        """Build Settings from a .env file with Pydantic validation."""
        raw = _load_env_file(path)

        def g(key: str, default: str = "") -> str:
            return raw.get(key, default) or default

        excluded = _parse_csv_set(g("ENV_EXCLUDE_CUSTOMERS", ""))
        blacklist = _parse_csv_set(g("ENV_TECHNOLOGY_BLACKLIST", ""))

        kwargs: dict[str, Any] = {
            "tacc_email": g("TACC_EMAIL"),
            "tacc_password": g("TACC_PASSWORD"),
            "tacc_start_date": g("TACC_START_DATE", DEFAULT_TACC_START_DATE),
            "tacc_end_date": g("TACC_END_DATE", DEFAULT_TACC_END_DATE),
            "first_name": g("FIRST_NAME", DEFAULT_FIRST_NAME),
            "last_name": g("LAST_NAME", DEFAULT_LAST_NAME),
            "title": g("TITLE", "auto"),
            "email": g("EMAIL"),
            "phone": g("PHONE"),
            "location": g("LOCATION"),
            "linkedin": g("LINKEDIN"),
            "resume_template": g("RESUME_TEMPLATE", "modern"),
            "min_project_duration_days": int(g("MINIMUM_PROJECT_DURATION_DAYS", "30")),
            "excluded_customers": excluded,
            "technology_blacklist": blacklist,
            "use_llm": g("USE_LLM", "false").lower() in ("true", "1", "yes"),
            "llm_url": g("LLM_URL", DEFAULT_LLM_URL),
            "llm_model": g("LLM_MODEL", DEFAULT_LLM_MODEL),
            "llm_provider": g("LLM_PROVIDER", DEFAULT_LLM_PROVIDER),
            "llm_api_key": g("LLM_API_KEY"),
            "llm_timeout": int(g("LLM_TIMEOUT", str(DEFAULT_LLM_TIMEOUT))),
            "llm_max_tokens": int(g("LLM_MAX_TOKENS", str(DEFAULT_LLM_MAX_TOKENS))),
            "education": g("EDUCATION"),
        }

        try:
            return cls(**kwargs)
        except Exception as e:
            import logging

            logger = logging.getLogger("TACC Resume builder")
            logger.error("Settings validation failed: %s", e)
            raise

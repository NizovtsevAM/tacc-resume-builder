"""
Project-wide constants and configuration defaults.
"""

from __future__ import annotations

from typing import Tuple

# Technology extraction
TECH_SAMPLE_SIZE: int = 50
TECH_MAX_ITEMS: int = 30

# LLM retry
LLM_MAX_RETRIES: int = 4
LLM_RETRY_BACKOFF_BASE: int = 2  # seconds

# Prompt size limits (characters)
LLM_PROMPT_MAX_CHARS: int = 8000
LLM_TECHNOLOGY_PROMPT_MAX: int = 6000
LLM_WORK_TYPE_PROMPT_MAX: int = 4000
LLM_SUMMARY_PROMPT_MAX: int = 3000

# Rate limiter defaults
RATE_LIMITER_DEFAULT_RPM: int = 30
RATE_LIMITER_DEFAULT_BURST: int = 5
RATE_LIMITER_ACQUIRE_TIMEOUT: float = 30.0

# Templates
TEMPLATE_DIR: str = "templates"
DEFAULT_TEMPLATE: str = "modern"
VALID_TEMPLATES: frozenset[str] = frozenset({"modern", "classic", "minimalist", "creative"})

# Date formats
DEFAULT_DATE_FORMATS: tuple[str, ...] = (
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%Y/%m/%d",
)

# Logging
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL: int = 20  # logging.INFO

# Exports
JSON_INDENT: int = 2
DEFAULT_OUTPUT_DIR: str = "output"
DEFAULT_INPUT_PATH: str = "input/tacc.json"

# Validation bounds
MIN_PROJECT_DURATION_DAYS: int = 1
MAX_PROJECT_DURATION_DAYS: int = 3650
MIN_FIRST_NAME_LENGTH: int = 1
MAX_FIRST_NAME_LENGTH: int = 100
MIN_LAST_NAME_LENGTH: int = 1
MAX_LAST_NAME_LENGTH: int = 100
MIN_LLM_TIMEOUT: int = 10
MAX_LLM_TIMEOUT: int = 600
MIN_LLM_MAX_TOKENS: int = 100
MAX_LLM_MAX_TOKENS: int = 32000
MIN_RATE_LIMIT_RPM: int = 1
MAX_RATE_LIMIT_RPM: int = 1000
MIN_MAX_BURST: int = 1
MAX_MAX_BURST: int = 100

# Default .env values
DEFAULT_TACC_START_DATE: str = "1/1/2011"
DEFAULT_TACC_END_DATE: str = "6/30/2026"
DEFAULT_FIRST_NAME: str = "John"
DEFAULT_LAST_NAME: str = "Doe"
DEFAULT_LLM_URL: str = "http://127.0.0.1:1234"
DEFAULT_LLM_MODEL: str = "google/gemma-4-e4b"
DEFAULT_LLM_PROVIDER: str = "lmstudio"
DEFAULT_LLM_TIMEOUT: int = 120
DEFAULT_LLM_MAX_TOKENS: int = 4000

# Supported LLM providers (values must match config.LLMProvider enum)
SUPPORTED_LLM_PROVIDERS: frozenset[str] = frozenset(
    {"openai", "azure", "lmstudio", "ollama", "openrouter", "anthropic", "gemini"}
)

# Default exclusions
DEFAULT_EXCLUDED_CUSTOMERS: tuple[str, ...] = (
    "vacation",
    "training",
    "sick",
    "sickness",
    "bench",
    "holiday",
    "day off",
    "break",
    "leave",
    "pto",
    "personal time",
    "admin",
    "office",
    "meeting",
    "conference",
    "workshop",
    "seminar",
    "interview",
    "recruitment",
)

DEFAULT_TECHNOLOGY_BLACKLIST: tuple[str, ...] = (
    "template",
    "extraction",
    "data scraping",
    "ui",
    "db",
    "it",
    "enum",
    "ie",
    "dropbox",
    "link",
    "file",
    "office",
    "admin",
    "support",
    "meeting",
)

# Skill categories ordering for display (HTML and DOCX)
SKILL_CATEGORIES: tuple[str, ...] = (
    "Backend",
    "Frontend",
    "Cloud",
    "DevOps",
    "Databases",
    "Testing",
    "Data Engineering",
    "Architecture",
)

# LLM API URL paths
LLM_OPENAI_COMPAT_PATH: str = "/v1/chat/completions"
LLM_OLLAMA_PATH: str = "/api/chat"

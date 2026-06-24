"""
TACC Resume Builder — Production-Grade Universal Resume Generator.

Modular architecture v2 — refactored from monolithic main.py into focused modules.
"""

from .config import Settings, parse_date, get_customer_group, load_json
from .models import ResumeProject, ResumeProfile
from .llm import (
    BaseLLMClient,
    LLMProvider,
    LLMResponse,
    LLMProviderError,
    TokenBucketRateLimiter,
)
from .extractors import TechnologyExtractor, extract_work_types
from .generators import (
    AchievementGenerator,
    ProfessionDetector,
    SkillCategorizer,
    generate_professional_summary,
    infer_project_role,
)
from .processors import ResumeDataProcessor
from .exporters import (
    export_resume_json,
    export_resume_html,
    save_document,
    ResumeDocumentGenerator,
)
from .workflows import workflow_fetch, workflow_generate

__all__ = [
    "Settings",
    "parse_date",
    "get_customer_group",
    "load_json",
    "ResumeProject",
    "ResumeProfile",
    "BaseLLMClient",
    "LLMProvider",
    "LLMResponse",
    "LLMProviderError",
    "TokenBucketRateLimiter",
    "TechnologyExtractor",
    "extract_work_types",
    "AchievementGenerator",
    "ProfessionDetector",
    "SkillCategorizer",
    "generate_professional_summary",
    "infer_project_role",
    "ResumeDataProcessor",
    "export_resume_json",
    "export_resume_html",
    "save_document",
    "ResumeDocumentGenerator",
    "workflow_fetch",
    "workflow_generate",
]

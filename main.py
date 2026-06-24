#!/usr/bin/env python3
"""
TACC Resume builder — Production-Grade Universal Resume Generator (v3).

Compatibility wrapper — imports from modular src/ package.
See src/ for the actual implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Re-export all public API from the modular package
from src import (
    Settings,
    ResumeProject,
    ResumeProfile,
    BaseLLMClient,
    LLMProvider,
    LLMResponse,
    LLMProviderError,
    TokenBucketRateLimiter,
    TechnologyExtractor,
    extract_work_types,
    AchievementGenerator,
    ProfessionDetector,
    SkillCategorizer,
    generate_professional_summary,
    infer_project_role,
    ResumeDataProcessor,
    export_resume_json,
    export_resume_html,
    save_document,
    ResumeDocumentGenerator,
    workflow_fetch,
    workflow_generate,
    parse_date,
    get_customer_group,
    load_json,
)

# Configure logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    from src.workflows import main

    sys.exit(0 if main() else 1)

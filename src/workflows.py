"""
Workflows — high-level orchestration: fetch TACC data, generate resume, CLI.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request

from .config import Settings
from .exporters import export_resume_html, export_resume_json, save_document
from .llm import BaseLLMClient, LLMProviderError
from .processors import ResumeDataProcessor

logger = logging.getLogger("TACC Resume builder")

MAX_RETRIES = 4
RETRY_BACKOFF_SEC = 2


def tacc_authenticate(email: str, password: str) -> str:
    """Authenticate with TACC API and return the token."""
    auth_url = "https://tacc.tula.co/api/auth"
    auth_data = json.dumps({"Email": email, "Password": password}).encode("utf-8")

    req = urllib.request.Request(
        auth_url,
        data=auth_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        resp_data = json.loads(response.read().decode("utf-8"))

    token = (
        resp_data.get("token")
        or resp_data.get("Token")
        or resp_data.get("access_token")
        or resp_data.get("accessToken")
    )
    if not token:
        raise LLMProviderError(f"No token in auth response. Keys: {list(resp_data.keys())}")
    return token


def fetch_timesheet(token: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch timesheet data from TACC API."""
    start_encoded = urllib.parse.quote(start_date)
    end_encoded = urllib.parse.quote(end_date)
    url = f"https://tacc.tula.co/api/timesheet?startDate={start_encoded}&endDate={end_encoded}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))

    records = data if isinstance(data, list) else data.get("data", data.get("records", []))
    logger.info("Fetched %d records from TACC", len(records))
    return records


def workflow_fetch(settings: Settings) -> bool:
    """Fetch TACC data and save to disk."""
    if not settings.tacc_email or not settings.tacc_password:
        logger.error("TACC_EMAIL and TACC_PASSWORD must be set in .env")
        return False

    try:
        logger.info("Authenticating with TACC...")
        token = tacc_authenticate(settings.tacc_email, settings.tacc_password)

        logger.info(
            "Fetching timesheet data %s → %s...",
            settings.tacc_start_date,
            settings.tacc_end_date,
        )
        records = fetch_timesheet(token, settings.tacc_start_date, settings.tacc_end_date)

        import os

        os.makedirs(os.path.dirname(settings.input_path) or ".", exist_ok=True)
        with open(settings.input_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        logger.info("Data saved to %s", settings.input_path)
        logger.info("Fetch completed successfully.")
        return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error("TACC API error: %s — %s", e.code, error_body[:500])
        return False
    except Exception as e:
        logger.error("TACC fetch failed: %s", e)
        return False


def workflow_generate(settings: Settings) -> bool:
    """Generate resume from TACC data."""
    import os

    if not os.path.exists(settings.input_path):
        logger.error("Input file not found: %s", settings.input_path)
        logger.info("Run the 'fetch' workflow first, or place data at %s", settings.input_path)
        return False

    try:
        llm: BaseLLMClient | None = None
        if settings.use_llm:
            try:
                llm = BaseLLMClient(settings)
                _ = llm.chat(
                    [{"role": "user", "content": "ping"}],
                    max_tokens=10,
                    cache_key="ping",
                )
                logger.info(
                    "LLM client initialized (%s / %s)",
                    settings.llm_provider,
                    settings.llm_model,
                )
            except Exception as e:
                logger.warning("LLM initialization failed, continuing without LLM: %s", e)
                llm = None
        else:
            logger.info("LLM analysis disabled (set USE_LLM=true in .env to enable)")

        processor = ResumeDataProcessor(settings, llm)
        profile = processor.process()

        if not profile.projects:
            logger.error("No projects generated. Cannot create resume.")
            return False

        logger.info(
            "Generated resume for: %s (%s)",
            profile.profession,
            profile.years_experience,
        )

        json_path = os.path.join(settings.output_dir, "resume.json")
        export_resume_json(profile, json_path)

        from .exporters import ResumeDocumentGenerator

        doc_gen = ResumeDocumentGenerator(settings)
        doc = doc_gen.generate(profile)

        docx_path = os.path.join(settings.output_dir, "resume.docx")
        save_document(doc, docx_path)

        html_path = os.path.join(settings.output_dir, "resume.html")
        export_resume_html(profile, settings, html_path)

        logger.info("Resume generation completed successfully.")
        return True

    except Exception as e:
        logger.error("Resume generation failed: %s", e)
        import traceback

        traceback.print_exc()
        return False


def show_menu() -> str:
    """Display menu and return user choice."""
    print()
    print("=" * 60)
    print("  RESUME GENERATION PIPELINE v3")
    print("=" * 60)
    print()
    print("  Choose a workflow:")
    print("    1. Fetch   — Download timesheet data from TACC API")
    print("    2. Generate — Create resume from timesheet data")
    print("    3. Both    — Fetch data and generate resume")
    print("    0. Exit")
    print("=" * 60)

    while True:
        try:
            choice = input("\n  Enter your choice (0-3): ").strip()
            if choice in ("0", "1", "2", "3"):
                return choice
            print("  Invalid choice. Please enter 0, 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print("\n  Interrupted.")
            sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="tacc-resume-builder",
        description="Generate professional resumes from TACC time-tracking data",
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        default="menu",
        choices=["menu", "fetch", "generate", "both"],
        help="Workflow to run (default: menu)",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Override resume template (modern, classic, minimalist, creative)",
    )
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM for this run")
    parser.add_argument("--input", default=None, help="Override input JSON path")
    parser.add_argument("--output", default=None, help="Override output directory")
    parser.add_argument(
        "--from-date",
        default=None,
        help="Only use records from this date onward (M/D/YYYY)",
    )
    return parser.parse_args()


def apply_args_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    """Apply CLI overrides to settings."""
    import copy

    data = settings.model_dump()
    if args.template:
        data["resume_template"] = args.template
    if args.no_llm:
        data["use_llm"] = False
    if args.input:
        data["input_path"] = args.input
    if args.output:
        data["output_dir"] = args.output
    return Settings(**data)


def main() -> bool:
    """Main entry point. Supports both interactive menu and CLI flags."""
    settings = Settings.from_env(".env")
    logger.info(
        "Configuration loaded. LLM: %s, Provider: %s",
        settings.use_llm,
        settings.llm_provider,
    )

    args = parse_args()

    # CLI mode
    if args.workflow != "menu":
        settings = apply_args_overrides(settings, args)
        logger.info(
            "CLI mode: workflow=%s, template=%s, no_llm=%s",
            args.workflow,
            settings.resume_template,
            args.no_llm,
        )
        if args.workflow == "fetch":
            return workflow_fetch(settings)
        if args.workflow == "generate":
            return workflow_generate(settings)
        if args.workflow == "both":
            fetch_ok = workflow_fetch(settings)
            if not fetch_ok:
                print("\n  Fetch failed. Skipping resume generation.")
                return False
            return workflow_generate(settings)

    # Interactive menu
    choice = show_menu()

    if choice == "0":
        print("  Exiting.")
        return True

    success = True

    if choice in ("1", "3"):
        if not workflow_fetch(settings):
            success = False
            if choice == "3":
                print("\n  Fetch failed. Skipping resume generation.")
                return False

    if choice in ("2", "3"):
        if not workflow_generate(settings):
            success = False

    if success:
        print("\n  ✓ All operations completed successfully!\n")

    return success

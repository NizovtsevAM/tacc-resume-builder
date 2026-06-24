"""
Integration tests — end-to-end pipeline with in-memory LLM mock.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from src.config import Settings
from src.processors import ResumeDataProcessor


class FakeLLM:
    """Minimal in-memory LLM stub for integration tests."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        cache_key: str | None = None,
    ) -> str:
        content = " ".join(m.get("content", "") for m in messages)
        self.calls.append({"content": content, "system_prompt": system_prompt})
        if cache_key and cache_key in self.responses:
            return self.responses[cache_key]
        return "Senior Full Stack Developer"


@pytest.fixture()
def sample_settings(tmp_path: str) -> Settings:
    input_path = str(tmp_path / "tacc.json")
    data = [
        {
            "CustomerName": "Acme",
            "Date": "2023-01-01",
            "Description": "Developed ASP.NET Core APIs and React frontend",
            "ContractId": 1,
            "Hours": 8,
        },
        {
            "CustomerName": "Acme",
            "Date": "2024-01-02",
            "Description": "Deployed microservices to Azure Kubernetes Service",
            "ContractId": 1,
            "Hours": 8,
        },
        {
            "CustomerName": "Internal",
            "Date": "2024-01-03",
            "Description": "Internal meeting",
            "ContractId": None,
            "Hours": 1,
        },
    ]
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    env_path = str(tmp_path / ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(
            "FIRST_NAME=Test\nLAST_NAME=User\n"
            f"INPUT_PATH={input_path}\n"
            f"OUTPUT_DIR={tmp_path}/out\nRESUME_TEMPLATE=modern\nUSE_LLM=false\n"
        )

    settings = Settings.from_env(env_path)
    settings.input_path = input_path

    # integration test override
    settings.min_project_duration_days = 1

    return settings


def test_full_pipeline_returns_profile(sample_settings: Settings) -> None:
    processor = ResumeDataProcessor(sample_settings)
    profile = processor.process()

    assert profile.years_experience > 0
    assert profile.profession
    assert profile.summary
    assert profile.projects
    assert any("Acme" in (p.customer or "") for p in profile.projects)
    assert not any("Internal" == (p.customer or "") for p in profile.projects)


def test_pipeline_with_llm_mock(sample_settings: Settings) -> None:
    fake_llm = FakeLLM()
    sample_settings.use_llm = True
    processor = ResumeDataProcessor(sample_settings, llm=fake_llm)
    profile = processor.process()

    assert profile.profession == "Senior Full Stack Developer"


def test_html_export_contains_name(tmp_path: str, sample_settings: Settings) -> None:
    from src.exporters import export_resume_html

    processor = ResumeDataProcessor(sample_settings)
    profile = processor.process()
    html_path = str(tmp_path / "resume.html")
    export_resume_html(profile, sample_settings, html_path)

    html = open(html_path, "r", encoding="utf-8").read()
    assert profile.profession in html

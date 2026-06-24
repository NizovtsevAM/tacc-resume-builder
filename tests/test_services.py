"""
Unit tests for Resume Generation Pipeline v3 service components.

Tests are designed to be deterministic — they mock LLM responses and
use fixture data to verify service logic independently.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import main


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sample_descriptions() -> list[str]:
    return [
        "Implemented REST API endpoints for customer management using ASP.NET Core and Entity Framework",
        "Fixed bugs in the authentication module related to JWT token validation",
        "Refactored legacy SQL stored procedures to use Entity Framework Core",
        "Set up CI/CD pipeline using GitHub Actions and Docker",
        "Developed React frontend components for the new dashboard",
        "Migrated data from legacy SQL Server to PostgreSQL",
    ]


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM client that returns pre-defined responses."""
    mock = MagicMock(spec=main.BaseLLMClient)
    mock.chat.return_value = "ASP.NET Core, Entity Framework, C#, Azure, Docker, React, TypeScript"
    return mock


@pytest.fixture
def sample_settings() -> main.Settings:
    return main.Settings(
        first_name="Test",
        last_name="User",
        min_project_duration_days=1,
        output_dir=tempfile.mkdtemp(),
        input_path="test_input.json",
    )


@pytest.fixture
def tacc_sample_data() -> list[dict]:
    """Simulated TACC timesheet data."""
    return [
        {
            "CustomerName": "TestCorp",
            "ContractId": "C001",
            "Date": "1/15/2023",
            "Description": "Developed new feature for user management",
        },
        {
            "CustomerName": "TestCorp",
            "ContractId": "C001",
            "Date": "1/16/2023",
            "Description": "Fixed critical bug in payment processing",
        },
        {
            "CustomerName": "TestCorp",
            "ContractId": "C001",
            "Date": "1/17/2023",
            "Description": "Code review and documentation updates",
        },
        {
            "CustomerName": "NonBillableCorp",
            "Date": "1/15/2023",
            "Description": "Internal meeting",
        },
    ]


# ===========================================================================
# Tests: TokenBucketRateLimiter
# ===========================================================================


class TestTokenBucketRateLimiter:
    def test_acquire_single_token(self):
        limiter = main.TokenBucketRateLimiter(tokens_per_minute=60, max_burst=10)
        assert limiter.acquire(timeout=1.0) is True
        assert limiter.available_tokens < 10  # one token consumed

    def test_acquire_multiple_tokens(self):
        limiter = main.TokenBucketRateLimiter(tokens_per_minute=60, max_burst=10)
        assert limiter.acquire(tokens=5, timeout=1.0) is True
        assert limiter.available_tokens < 10

    def test_rate_limit_exceeded(self):
        limiter = main.TokenBucketRateLimiter(tokens_per_minute=1, max_burst=1)
        # Consume the only token
        assert limiter.acquire(timeout=0.1) is True
        # Should fail due to rate limit (timeout too short)
        assert limiter.acquire(timeout=0.1) is False

    def test_token_refill(self):
        limiter = main.TokenBucketRateLimiter(tokens_per_minute=120, max_burst=5)
        # Consume all tokens
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True
        # Should be empty
        assert limiter.available_tokens < 1
        # Wait for refill
        import time

        time.sleep(0.5)
        assert limiter.available_tokens > 0

    def test_is_available_property(self):
        limiter = main.TokenBucketRateLimiter(tokens_per_minute=60, max_burst=3)
        assert limiter.is_available is True
        limiter.acquire(tokens=3)
        assert limiter.is_available is False


# ===========================================================================
# Tests: TechnologyExtractor
# ===========================================================================


class TestTechnologyExtractor:
    def test_extract_regex_only(self, sample_descriptions):
        extractor = main.TechnologyExtractor()
        techs = extractor.extract(sample_descriptions, use_llm=False)
        assert isinstance(techs, list)
        assert len(techs) > 0
        # Should contain known techs from patterns
        techs_lower = [t.lower() for t in techs]
        assert "react" in techs_lower or any("react" in t for t in techs_lower)
        assert "docker" in techs_lower

    def test_extract_with_llm(self, sample_descriptions, mock_llm):
        extractor = main.TechnologyExtractor(llm=mock_llm)
        techs = extractor.extract(sample_descriptions, use_llm=True)
        assert isinstance(techs, list)
        # LLM was called
        mock_llm.chat.assert_called_once()

    def test_extract_empty_descriptions(self):
        extractor = main.TechnologyExtractor()
        assert extractor.extract([]) == []

    def test_extract_with_blacklist(self, sample_descriptions):
        blacklist = frozenset({"docker"})
        extractor = main.TechnologyExtractor(blacklist=blacklist)
        techs = extractor.extract(sample_descriptions, use_llm=False)
        techs_lower = [t.lower() for t in techs]
        assert "docker" not in techs_lower

    def test_is_valid_generic_terms(self):
        extractor = main.TechnologyExtractor()
        assert extractor._is_valid("Docker") is True
        assert extractor._is_valid("go") is False  # generic term
        assert extractor._is_valid("it") is False
        assert extractor._is_valid("California") is False  # US state
        assert extractor._is_valid("UI") is False  # too short
        assert extractor._is_valid("Python") is True

    def test_sample_descriptions(self):
        descs = ["short"] * 100
        sampled = main.TechnologyExtractor._sample_descriptions(descs, 10)
        assert len(sampled) <= 10
        assert isinstance(sampled, list)


# ===========================================================================
# Tests: Work Type Extractor
# ===========================================================================


class TestWorkTypeExtractor:
    def test_extract_work_types_keyword(self, sample_descriptions):
        types = main.extract_work_types(sample_descriptions, use_llm=False)
        assert isinstance(types, list)
        assert len(types) > 0
        assert len(types) <= 6
        # Should contain relevant types
        types_str = " ".join(types).lower()
        assert "api" in types_str or "bug" in types_str or "refactoring" in types_str

    def test_extract_work_types_empty(self):
        assert main.extract_work_types([]) == []

    def test_extract_work_types_with_llm(self, sample_descriptions, mock_llm):
        types = main.extract_work_types(sample_descriptions, llm=mock_llm, use_llm=True)
        assert isinstance(types, list)
        assert len(types) <= 6


# ===========================================================================
# Tests: AchievementGenerator
# ===========================================================================


class TestAchievementGenerator:
    def test_generate_heuristic(self, sample_descriptions):
        gen = main.AchievementGenerator()
        responsibilities, achievements = gen.generate(
            sample_descriptions,
            technologies=["C#", "React", "Azure"],
            work_types=["New Feature Development", "Bug Fixing"],
            use_llm=False,
        )
        assert isinstance(responsibilities, list)
        assert isinstance(achievements, list)
        assert len(responsibilities) > 0
        assert len(achievements) > 0

    def test_generate_empty_descriptions(self):
        gen = main.AchievementGenerator()
        resp, ach = gen.generate([], [], [])
        assert resp == []
        assert ach == []

    def test_generate_meaningful_filter(self):
        gen = main.AchievementGenerator()
        descs = [
            "Daily standup meeting",
            "Email communication with team",
            "Developed new authentication system using OAuth 2.0",
        ]
        resp, ach = gen.generate(descs, ["OAuth"], [], use_llm=False)
        assert len(resp) > 0
        # Should filter out meeting/email descriptions
        resp_text = " ".join(resp).lower()
        assert "standup" not in resp_text

    def test_generate_with_llm(self, sample_descriptions, mock_llm):
        mock_llm.chat.return_value = (
            "RESPONSIBILITIES:\n"
            "• Developed REST API endpoints using ASP.NET Core\n"
            "• Maintained and improved CI/CD pipelines\n\n"
            "ACHIEVEMENTS:\n"
            "• Reduced bug count by 40%\n"
            "• Migrated legacy system to modern architecture"
        )
        gen = main.AchievementGenerator(llm=mock_llm)
        responsibilities, achievements = gen.generate(
            sample_descriptions,
            technologies=["C#", "Azure"],
            work_types=["API Development"],
            use_llm=True,
        )
        assert len(responsibilities) > 0
        assert len(achievements) > 0
        mock_llm.chat.assert_called_once()


# ===========================================================================
# Tests: ProfessionDetector
# ===========================================================================


class TestProfessionDetector:
    def test_detect_full_stack(self):
        detector = main.ProfessionDetector()
        result = detector.detect(
            technologies=["C#", "React", "TypeScript", "Azure"],
            descriptions=["Full stack development"],
            work_types=[],
            use_llm=False,
        )
        assert result in [
            "Senior Full Stack Developer",
            "Backend Developer",
            "Software Developer",
        ]

    def test_detect_devops(self):
        detector = main.ProfessionDetector()
        result = detector.detect(
            technologies=["Docker", "Kubernetes", "Terraform", "Jenkins"],
            descriptions=["CI/CD pipeline setup"],
            work_types=[],
            use_llm=False,
        )
        assert "DevOps" in result

    def test_detect_heuristic_fallback(self):
        detector = main.ProfessionDetector()
        result = detector.detect(
            technologies=["UnknownTech1", "UnknownTech2"],
            descriptions=["General software work"],
            work_types=[],
            use_llm=False,
        )
        assert result == "Software Developer"

    def test_detect_with_llm(self, mock_llm):
        mock_llm.chat.return_value = "DevOps Engineer"
        detector = main.ProfessionDetector(llm=mock_llm)
        result = detector.detect(
            technologies=["Docker"],
            descriptions=["DevOps work"],
            work_types=["Infrastructure/DevOps"],
            use_llm=True,
        )
        assert result == "DevOps Engineer"
        mock_llm.chat.assert_called_once()


# ===========================================================================
# Tests: SkillCategorizer
# ===========================================================================


class TestSkillCategorizer:
    def test_categorize_backend(self):
        categorizer = main.SkillCategorizer()
        techs = ["C#", "Python", "ASP.NET Core"]
        result = categorizer.categorize(techs, use_llm=False)
        assert "Backend" in result
        assert "C#" in result["Backend"]
        assert "Python" in result["Backend"]

    def test_categorize_mixed(self):
        categorizer = main.SkillCategorizer()
        techs = ["C#", "React", "Azure", "SQL Server"]
        result = categorizer.categorize(techs, use_llm=False)
        assert "Backend" in result
        assert "Frontend" in result
        assert "Cloud" in result
        assert "Databases" in result

    def test_categorize_empty(self):
        categorizer = main.SkillCategorizer()
        assert categorizer.categorize([]) == {}

    def test_categorize_unknown(self):
        categorizer = main.SkillCategorizer()
        techs = ["SomeRandomTool2024"]
        result = categorizer.categorize(techs, use_llm=False)
        # Should go to "Other" category or stay in uncategorized
        if "Other" in result:
            assert "SomeRandomTool2024" in result["Other"]


# ===========================================================================
# Tests: Settings (Pydantic Validation)
# ===========================================================================


class TestSettingsPydantic:
    def test_default_settings(self):
        s = main.Settings()
        assert s.first_name == "John"
        assert s.last_name == "Doe"
        assert s.use_llm is False
        assert s.min_project_duration_days == 30

    def test_provider_validation(self):
        with pytest.raises(Exception):
            main.Settings(llm_provider="unsupported_provider")

    def test_url_validation(self):
        with pytest.raises(Exception):
            main.Settings(llm_url="not-a-url")

    def test_url_validation_http(self):
        s = main.Settings(llm_url="http://localhost:8080")
        assert s.llm_url == "http://localhost:8080"

    def test_invalid_provider(self):
        with pytest.raises(Exception, match="Unsupported LLM provider"):
            main.Settings(llm_provider="nonexistent")

    def test_min_max_bounds(self):
        with pytest.raises(Exception):
            main.Settings(min_project_duration_days=0)
        with pytest.raises(Exception):
            main.Settings(llm_timeout=5)  # below minimum 10
        with pytest.raises(Exception):
            main.Settings(llm_max_tokens=50)  # below minimum 100


# ===========================================================================
# Tests: parse_date
# ===========================================================================


class TestParseDate:
    def test_parse_mmddyyyy(self):
        dt = main.parse_date("01/15/2023")
        assert dt is not None
        assert dt.month == 1
        assert dt.day == 15
        assert dt.year == 2023

    def test_parse_iso_format(self):
        dt = main.parse_date("2023-01-15")
        assert dt is not None
        assert dt.month == 1

    def test_parse_invalid(self):
        assert main.parse_date("") is None
        assert main.parse_date("not-a-date") is None


# ===========================================================================
# Tests: ResumeDataProcessor
# ===========================================================================


class TestResumeDataProcessor:
    @pytest.fixture
    def processor(self, sample_settings):
        return main.ResumeDataProcessor(settings=sample_settings)

    def test_is_excluded_empty(self, processor):
        assert processor._is_excluded("AnyCorp") is False

    def test_is_excluded_matched(self, processor):
        processor.settings.excluded_customers = frozenset({"excluded corp"})
        assert processor._is_excluded("Excluded Corp") is True

    def test_categorize_records(self, processor, tacc_sample_data):
        result = processor._categorize_records(tacc_sample_data)
        assert "work" in result
        assert "non_billable" in result
        assert len(result["work"]) == 3  # TestCorp entries with ContractId
        assert len(result["non_billable"]) == 1  # NonBillableCorp without ContractId

    def test_categorize_records_with_exclusion(self, processor, tacc_sample_data):
        processor.settings.excluded_customers = frozenset({"testcorp"})
        result = processor._categorize_records(tacc_sample_data)
        # TestCorp entries should now be in non_billable
        assert len(result["non_billable"]) == 4  # all excluded


# ===========================================================================
# Tests: Profile and Domain Models
# ===========================================================================


class TestResumeProfile:
    def test_to_dict(self):
        project = main.ResumeProject(
            customer="TestCorp",
            role="Developer",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 6, 1),
            days=150,
            technologies=["C#", "Azure"],
            responsibilities=["Developed features"],
            achievements=["Delivered project on time"],
            work_types=["Development"],
        )
        profile = main.ResumeProfile(
            first_name="John",
            last_name="Doe",
            profession="Developer",
            summary="Test summary",
            skills={"Backend": ["C#"]},
            projects=[project],
        )
        d = profile.to_dict()
        assert d["profession"] == "Developer"
        assert d["summary"] == "Test summary"
        assert len(d["projects"]) == 1
        assert d["projects"][0]["technologies"] == ["Azure", "C#"]


class TestResumeProject:
    def test_duration_years(self):
        p = main.ResumeProject(
            customer="Test",
            role="Dev",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2022, 1, 1),
            days=730,
        )
        # Approximately 2 years
        assert p.duration_years() == pytest.approx(2.0, abs=0.1)


# ===========================================================================
# Tests: Utility Functions
# ===========================================================================


class TestChunkText:
    def test_chunk_short_text(self):
        from src.config import _chunk_text

        text = "Short text."
        assert _chunk_text(text, max_chars=100) == [text]

    def test_chunk_long_text(self):
        from src.config import _chunk_text

        text = ". ".join(["This is a long sentence with enough content to be split"] * 50)
        chunks = _chunk_text(text, max_chars=500)
        assert len(chunks) > 1
        assert all(len(c) <= 500 for c in chunks)


class TestParseCSVSet:
    def test_parse_csv_set(self):
        from src.config import _parse_csv_set

        result = _parse_csv_set("A, B, C")
        assert result == frozenset({"a", "b", "c"})

    def test_parse_csv_empty(self):
        from src.config import _parse_csv_set

        assert _parse_csv_set("") == frozenset()


class TestLoadEnvFile:
    def test_load_nonexistent(self):
        from src.config import _load_env_file

        result = _load_env_file("/nonexistent/.env")
        assert result == {}

    def test_load_with_comments(self):
        from src.config import _load_env_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# Comment\nKEY=value\nANOTHER=test\n")
            f.flush()
            result = _load_env_file(f.name)
            os.unlink(f.name)
        assert result == {"KEY": "value", "ANOTHER": "test"}


if __name__ == "__main__":
    pytest.main(["-v", __file__])

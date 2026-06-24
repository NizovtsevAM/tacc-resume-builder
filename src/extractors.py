"""
Extractors — technology detection and work type classification.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter

from .llm import BaseLLMClient, LLMClientProtocol
from .constants import LLM_PROMPT_MAX_CHARS, TECH_MAX_ITEMS, TECH_SAMPLE_SIZE

logger = logging.getLogger("TACC Resume builder")

WORK_TYPE_CATEGORIES = [
    "New Feature Development",
    "Bug Fixing",
    "Refactoring",
    "Technical Support",
    "Data Migration",
    "System Integration",
    "UI/Frontend Development",
    "API Development",
    "Data Pipeline/ETL",
    "Testing/QA",
    "Code Review",
    "Process Automation",
    "Infrastructure/DevOps",
    "Research",
    "Documentation",
    "Mentoring",
    "Performance Optimization",
    "Security",
]

WORK_TYPE_KEYWORDS = {
    "New Feature Development": ["feature", "implement", "develop", "build", "create", "add", "new"],
    "Bug Fixing": ["bug", "fix", "issue", "error", "broken", "defect", "incorrect"],
    "Refactoring": ["refactor", "clean", "rewrite", "rework", "modernize", "eliminate"],
    "Technical Support": ["support", "help", "assist", "investigate", "troubleshoot"],
    "Data Migration": ["migrat", "move data", "transfer", "import", "export"],
    "System Integration": ["integrat", "api", "connect", "interface"],
    "UI/Frontend Development": ["ui", "ux", "frontend", "front-end", "user interface", "portal", "web page"],
    "API Development": ["api", "endpoint", "rest", "graphql", "web service"],
    "Data Pipeline/ETL": ["etl", "pipeline", "data processing", "batch", "stream"],
    "Testing/QA": ["test", "qa", "automation", "unit test", "integration test"],
    "Code Review": ["code review", "pull request", "merge"],
    "Process Automation": ["automat", "script", "workflow", "pipeline"],
    "Infrastructure/DevOps": ["devops", "infrastructure", "deploy", "ci/cd", "container"],
    "Research": ["research", "investigat", "evaluate", "prove of concept", "poc"],
    "Documentation": ["document", "readme", "wiki", "spec"],
    "Mentoring": ["mentor", "teach", "coach", "guide", "pair programming"],
    "Performance Optimization": ["performance", "optimiz", "slow", "latency", "throughput"],
    "Security": ["security", "auth", "authenticat", "oauth", "vulnerability"],
}


class TechnologyExtractor:
    """Extracts and scores technologies from project descriptions."""

    TECH_PATTERNS = [
        (r"(?i)(?<!\w)(AWS|Amazon\s*Web\s*Services|Azure|GCP|Google\s*Cloud)(?!\w)", "Cloud"),
        (r"(?i)(?<!\w)(Docker|Kubernetes|K8s|Terraform|Helm|Ansible|Packer)(?!\w)", "DevOps"),
        (r"(?i)(?<!\w)(PostgreSQL|Postgres|MySQL|SQL\s*Server|MongoDB|Redis|Elasticsearch|ElasticSearch|Cassandra|DynamoDB|Cosmos\s*DB|MSSQL|SQLite|MariaDB)(?!\w)", "Database"),
        (r"(?i)(?<!\w)(React|Angular|Vue\.?js|Svelte|Next\.?js|Nuxt|Blazor|Webpack|Vite|Bootstrap|Tailwind|jQuery)(?!\w)", "Frontend"),
        (r"(?i)(?<!\w)(\.NET\s*(Core|Framework)?|ASP\.NET|C#|VB\.NET|F#|Entity\s*Framework|LINQ|WCF|WPF|WinForms|\.Net|\.net)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(Java|Spring\s*Boot|Spring|Kotlin|JVM|Hibernate|Maven|Gradle|JSP|Servlets)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(Python|Django|Flask|FastAPI|Celery|NumPy|Pandas|Jupyter)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(Node\.?js|Express|Nest\.?js|TypeScript|JavaScript|Deno|Bun|npm|yarn)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(Selenium|Playwright|Cypress|Puppeteer|Appium|TestCafe|xUnit|nUnit|Jest|Mocha|Chai|Jasmine|Karma|SpecFlow|Gauge|Postman|SoapUI|Swagger)(?!\w)", "Testing"),
        (r"(?i)(?<!\w)(Airflow|Spark|Databricks|dbt|Snowflake|Kafka|Flink|Hadoop|Hive|Presto|Trino|Apache\s*Spark|Apache\s*Airflow)(?!\w)", "Data Engineering"),
        (r"(?i)(?<!\w)(Golang|Rust|Scala|Swift|Ruby|PHP|Elixir|Clojure|Haskell|Perl)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(CI/CD|Jenkins|GitLab\s*CI|GitHub\s*Actions|CircleCI|TeamCity|ArgoCD|TravisCI|Bamboo)(?!\w)", "DevOps"),
        (r"(?i)(?<!\w)(RabbitMQ|SQS|SNS|ActiveMQ|NATS|ZeroMQ|Azure\s*Service\s*Bus)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(gRPC|REST|GraphQL|WebSocket|SOAP|OData|SignalR)(?!\w)", "Backend"),
        (r"(?i)(?<!\w)(Microservices|DDD|CQRS|Event\s*Sourcing|Event\s*Driven|Clean\s*Architecture|SOLID|Onion\s*Architecture|Hexagonal\s*Architecture)(?!\w)", "Architecture"),
        (r"(?i)(?<!\w)(React\s*Native|Flutter|Xamarin|MAUI|SwiftUI|UIKit|iOS|Android)(?!\w)", "Frontend"),
        (r"(?i)(?<!\w)(Windows\s*Server|Linux|Ubuntu|CentOS|Debian|RedHat|Nginx|Apache|IIS)(?!\w)", "DevOps"),
        (r"(?i)(?<!\w)(Git|SVN|TFS|Azure\s*DevOps|Jira|Confluence|Trello|Asana|Slack)(?!\w)", "DevOps"),
    ]

    def __init__(self, llm: LLMClientProtocol | None = None, blacklist: frozenset = frozenset()):
        self._llm = llm
        self._blacklist = blacklist

    def extract(self, descriptions: list[str], use_llm: bool = False) -> list[str]:
        if not descriptions:
            return []

        regex_techs = []
        for desc in descriptions:
            desc_clean = desc.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            for pattern, _ in self.TECH_PATTERNS:
                for match in re.finditer(pattern, desc_clean):
                    tech = match.group(1).strip()
                    if self._is_valid(tech):
                        regex_techs.append(tech)

        llm_techs = []
        if use_llm and self._llm:
            sample = self._sample_descriptions(descriptions, TECH_SAMPLE_SIZE)
            sample_text = "\n".join(sample)
            if len(sample_text) > LLM_PROMPT_MAX_CHARS:
                sample_text = sample_text[:LLM_PROMPT_MAX_CHARS]

            prompt = (
                "Extract all legitimate technologies, programming languages, frameworks, databases, tools, and platforms mentioned in these work descriptions.\n\n"
                "Rules:\n"
                "- Output ONLY a comma-separated list\n"
                "- No explanations, no bullet points, no markdown\n"
                "- Each item should be a single technology name (e.g., .NET, C#, React, Azure, Docker)\n"
                "- Include only real, verifiable technologies\n"
                "- Exclude: generic terms, state names, non-technical items\n\n"
                f"Descriptions:\n{sample_text}"
            )
            result = self._llm.chat(
                [{"role": "user", "content": prompt}],
                system_prompt="You are a technology extraction specialist. Output only comma-separated technology names.",
                max_tokens=500,
                temperature=0.1,
                cache_key=hashlib.md5(sample_text.encode()).hexdigest(),
            )
            if result:
                for item in result.split(","):
                    tech = item.strip()
                    if self._is_valid(tech):
                        llm_techs.append(tech)

        all_techs = regex_techs + llm_techs
        counter = Counter(t.lower() for t in all_techs)

        tech_map = {}
        for t in all_techs:
            key = t.lower()
            if key not in tech_map or len(t) > len(tech_map[key]):
                tech_map[key] = t

        scored = []
        max_freq = max(counter.values(), default=1)
        for key, freq in counter.most_common():
            name = tech_map[key]
            llm_bonus = 1.5 if name.lower() in {t.lower() for t in llm_techs} else 1.0
            confidence = min(1.0, (freq / max_freq) * llm_bonus)
            scored.append((name, freq, confidence))

        scored.sort(key=lambda x: (-x[1], -x[2]))
        return [name for name, _, _ in scored[:TECH_MAX_ITEMS]]

    def _is_valid(self, tech: str) -> bool:
        stripped = tech.strip()
        if not stripped or len(stripped) < 3:
            return False
        lower = stripped.lower()
        if lower in self._blacklist:
            return False
        if not any(c.isalnum() for c in stripped):
            return False
        if stripped.isdigit():
            return False
        generic = {
            "template", "data extraction", "data scraping", "ui", "db",
            "enum", "ie", "dropbox", "link", "file", "office", "admin",
            "support", "meeting", "email", "phone", "team", "project",
            "management", "documentation", "testing", "development",
            "samsung", "trello", "asana", "slack", "itunes",
            "monday", "basecamp", "notion", "clickup",
        }
        if lower in generic:
            return False
        us_states = {
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
            "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
            "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
            "maine", "maryland", "massachusetts", "michigan", "minnesota",
            "mississippi", "missouri", "montana", "nebraska", "nevada",
            "new hampshire", "new jersey", "new mexico", "new york",
            "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
            "pennsylvania", "rhode island", "south carolina", "south dakota",
            "tennessee", "texas", "utah", "vermont", "virginia", "washington",
            "west virginia", "wisconsin", "wyoming",
        }
        if lower in us_states:
            return False
        return True

    @staticmethod
    def _sample_descriptions(descriptions: list[str], max_items: int) -> list[str]:
        if len(descriptions) <= max_items:
            return descriptions
        unique = list(dict.fromkeys(descriptions))
        unique.sort(key=lambda x: (-len(x), x))
        sampled = []
        if len(unique) <= max_items:
            sampled = unique
        else:
            top_count = int(max_items * 0.6)
            sampled = unique[:top_count]
            remaining = unique[top_count:]
            step = max(1, len(remaining) // (max_items - top_count))
            for i in range(0, len(remaining), step):
                if len(sampled) >= max_items:
                    break
                sampled.append(remaining[i])
        return sampled[:max_items]


def extract_work_types(
    descriptions: list[str],
    llm: LLMClientProtocol | None = None,
    use_llm: bool = False,
) -> list[str]:
    if not descriptions:
        return []

    all_text = " ".join(descriptions).lower()
    scores = []
    for category, keywords in WORK_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in all_text)
        if score > 0:
            scores.append((category, score))

    scores.sort(key=lambda x: -x[1])
    top_keyword = [c for c, _ in scores[:6]]

    if use_llm and llm:
        sample = "\n".join(descriptions[:30])
        if len(sample) > 4000:
            sample = sample[:4000]
        prompt = (
            "Analyze these work descriptions and determine the top work types.\n\n"
            f"Pick from: {', '.join(WORK_TYPE_CATEGORIES)}\n\n"
            "Return ONLY a comma-separated list of the 3-6 most relevant categories, nothing else.\n\n"
            f"Descriptions:\n{sample}"
        )
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a work analyst. Output only comma-separated category names.",
            max_tokens=200,
            temperature=0.1,
            cache_key=hashlib.md5(sample.encode()).hexdigest(),
        )
        if result:
            llm_items = [x.strip() for x in result.split(",") if x.strip()]
            merged = []
            seen = set()
            for item in llm_items + top_keyword:
                if item not in seen:
                    merged.append(item)
                    seen.add(item)
            return merged[:6]

    return top_keyword[:6]
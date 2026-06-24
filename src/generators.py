"""
Generators — resume content generation (achievements, profession, skills, summary, roles).
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from typing import Any

from .constants import LLM_MAX_RETRIES, LLM_PROMPT_MAX_CHARS, LLM_RETRY_BACKOFF_BASE
from .llm import BaseLLMClient, LLMClientProtocol

logger = logging.getLogger("TACC Resume builder")


class AchievementGenerator:
    """Generates resume responsibilities and achievements from descriptions."""

    def __init__(self, llm: LLMClientProtocol | None = None) -> None:
        self._llm = llm

    def generate(
        self,
        descriptions: list[str],
        technologies: list[str],
        work_types: list[str],
        use_llm: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Generate (responsibilities, achievements) tuples."""
        if not descriptions:
            return [], []

        if not use_llm or not self._llm:
            return self._generate_heuristic(descriptions, technologies, work_types)

        return self._generate_llm(descriptions, technologies, work_types)

    def _generate_heuristic(
        self,
        descriptions: list[str],
        technologies: list[str],
        work_types: list[str],
    ) -> tuple[list[str], list[str]]:
        """Generate basic responsibilities and achievements from heuristics."""
        # Deduplicate descriptions
        unique_descs = list(dict.fromkeys(descriptions))

        # Filter meaningful descriptions (not just support/admin)
        meaningful = [
            d
            for d in unique_descs
            if len(d) > 15
            and not any(
                kw in d.lower() for kw in ["meeting", "standup", "daily", "email", "phone call"]
            )
        ]

        if not meaningful:
            return ["Provided technical support and maintenance."], []

        # Responsibilities from regular activities
        responsibilities: list[str] = []
        achievements: list[str] = []

        # Categorize based on content
        bug_fixes = [d for d in meaningful if re.search(r"(?i)\b(fix|bug|error|issue|broken)\b", d)]
        features = [
            d
            for d in meaningful
            if re.search(r"(?i)\b(implement|feature|add|create|build|develop)\b", d)
        ]
        refactors = [
            d
            for d in meaningful
            if re.search(r"(?i)\b(refactor|rewrite|clean|modernize|eliminate)\b", d)
        ]
        support_items = [
            d
            for d in meaningful
            if re.search(r"(?i)\b(support|investigate|research|troubleshoot)\b", d)
        ]

        if features:
            responsibilities.append(
                f"Developed and implemented new features including {features[0][:80]}."
            )
            achievements.append(
                f"Delivered {len(features)} feature implementations, enhancing system capabilities."
            )
        if bug_fixes:
            responsibilities.append(
                "Performed bug fixes and issue resolution across the application."
            )
            achievements.append(
                f"Resolved {len(bug_fixes)} software defects and production issues."
            )
        if refactors:
            responsibilities.append(
                "Conducted code refactoring and system modernization initiatives."
            )
            achievements.append("Refactored and optimized legacy code, improving maintainability.")
        if support_items:
            responsibilities.append(
                "Provided technical support and investigation for production systems."
            )

        if not responsibilities and not achievements:
            responsibilities.append(
                f"Developed and maintained software solutions using {', '.join(technologies[:5])}."
            )
            achievements.append("Contributed to the successful delivery of project milestones.")

        return responsibilities[:5], achievements[:5]

    def _generate_llm(
        self,
        descriptions: list[str],
        technologies: list[str],
        work_types: list[str],
    ) -> tuple[list[str], list[str]]:
        """Generate responsibilities and achievements using LLM."""
        sample = "\n".join(descriptions[:60])
        if len(sample) > 6000:
            sample = sample[:6000]

        prompt = f"""Analyze these work descriptions and generate TWO separate lists:

1. RESPONSIBILITIES (4-6 items): Daily duties, regular activities, technical ownership
2. ACHIEVEMENTS (3-5 items): Measurable impact, delivered features, improvements, optimizations

Technologies used: {", ".join(technologies[:10])}
Work types: {", ".join(work_types[:6])}

Rules:
- Start each bullet with a strong action verb
- Professional CV style
- Maximum 25 words per bullet
- No first-person pronouns
- Be specific, not generic
- Use present tense for current/recent work

Format your response EXACTLY like this:
RESPONSIBILITIES:
• [responsibility 1]
• [responsibility 2]

ACHIEVEMENTS:
• [achievement 1]
• [achievement 2]

Descriptions:
{sample}"""

        result = self._llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a professional resume writer. Generate responsibilities and achievements from work descriptions.",
            max_tokens=1000,
            temperature=0.3,
            cache_key=hashlib.md5((sample + str(technologies[:5])).encode()).hexdigest(),
        )

        if not result:
            return self._generate_heuristic(descriptions, technologies, work_types)

        responsibilities: list[str] = []
        achievements: list[str] = []
        current_section: str | None = None

        for line in result.splitlines():
            line = line.strip()
            if not line:
                continue
            upper = line.upper()
            if "RESPONSIBILITIES" in upper and ":" in line:
                current_section = "responsibilities"
                continue
            elif "ACHIEVEMENTS" in upper and ":" in line:
                current_section = "achievements"
                continue

            cleaned = re.sub(r"^[•\-\*\d\.\)]+\s*", "", line).strip()
            if len(cleaned) > 10:
                if current_section == "responsibilities":
                    responsibilities.append(cleaned)
                elif current_section == "achievements":
                    achievements.append(cleaned)

        if not responsibilities and not achievements:
            return self._generate_heuristic(descriptions, technologies, work_types)

        return responsibilities[:6], achievements[:5]


class ProfessionDetector:
    """Detects profession, seniority, and specialization."""

    # Seniority keywords
    SENIORITY_PATTERNS: list[tuple[str, int]] = [
        (r"(?i)\b(lead|principal|staff|chief|architect)\b", 3),
        (r"(?i)\b(senior|sr\.?)\b", 2),
        (r"(?i)\b(mid[\s-]level|middle)\b", 1),
        (r"(?i)\b(junior|jr\.?|entry)\b", 0),
    ]

    # Heuristic profession detection
    HEURISTIC_PROFESSIONS: list[tuple[list[str], str]] = [
        (
            [
                "react",
                "angular",
                "vue",
                "svelte",
                "frontend",
                "front-end",
                "ui",
                "blazor",
            ],
            "Senior Full Stack Developer",
        ),
        (
            [".net", "asp.net", "c#", "entity framework", "linq", "wcf"],
            "Senior .NET Developer",
        ),
        (
            [
                "selenium",
                "playwright",
                "cypress",
                "testcafe",
                "appium",
                "test automation",
            ],
            "QA Automation Engineer",
        ),
        (
            [
                "docker",
                "kubernetes",
                "k8s",
                "terraform",
                "helm",
                "ci/cd",
                "jenkins",
                "argocd",
            ],
            "DevOps Engineer",
        ),
        (
            [
                "etl",
                "airflow",
                "spark",
                "databricks",
                "dbt",
                "snowflake",
                "data pipeline",
            ],
            "Data Engineer",
        ),
        (
            ["python", "numpy", "pandas", "data analysis", "data visualization"],
            "Data Analyst",
        ),
        (["java", "spring", "spring boot", "kotlin", "jvm"], "Senior Java Developer"),
        (
            ["node.js", "express", "nest.js", "typescript", "javascript"],
            "Senior Full Stack Developer",
        ),
        (["go", "golang", "rust"], "Backend Developer"),
        (["react", "react native", "angular", "vue"], "Senior Frontend Developer"),
        (
            ["machine learning", "deep learning", "ai", "tensorflow", "pytorch", "nlp"],
            "Machine Learning Engineer",
        ),
        (
            ["business analysis", "requirements", "stakeholder", "brd", "frd"],
            "Business Analyst",
        ),
        (
            ["product owner", "backlog", "scrum", "sprint", "product management"],
            "Product Owner",
        ),
        (
            ["project manager", "pmp", "agile", "waterfall", "project planning"],
            "Project Manager",
        ),
        (
            ["solution architect", "architecture", "system design", "microservices"],
            "Solution Architect",
        ),
        (
            ["technical lead", "tech lead", "team lead", "engineering manager"],
            "Technical Lead",
        ),
        (
            ["devops", "aws", "azure", "gcp", "cloud", "infrastructure"],
            "DevOps Engineer",
        ),
        (["support", "helpdesk", "troubleshooting", "l2", "l3"], "Support Engineer"),
        (
            ["system admin", "sysadmin", "linux", "windows server", "active directory"],
            "System Administrator",
        ),
    ]

    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self._llm = llm

    def detect(
        self,
        technologies: list[str],
        descriptions: list[str],
        work_types: list[str],
        use_llm: bool = False,
    ) -> str:
        """Detect the most appropriate profession title."""
        # First try LLM
        if use_llm and self._llm:
            result = self._detect_llm(technologies, descriptions, work_types)
            if result:
                return result

        # Fallback to heuristics
        return self._detect_heuristic(technologies, descriptions)

    def _detect_llm(
        self,
        technologies: list[str],
        descriptions: list[str],
        work_types: list[str],
    ) -> str | None:
        """Use LLM to detect profession."""
        sample = "\n".join(descriptions[:20])
        if len(sample) > 3000:
            sample = sample[:3000]

        prompt = f"""Based on the following information, determine the most accurate profession title.

Technologies: {", ".join(technologies[:15])}
Work Types: {", ".join(work_types[:8])}

Project Descriptions (sample):
{sample}

Choose from these categories:
- Senior Full Stack Developer
- Senior .NET Developer
- Senior Java Developer
- Senior Frontend Developer
- Backend Developer
- QA Automation Engineer
- QA Engineer
- DevOps Engineer
- Data Engineer
- Data Analyst
- Business Analyst
- Project Manager
- Product Owner
- Solution Architect
- Technical Lead
- Support Engineer
- System Administrator
- Machine Learning Engineer
- Software Developer

Return ONLY the profession title, nothing else."""

        result = self._llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a profession classification expert. Return only the profession title.",
            max_tokens=50,
            temperature=0.1,
            cache_key=hashlib.md5((sample + str(technologies[:10])).encode()).hexdigest(),
        )

        if result and len(result) < 60:
            return result.strip()
        return None

    def _detect_heuristic(
        self,
        technologies: list[str],
        descriptions: list[str],
    ) -> str:
        """Detect profession using keyword heuristics."""
        all_text = " ".join(technologies).lower() + " " + " ".join(descriptions).lower()

        for keywords, profession in self.HEURISTIC_PROFESSIONS:
            if any(kw in all_text for kw in keywords):
                return profession

        # Detect if it's a full stack developer by checking both frontend and backend
        backend_keywords = {
            ".net",
            "c#",
            "java",
            "python",
            "node.js",
            "go",
            "golang",
            "rust",
            "php",
        }
        frontend_keywords = {
            "react",
            "angular",
            "vue",
            "javascript",
            "typescript",
            "html",
            "css",
        }
        has_backend = any(kw in all_text for kw in backend_keywords)
        has_frontend = any(kw in all_text for kw in frontend_keywords)

        if has_backend and has_frontend:
            return "Senior Full Stack Developer"
        if has_backend:
            return "Backend Developer"
        if has_frontend:
            return "Frontend Developer"

        return "Software Developer"


class SkillCategorizer:
    """Categorizes skills into a dynamic matrix."""

    DEFAULT_CATEGORIES: dict[str, set[str]] = {
        "Backend": {
            ".net",
            "c#",
            "asp.net",
            "asp.net core",
            "web api",
            "entity framework",
            "linq",
            "wcf",
            "grpc",
            "java",
            "spring",
            "spring boot",
            "kotlin",
            "python",
            "django",
            "flask",
            "fastapi",
            "celery",
            "node.js",
            "express",
            "nest.js",
            "go",
            "golang",
            "rust",
            "scala",
            "ruby",
            "php",
            "laravel",
            "elixir",
            "graphql",
            "rest",
            "soap",
            "signalr",
            "microservices",
        },
        "Frontend": {
            "javascript",
            "typescript",
            "react",
            "angular",
            "vue",
            "svelte",
            "html",
            "css",
            "blazor",
            "next.js",
            "nuxt",
            "webpack",
            "vite",
            "react native",
            "flutter",
            "xamarin",
            "maui",
            "wpf",
            "winforms",
            "windows forms",
        },
        "Cloud": {
            "azure",
            "aws",
            "gcp",
            "google cloud",
            "amazon web services",
            "cloudformation",
            "lambda",
            "ec2",
            "s3",
            "azure devops",
            "azure functions",
            "azure service bus",
            "azure sql",
            "aks",
            "eks",
            "gke",
        },
        "DevOps": {
            "docker",
            "kubernetes",
            "k8s",
            "terraform",
            "helm",
            "ansible",
            "jenkins",
            "github actions",
            "gitlab ci",
            "circleci",
            "teamcity",
            "ci/cd",
            "argocd",
            "packer",
            "vagrant",
            "prometheus",
            "grafana",
            "elk",
            "splunk",
            "datadog",
            "new relic",
        },
        "Data Engineering": {
            "etl",
            "airflow",
            "spark",
            "databricks",
            "dbt",
            "snowflake",
            "kafka",
            "flink",
            "hadoop",
            "hive",
            "presto",
            "trino",
            "data pipeline",
            "data warehouse",
            "data lake",
            "delta lake",
            "bigquery",
            "redshift",
            "synapse",
        },
        "Testing": {
            "selenium",
            "playwright",
            "cypress",
            "puppeteer",
            "appium",
            "testcafe",
            "xunit",
            "nunit",
            "jest",
            "mocha",
            "chai",
            "jasmine",
            "karma",
            "ms test",
            "specflow",
            "gauge",
            "postman",
            "soapui",
            "junit",
            "pytest",
            "robot framework",
        },
        "Databases": {
            "sql server",
            "postgresql",
            "postgres",
            "mysql",
            "oracle",
            "mongodb",
            "redis",
            "elasticsearch",
            "cassandra",
            "dynamodb",
            "cosmos db",
            "mariadb",
            "sqlite",
            "neo4j",
            "couchbase",
            "firebase",
            "supabase",
            "graphql",
        },
        "Architecture": {
            "microservices",
            "ddd",
            "domain driven design",
            "cqrs",
            "event sourcing",
            "event driven",
            "clean architecture",
            "onion architecture",
            "hexagonal architecture",
            "solid",
            "design patterns",
            "enterprise architecture",
            "soa",
            "serverless",
            "event storming",
            "uml",
        },
    }

    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self._llm = llm

    def categorize(
        self,
        technologies: list[str],
        use_llm: bool = False,
    ) -> dict[str, list[str]]:
        """Categorize technologies into a dynamic skill matrix."""
        categorized: dict[str, list[str]] = {}
        uncategorized: list[str] = []

        # First, try to categorize using known categories
        for tech in technologies:
            tech_lower = tech.lower().strip()
            matched = False
            for category, keywords in self.DEFAULT_CATEGORIES.items():
                if tech_lower in keywords:
                    if category not in categorized:
                        categorized[category] = []
                    if tech not in categorized[category]:
                        categorized[category].append(tech)
                    matched = True
                    break
            if not matched:
                uncategorized.append(tech)

        # Use LLM for uncategorized technologies
        if use_llm and self._llm and uncategorized:
            categorized = self._categorize_with_llm(uncategorized, categorized)

        # Sort within categories
        for cat in categorized:
            categorized[cat] = sorted(set(categorized[cat]))

        # Handle remaining uncategorized
        if uncategorized:
            for tech in uncategorized:
                added = False
                for cat in categorized:
                    if tech.lower() in {t.lower() for t in categorized[cat]}:
                        added = True
                        break
                if not added:
                    categorized.setdefault("Other", []).append(tech)

        # Filter empty categories
        return {k: v for k, v in categorized.items() if v}

    def _categorize_with_llm(
        self,
        technologies: list[str],
        existing: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        """Use LLM to categorize unknown technologies."""
        result = existing.copy()
        categories_list = list(self.DEFAULT_CATEGORIES.keys())

        # Batch in groups of 10
        for i in range(0, len(technologies), 10):
            batch = technologies[i : i + 10]
            prompt = f"""Categorize each technology into exactly one category.

Categories: {", ".join(categories_list)}

Technology list:
{chr(10).join(f"{j + 1}. {t}" for j, t in enumerate(batch))}

For each item, respond with: "Technology -> Category"
Example: Azure -> Cloud, React -> Frontend

Return one per line, nothing else."""

            llm_result = self._llm.chat(
                [{"role": "user", "content": prompt}],
                system_prompt="You are a technology categorizer. Map each technology to exactly one category.",
                max_tokens=300,
                temperature=0.1,
                cache_key=hashlib.md5(str(batch).encode()).hexdigest(),
            )

            if llm_result:
                for line in llm_result.splitlines():
                    line = line.strip()
                    if "->" in line:
                        parts = line.split("->")
                        if len(parts) == 2:
                            tech = parts[0].strip()
                            cat = parts[1].strip()
                            # Validate category name
                            valid_cats = set(categories_list)
                            # Also find close match
                            best_match = None
                            for valid in valid_cats:
                                if valid.lower() == cat.lower():
                                    best_match = valid
                                    break
                            if best_match:
                                if best_match not in result:
                                    result[best_match] = []
                                if tech not in result[best_match] and tech in technologies:
                                    result[best_match].append(tech)

        return result


def generate_professional_summary(
    profession: str,
    years_experience: float,
    technologies: list[str],
    projects: list[Any],
    llm: BaseLLMClient | None = None,
    use_llm: bool = False,
) -> str:
    """Generate an ATS-optimized professional summary."""
    # Count projects and their types
    project_count = len(projects)
    work_types_flat = [wt for p in projects for wt in p.work_types]
    type_counter = Counter(wt.lower() for wt in work_types_flat)
    top_types = [t for t, _ in type_counter.most_common(4)]

    # Top technologies by frequency
    tech_counter = Counter(t.lower() for p in projects for t in p.technologies)
    top_techs = [t for t, _ in tech_counter.most_common(12)]

    # Projects by industry (grouped by customer name patterns)
    industries = set()
    for p in projects:
        name_lower = p.customer.lower()
        if (
            "gracenote" in name_lower
            or "tv" in name_lower
            or "media" in name_lower
            or "news" in name_lower
        ):
            industries.add("Media & Entertainment")
        elif "bel air" in name_lower or "internet" in name_lower or "isp" in name_lower:
            industries.add("Telecommunications/ISP")
        elif "block" in name_lower or "fintech" in name_lower or "finance" in name_lower:
            industries.add("Fintech")
        elif "insta" in name_lower or "vin" in name_lower:
            industries.add("Automotive")

    if use_llm and llm:
        prompt = f"""Create a professional resume summary with the following parameters:

Profession: {profession}
Years of Experience: {years_experience}
Key Technologies: {", ".join(top_techs[:10])}
Industries: {", ".join(industries) if industries else "Software/Technology"}
Number of Projects: {project_count}
Primary Work Types: {", ".join(top_types)}

Requirements:
- 3-5 sentences
- ATS-optimized (keywords naturally integrated)
- Professional, confident tone
- No first-person pronouns
- No clichés ("results-driven", "team player", etc.)
- Seniority-aware
- Specific about technologies and domains
- Not generic — must sound like a real professional

Return ONLY the summary paragraph."""

        result = llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You are an expert resume writer specializing in ATS-optimized professional summaries.",
            max_tokens=400,
            temperature=0.4,
            cache_key=hashlib.md5(
                f"{profession}{years_experience}{top_techs[:8]}{industries}".encode()
            ).hexdigest(),
        )
        if result and len(result) > 80:
            return result.strip()

    # Fallback: generate a structured summary
    industries_str = (
        f"across {', '.join(industries)}" if industries else "across multiple industries"
    )
    tech_str = ", ".join(top_techs[:8])

    summary = (
        f"{profession} with approximately {years_experience} years of professional experience "
        f"delivering software solutions {industries_str}. "
        f"Demonstrated expertise in {tech_str}. "
    )

    if top_types:
        summary += f"Proven track record in {', '.join(top_types[:3])}. "

    summary += (
        "Experienced in full software development lifecycle, collaborating with "
        "distributed cross-functional teams, and driving technical excellence "
        "through modern engineering practices."
    )

    return summary


def infer_project_role(
    technologies: list[str],
    work_types: list[str],
    descriptions: list[str],
    llm: BaseLLMClient | None = None,
    use_llm: bool = False,
) -> str:
    """Infer the most appropriate role for a project."""
    all_text = " ".join(technologies).lower() + " " + " ".join(work_types).lower()

    # Heuristic role detection based on technology patterns
    role_patterns: list[tuple[list[str], str]] = [
        (
            [
                "react",
                "angular",
                "vue",
                "svelte",
                "frontend",
                "ui",
                "blazor",
                "typescript",
                "javascript",
            ],
            "Senior Full Stack Developer",
        ),
        (
            [".net", "c#", "asp.net", "entity framework", "linq", "wcf"],
            "Senior .NET Developer",
        ),
        (["java", "spring", "spring boot", "kotlin"], "Senior Java Developer"),
        (["python", "django", "flask", "fastapi"], "Senior Python Developer"),
        (["node.js", "express", "nest.js"], "Senior Node.js Developer"),
        (["go", "golang"], "Senior Go Developer"),
        (
            ["selenium", "playwright", "cypress", "automation", "test"],
            "QA Automation Engineer",
        ),
        (["devops", "docker", "kubernetes", "terraform", "ci/cd"], "DevOps Engineer"),
        (["etl", "airflow", "spark", "databricks", "pipeline"], "Data Engineer"),
        (["react native", "flutter", "xamarin", "mobile"], "Mobile Developer"),
        (["architect", "microservices", "ddd", "system design"], "Solution Architect"),
        (["support", "maintenance", "troubleshoot"], "Support Engineer"),
        (
            ["admin", "administration", "linux", "windows server"],
            "System Administrator",
        ),
    ]

    for keywords, role in role_patterns:
        if any(kw in all_text for kw in keywords):
            return role

    # Default to profession-agnostic
    return "Software Developer"

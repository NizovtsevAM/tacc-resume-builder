"""
Data processor — core pipeline: TACC records → ResumeProfile.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from .config import parse_date, load_json
from .constants import DEFAULT_INPUT_PATH, JSON_INDENT
from .extractors import TechnologyExtractor, extract_work_types
from .schema import validate_tacc_data
from .generators import (
    AchievementGenerator,
    ProfessionDetector,
    SkillCategorizer,
    generate_professional_summary,
    infer_project_role,
)
from .llm import BaseLLMClient, LLMClientProtocol
from .models import ResumeProject, ResumeProfile

logger = logging.getLogger("TACC Resume builder")


class ResumeDataProcessor:
    """Core pipeline: processes TACC records into ResumeProject domain models."""

    def __init__(
        self,
        settings: Any,
        llm: LLMClientProtocol | None = None,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.tech_extractor = TechnologyExtractor(llm, settings.technology_blacklist)
        self.achievement_gen = AchievementGenerator(llm)
        self.profession_detector = ProfessionDetector(llm)
        self.skill_categorizer = SkillCategorizer(llm)

    def process(self) -> ResumeProfile:
        """Full pipeline: load → categorize → group → enhance → build profile."""
        data = load_json(self.settings.input_path)
        logger.info("Loaded %d records from %s", len(data), self.settings.input_path)
        try:
            validate_tacc_data(data)
        except ValueError as e:
            logger.error("Input data validation failed: %s", e)
            raise

        # Step 1: Categorize work vs non-work
        categorized = self._categorize_records(data)
        logger.info(
            "Work records: %d | Non-billable: %d",
            len(categorized["work"]),
            len(categorized["non_billable"]),
        )

        # Step 2: Group by customer
        work_groups = self._group_by_customer(categorized["work"])
        logger.info("Project groups after filtering: %d", len(work_groups))

        if not work_groups:
            logger.error("No valid project groups found. Check your data and filters.")
            return ResumeProfile(
                first_name=self.settings.first_name,
                last_name=self.settings.last_name,
            )

        # Step 3: Enhance each project
        projects = self._enhance_projects(work_groups)

        # Step 4: Resolve profession — explicit TITLE from .env takes priority over auto-detection
        all_techs = list(dict.fromkeys(t for p in projects for t in p.technologies))
        all_descs = [d for p in projects for d in p.descriptions]
        all_work_types = list(dict.fromkeys(wt for p in projects for wt in p.work_types))
        title = (self.settings.title or "").strip()
        if title and title.lower() != "auto":
            profession = title
            logger.info("Using profession from TITLE setting: %s", profession)
        else:
            profession = self.profession_detector.detect(
                all_techs,
                all_descs,
                all_work_types,
                use_llm=self.settings.use_llm,
            )
            logger.info("Detected profession: %s", profession)

        # Step 5: Calculate total experience
        # Use the latest date from ALL input records (not just billable projects)
        # to account for ongoing employment, training, etc.
        years = 0.0
        if projects:
            min_start = min(p.start_date for p in projects)
            # Fall back to latest raw data date if available, otherwise last project end
            raw_data_max = max(
                (parse_date(r.get("Date", "")) for r in data if r.get("Date")),
                default=max(p.end_date for p in projects),
            )
            max_end = max(p.end_date for p in projects)
            if raw_data_max and raw_data_max > max_end:
                max_end = raw_data_max
            years = round((max_end - min_start).days / 365.25, 1)

        # Step 6: Build skill matrix
        skill_matrix = self.skill_categorizer.categorize(
            all_techs,
            use_llm=self.settings.use_llm,
        )

        # Step 7: Generate summary
        summary = generate_professional_summary(
            profession=profession,
            years_experience=years,
            technologies=all_techs,
            projects=projects,
            llm=self.llm,
            use_llm=self.settings.use_llm,
        )

        # Step 8: Assemble profile
        return ResumeProfile(
            first_name=self.settings.first_name,
            last_name=self.settings.last_name,
            profession=profession,
            summary=summary,
            email=self.settings.email,
            phone=self.settings.phone,
            location=self.settings.location,
            linkedin=self.settings.linkedin,
            education=self.settings.education,
            years_experience=years,
            skills=skill_matrix,
            projects=projects,
        )

    def _categorize_records(self, data: list[dict]) -> dict[str, list[dict]]:
        """Separate work (billable) from non-billable records."""
        work: list[dict] = []
        non_billable: list[dict] = []

        for r in data:
            customer = r.get("CustomerName", "Unknown")
            if self._is_excluded(customer):
                non_billable.append(r)
                continue
            if r.get("ContractId") is not None:
                work.append(r)
            else:
                non_billable.append(r)

        return {"work": work, "non_billable": non_billable}

    def _is_excluded(self, customer_name: str) -> bool:
        """Check if a customer is in the exclusion list."""
        if not customer_name or not self.settings.excluded_customers:
            return False
        lower = customer_name.lower().strip()
        for excluded in self.settings.excluded_customers:
            if (
                lower == excluded
                or lower.startswith(excluded + " ")
                or lower.startswith(excluded + "(")
            ):
                return True
        return False

    def _group_by_customer(self, records: list[dict]) -> list[dict]:
        """Group work records by full CustomerName. Each distinct customer = separate project."""
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in records:
            group_name = r["CustomerName"]
            groups[group_name].append(r)

        result: list[dict] = []
        for group_name, recs in groups.items():
            if len(recs) < self.settings.min_project_duration_days:
                logger.debug(
                    "Skipping project '%s' (%d days < %d)",
                    group_name,
                    len(recs),
                    self.settings.min_project_duration_days,
                )
                continue

            # Sort by date
            recs.sort(key=lambda x: parse_date(x.get("Date", "")) or datetime.min)
            dates = [parse_date(r.get("Date", "")) for r in recs if r.get("Date")]
            dates = [d for d in dates if d]
            if not dates:
                continue

            descriptions = [r.get("Description", "") for r in recs if r.get("Description")]

            result.append(
                {
                    "customer": group_name,
                    "start_date": min(dates),
                    "end_date": max(dates),
                    "days": len(recs),
                    "descriptions": descriptions,
                    "records_count": len(recs),
                }
            )

        result.sort(key=lambda x: x["end_date"], reverse=True)
        return result

    def _enhance_projects(self, work_groups: list[dict]) -> list[ResumeProject]:
        """Enhance raw project groups with technologies, roles, etc."""
        projects: list[ResumeProject] = []

        for group in work_groups:
            descriptions = group["descriptions"]

            # Extract technologies
            technologies = self.tech_extractor.extract(
                descriptions,
                use_llm=self.settings.use_llm,
            )

            # Extract work types
            work_types = extract_work_types(
                descriptions,
                llm=self.llm,
                use_llm=self.settings.use_llm,
            )

            # Generate responsibilities & achievements
            responsibilities, achievements = self.achievement_gen.generate(
                descriptions,
                technologies,
                work_types,
                use_llm=self.settings.use_llm,
            )

            # Infer role
            role = infer_project_role(
                technologies,
                work_types,
                descriptions,
                llm=self.llm,
                use_llm=self.settings.use_llm,
            )

            project = ResumeProject(
                customer=group["customer"],
                role=role,
                start_date=group["start_date"],
                end_date=group["end_date"],
                days=group["days"],
                descriptions=descriptions,
                responsibilities=responsibilities,
                achievements=achievements,
                technologies=technologies,
                work_types=work_types,
            )
            projects.append(project)

        return projects

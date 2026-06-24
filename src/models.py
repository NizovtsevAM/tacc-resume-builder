"""
Domain models — dataclasses for resume data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ResumeProject:
    """A single project / engagement in the resume."""

    customer: str
    role: str
    start_date: datetime
    end_date: datetime
    days: int
    descriptions: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    work_types: list[str] = field(default_factory=list)

    def duration_years(self) -> float:
        return round((self.end_date - self.start_date).days / 365.25, 1)


@dataclass
class ResumeProfile:
    """Top-level resume data."""

    first_name: str = ""
    last_name: str = ""
    profession: str = "Software Professional"
    summary: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    education: str = ""
    years_experience: float = 0.0
    skills: dict[str, list[str]] = field(default_factory=dict)
    projects: list[ResumeProject] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profession": self.profession,
            "summary": self.summary,
            "years_experience": self.years_experience,
            "skills": dict(self.skills),
            "projects": [
                {
                    "customer": p.customer,
                    "role": p.role,
                    "start_date": p.start_date.strftime("%b %Y"),
                    "end_date": p.end_date.strftime("%b %Y"),
                    "duration_days": p.days,
                    "work_types": p.work_types,
                    "technologies": sorted(set(p.technologies)),
                    "responsibilities": p.responsibilities,
                    "achievements": p.achievements,
                }
                for p in self.projects
            ],
        }

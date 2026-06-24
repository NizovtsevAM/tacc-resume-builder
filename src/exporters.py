"""
Exporters — DOCX, HTML, JSON resume generation.
"""

from __future__ import annotations

import html as html_mod
import json
import logging
import os
from typing import Any

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .config import Settings
from .models import ResumeProfile

logger = logging.getLogger("TACC Resume builder")


def export_resume_json(profile: ResumeProfile, output_path: str) -> None:
    """Export resume data to JSON."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
    logger.info("Resume JSON exported to: %s", output_path)


def save_document(doc: Document, output_path: str) -> None:
    """Save the DOCX document."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    logger.info("Resume DOCX saved to: %s", output_path)


def export_resume_html(
    profile: ResumeProfile, settings: Settings, output_path: str
) -> None:
    """Export resume data to HTML using a template."""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    template_name = settings.resume_template if settings.resume_template else "modern"
    template_path = os.path.join(templates_dir, f"{template_name}.html")

    if not os.path.exists(template_path):
        logger.warning(
            "Template %s not found at %s, falling back to modern",
            template_name,
            template_path,
        )
        template_path = os.path.join(templates_dir, "modern.html")
        if not os.path.exists(template_path):
            logger.error("No templates found. Skipping HTML export.")
            return

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Build contact string with hyperlinks
    contact_parts: list[str] = []
    if profile.email:
        contact_parts.append(
            f'<a href="mailto:{html_mod.escape(profile.email)}" style="color: #8892b0; text-decoration: none;">{html_mod.escape(profile.email)}</a>'
        )
    if profile.phone:
        contact_parts.append(html_mod.escape(profile.phone))
    if profile.location:
        contact_parts.append(html_mod.escape(profile.location))
    if profile.linkedin:
        linkedin_url = profile.linkedin
        if not linkedin_url.startswith("http"):
            linkedin_url = "https://" + linkedin_url
        contact_parts.append(
            f'<a href="{html_mod.escape(linkedin_url)}" target="_blank" rel="noopener" style="color: #8892b0; text-decoration: none;">{html_mod.escape(profile.linkedin)}</a>'
        )
    contacts = " | ".join(contact_parts)

    # Build skills section HTML
    skills_html = ""
    if profile.skills:
        skills_html = '<div class="section">\n  <h2>Technical Skills</h2>\n'
        for category in [
            "Backend",
            "Frontend",
            "Cloud",
            "DevOps",
            "Databases",
            "Testing",
            "Data Engineering",
            "Architecture",
        ]:
            if category in profile.skills:
                skills_html += (
                    f'  <div class="skill-category">\n'
                    f'    <div class="cat-name">{html_mod.escape(category)}</div>\n'
                    f'    <div class="skills-grid">\n'
                )
                for skill in sorted(profile.skills[category]):
                    skills_html += f'      <span class="skill-tag">{html_mod.escape(skill)}</span>\n'
                skills_html += "    </div>\n  </div>\n"
        for category in sorted(profile.skills.keys()):
            if category not in [
                "Backend",
                "Frontend",
                "Cloud",
                "DevOps",
                "Databases",
                "Testing",
                "Data Engineering",
                "Architecture",
            ]:
                skills_html += (
                    f'  <div class="skill-category">\n'
                    f'    <div class="cat-name">{html_mod.escape(category)}</div>\n'
                    f'    <div class="skills-grid">\n'
                )
                for skill in sorted(profile.skills[category]):
                    skills_html += f'      <span class="skill-tag">{html_mod.escape(skill)}</span>\n'
                skills_html += "    </div>\n  </div>\n"
        skills_html += "</div>\n"

    # Build projects section HTML
    projects_html = ""
    for project in profile.projects:
        projects_html += '<div class="project">\n'
        projects_html += (
            f'  <div class="company">{html_mod.escape(project.customer)}</div>\n'
        )
        if project.role:
            projects_html += (
                f'  <div class="role">{html_mod.escape(project.role)}</div>\n'
            )
        projects_html += (
            f'  <div class="dates">'
            f"{project.start_date.strftime('%b %Y')} — {project.end_date.strftime('%b %Y')}"
            f"  |  {project.days} days"
            f"</div>\n"
        )
        projects_html += '  <div class="details">\n'
        if project.responsibilities:
            projects_html += "    <h3>Responsibilities</h3>\n    <ul>\n"
            for resp in project.responsibilities:
                projects_html += f"      <li>{html_mod.escape(resp)}</li>\n"
            projects_html += "    </ul>\n"
        if project.achievements:
            projects_html += "    <h3>Achievements</h3>\n    <ul>\n"
            for ach in project.achievements:
                projects_html += f"      <li>{html_mod.escape(ach)}</li>\n"
            projects_html += "    </ul>\n"
        projects_html += "  </div>\n"
        if project.technologies:
            projects_html += (
                f'  <div class="techs">'
                f"<strong>Technologies:</strong> {html_mod.escape(', '.join(sorted(set(project.technologies))))}"
                f"</div>\n"
            )
        projects_html += "</div>\n"

    # Build education section
    education_html = ""
    if profile.education:
        education_html = (
            '<div class="section">\n'
            f"  <h2>Education</h2>\n"
            f"  <p>{html_mod.escape(profile.education)}</p>\n"
            "</div>\n"
        )

    # Replace placeholders
    html_content = template
    html_content = html_content.replace(
        "{{ NAME }}", html_mod.escape(f"{profile.first_name} {profile.last_name}")
    )
    html_content = html_content.replace(
        "{{ PROFESSION }}", html_mod.escape(profile.profession)
    )
    html_content = html_content.replace("{{ CONTACTS }}", contacts)
    html_content = html_content.replace(
        "{{ SUMMARY }}", html_mod.escape(profile.summary)
    )
    html_content = html_content.replace("{{ SKILLS_SECTION }}", skills_html)
    html_content = html_content.replace("{{ PROJECTS }}", projects_html)
    html_content = html_content.replace("{{ EDUCATION_SECTION }}", education_html)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info("Resume HTML exported to: %s", output_path)


class ResumeDocumentGenerator:
    """Generates ATS-optimized professional DOCX resumes."""

    FONTS = ["Calibri", "Arial", "Helvetica", "Segoe UI", "Verdana"]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._font_name = self.FONTS[0]

    def generate(self, profile: ResumeProfile) -> Document:
        """Create a professional DOCX document from the resume profile."""
        doc = Document()

        # Page setup
        section = doc.sections[0]
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

        # Default style
        style = doc.styles["Normal"]
        style.font.name = self._font_name
        style.font.size = Pt(10.5)
        style.paragraph_format.space_after = Pt(2)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.line_spacing = 1.08

        # Header
        self._add_header(doc, profile)

        # Professional Summary
        self._add_section_heading(doc, "PROFESSIONAL SUMMARY")
        p = doc.add_paragraph(profile.summary)
        p.style.font.name = self._font_name
        p.paragraph_format.space_after = Pt(6)

        # Core Competencies
        if profile.skills:
            self._add_section_heading(doc, "CORE COMPETENCIES")
            all_skills: list[str] = []
            for cat in [
                "Backend",
                "Frontend",
                "Cloud",
                "DevOps",
                "Databases",
                "Testing",
                "Data Engineering",
                "Architecture",
            ]:
                if cat in profile.skills:
                    all_skills.extend(profile.skills[cat])
            for cat, skills in profile.skills.items():
                if cat not in [
                    "Backend",
                    "Frontend",
                    "Cloud",
                    "DevOps",
                    "Databases",
                    "Testing",
                    "Data Engineering",
                    "Architecture",
                    "Other",
                ]:
                    all_skills.extend(skills)

            seen = set()
            unique_skills: list[str] = []
            for s in all_skills:
                if s.lower() not in seen:
                    unique_skills.append(s)
                    seen.add(s.lower())

            p = doc.add_paragraph(", ".join(unique_skills[:20]))
            p.style.font.name = self._font_name
            p.paragraph_format.space_after = Pt(6)

        # Technical Skills
        if profile.skills:
            self._add_section_heading(doc, "TECHNICAL SKILLS")
            for category in [
                "Backend",
                "Frontend",
                "Cloud",
                "DevOps",
                "Databases",
                "Testing",
                "Data Engineering",
                "Architecture",
            ]:
                if category in profile.skills:
                    self._add_skill_line(doc, category, profile.skills[category])
            for category in sorted(profile.skills.keys()):
                if category not in [
                    "Backend",
                    "Frontend",
                    "Cloud",
                    "DevOps",
                    "Databases",
                    "Testing",
                    "Data Engineering",
                    "Architecture",
                ]:
                    self._add_skill_line(doc, category, profile.skills[category])

        # Professional Experience
        self._add_section_heading(doc, "PROFESSIONAL EXPERIENCE")
        for project in profile.projects:
            self._add_project_entry(doc, project)

        # Education (optional)
        if profile.education:
            self._add_section_heading(doc, "EDUCATION")
            p = doc.add_paragraph(profile.education)
            p.style.font.name = self._font_name

        return doc

    @staticmethod
    def _add_hyperlink(paragraph, text: str, url: str, font_size: Any) -> None:
        """Add a hyperlink to a paragraph."""
        from docx.oxml.ns import qn

        part = paragraph.part
        r_id = part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )
        hyperlink = paragraph._p.makeelement(qn("w:hyperlink"), {qn("r:id"): r_id})
        new_run = hyperlink.makeelement(qn("w:r"), {})
        rPr = new_run.makeelement(qn("w:rPr"), {})
        c = rPr.makeelement(qn("w:color"), {qn("w:val"): "34495E"})
        rPr.append(c)
        u = rPr.makeelement(qn("w:u"), {qn("w:val"): "single"})
        rPr.append(u)
        sz = rPr.makeelement(qn("w:sz"), {qn("w:val"): str(int(font_size.pt * 2))})
        rPr.append(sz)
        new_run.append(rPr)
        t = new_run.makeelement(qn("w:t"), {})
        t.text = text
        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)

    def _add_header(self, doc: Document, profile: ResumeProfile) -> None:
        """Add name, title, and contact information."""
        # Name
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(f"{profile.first_name} {profile.last_name}")
        run.bold = True
        run.font.size = Pt(20)
        run.font.name = self._font_name
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

        # Title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(profile.profession)
        run.font.size = Pt(12)
        run.font.name = self._font_name
        run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)
        run.italic = True

        # Contact line
        contact_parts: list[tuple[str, str | None]] = []
        if profile.email:
            contact_parts.append((profile.email, f"mailto:{profile.email}"))
        if profile.phone:
            contact_parts.append((profile.phone, None))
        if profile.location:
            contact_parts.append((profile.location, None))
        if profile.linkedin:
            linkedin_url = profile.linkedin
            if not linkedin_url.startswith("http"):
                linkedin_url = "https://" + linkedin_url
            contact_parts.append((profile.linkedin, linkedin_url))

        if contact_parts:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            for i, (text, url) in enumerate(contact_parts):
                if i > 0:
                    run = p.add_run(" | ")
                    run.font.size = Pt(9.5)
                    run.font.name = self._font_name
                    run.font.color.rgb = RGBColor(0x34, 0x49, 0x5E)
                if url:
                    self._add_hyperlink(p, text, url, Pt(9.5))
                else:
                    run = p.add_run(text)
                    run.font.size = Pt(9.5)
                    run.font.name = self._font_name
                    run.font.color.rgb = RGBColor(0x34, 0x49, 0x5E)

        # Horizontal rule
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run("─" * 85)
        run.font.size = Pt(6)
        run.font.color.rgb = RGBColor(0x95, 0xA5, 0xA6)

    def _add_section_heading(self, doc: Document, text: str) -> None:
        """Add a section heading consistent with ATS requirements."""
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True

        run = p.add_run(text.upper())
        run.bold = True
        run.font.size = Pt(12)
        run.font.name = self._font_name
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

        # Underline
        run2 = p.add_run("\n" + "─" * 85)
        run2.font.size = Pt(5)
        run2.font.color.rgb = RGBColor(0x95, 0xA5, 0xA6)

    def _add_skill_line(self, doc: Document, category: str, skills: list[str]) -> None:
        """Add a skill category line."""
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.keep_with_next = True

        run = p.add_run(f"{category}: ")
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = self._font_name

        run2 = p.add_run(", ".join(sorted(skills)))
        run2.font.size = Pt(10)
        run2.font.name = self._font_name

    def _add_project_entry(self, doc: Document, project: Any) -> None:
        """Add a professional experience entry for one project."""
        # Company / Customer name
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True

        run = p.add_run(project.customer)
        run.bold = True
        run.font.size = Pt(11.5)
        run.font.name = self._font_name

        # Role
        if project.role:
            p2 = doc.add_paragraph()
            p2.paragraph_format.space_before = Pt(0)
            p2.paragraph_format.space_after = Pt(0)
            p2.paragraph_format.keep_with_next = True

            run = p2.add_run(project.role)
            run.font.size = Pt(10.5)
            run.font.name = self._font_name
            run.italic = True
            run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x50)

        # Dates
        p3 = doc.add_paragraph()
        p3.paragraph_format.space_before = Pt(0)
        p3.paragraph_format.space_after = Pt(4)
        p3.paragraph_format.keep_with_next = True

        run = p3.add_run(
            f"{project.start_date.strftime('%b %Y')} — {project.end_date.strftime('%b %Y')}"
            f"  |  {project.days} days"
        )
        run.font.size = Pt(9)
        run.font.name = self._font_name
        run.font.color.rgb = RGBColor(0x7F, 0x8C, 0x8D)

        # Responsibilities
        if project.responsibilities:
            p4 = doc.add_paragraph()
            p4.paragraph_format.space_before = Pt(2)
            p4.paragraph_format.space_after = Pt(2)
            run = p4.add_run("Responsibilities:")
            run.bold = True
            run.font.size = Pt(10)
            run.font.name = self._font_name

            for resp in project.responsibilities:
                bullet = doc.add_paragraph(style="List Bullet")
                bullet.clear()
                run = bullet.add_run(resp)
                run.font.size = Pt(10)
                run.font.name = self._font_name
                bullet.paragraph_format.space_after = Pt(1)
                bullet.paragraph_format.space_before = Pt(0)

        # Achievements
        if project.achievements:
            p5 = doc.add_paragraph()
            p5.paragraph_format.space_before = Pt(4)
            p5.paragraph_format.space_after = Pt(2)
            run = p5.add_run("Achievements:")
            run.bold = True
            run.font.size = Pt(10)
            run.font.name = self._font_name

            for ach in project.achievements:
                bullet = doc.add_paragraph(style="List Bullet")
                bullet.clear()
                run = bullet.add_run(ach)
                run.font.size = Pt(10)
                run.font.name = self._font_name
                bullet.paragraph_format.space_after = Pt(1)
                bullet.paragraph_format.space_before = Pt(0)

        # Technologies
        if project.technologies:
            p6 = doc.add_paragraph()
            p6.paragraph_format.space_before = Pt(4)
            p6.paragraph_format.space_after = Pt(2)
            run = p6.add_run("Technologies: ")
            run.bold = True
            run.font.size = Pt(9.5)
            run.font.name = self._font_name

            run2 = p6.add_run(", ".join(sorted(set(project.technologies))))
            run2.font.size = Pt(9.5)
            run2.font.name = self._font_name
            run2.font.color.rgb = RGBColor(0x34, 0x49, 0x5E)

        # Spacer between projects
        p_spacer = doc.add_paragraph()
        p_spacer.paragraph_format.space_before = Pt(2)
        p_spacer.paragraph_format.space_after = Pt(0)
        run = p_spacer.add_run("")
        run.font.size = Pt(2)

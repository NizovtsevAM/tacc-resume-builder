"""
DOCX template themes — visual styles aligned with HTML templates.
"""

from __future__ import annotations

from dataclasses import dataclass

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import RGBColor

from .constants import DEFAULT_TEMPLATE, VALID_TEMPLATES


def _rgb(hex_color: str) -> RGBColor:
    value = hex_color.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


@dataclass(frozen=True)
class DocxTheme:
    """Visual theme for DOCX resume export."""

    name: str
    font_name: str
    contact_font_name: str
    body_size: float
    name_size: float
    title_size: float
    contact_size: float
    section_heading_size: float
    company_size: float
    role_size: float
    date_size: float
    name_color: RGBColor
    title_color: RGBColor
    contact_color: RGBColor
    link_color: str
    heading_color: RGBColor
    role_color: RGBColor
    date_color: RGBColor
    tech_color: RGBColor
    accent_color: RGBColor
    accent_hex: str
    header_align: WD_ALIGN_PARAGRAPH
    title_italic: bool
    role_italic: bool
    role_bold: bool
    show_core_competencies: bool
    header_rule: bool
    section_rule_width: int
    bullet_prefix: str | None
    project_left_border: bool
    margin_left: float
    margin_right: float
    margin_top: float
    margin_bottom: float


DOCX_THEMES: dict[str, DocxTheme] = {
    "modern": DocxTheme(
        name="modern",
        font_name="Calibri",
        contact_font_name="Calibri",
        body_size=10.5,
        name_size=20,
        title_size=12,
        contact_size=9.5,
        section_heading_size=12,
        company_size=11.5,
        role_size=10.5,
        date_size=9,
        name_color=_rgb("1A1A2E"),
        title_color=_rgb("2C3E50"),
        contact_color=_rgb("34495E"),
        link_color="34495E",
        heading_color=_rgb("1A1A2E"),
        role_color=_rgb("2C3E50"),
        date_color=_rgb("7F8C8D"),
        tech_color=_rgb("34495E"),
        accent_color=_rgb("1A1A2E"),
        accent_hex="1A1A2E",
        header_align=WD_ALIGN_PARAGRAPH.CENTER,
        title_italic=True,
        role_italic=True,
        role_bold=False,
        show_core_competencies=True,
        header_rule=True,
        section_rule_width=85,
        bullet_prefix=None,
        project_left_border=False,
        margin_left=0.75,
        margin_right=0.75,
        margin_top=0.5,
        margin_bottom=0.5,
    ),
    "classic": DocxTheme(
        name="classic",
        font_name="Georgia",
        contact_font_name="Calibri",
        body_size=10.5,
        name_size=26,
        title_size=13,
        contact_size=10,
        section_heading_size=13,
        company_size=12,
        role_size=11,
        date_size=9.5,
        name_color=_rgb("111111"),
        title_color=_rgb("444444"),
        contact_color=_rgb("555555"),
        link_color="0645AD",
        heading_color=_rgb("111111"),
        role_color=_rgb("333333"),
        date_color=_rgb("555555"),
        tech_color=_rgb("333333"),
        accent_color=_rgb("111111"),
        accent_hex="111111",
        header_align=WD_ALIGN_PARAGRAPH.CENTER,
        title_italic=True,
        role_italic=True,
        role_bold=False,
        show_core_competencies=True,
        header_rule=True,
        section_rule_width=85,
        bullet_prefix=None,
        project_left_border=False,
        margin_left=0.85,
        margin_right=0.85,
        margin_top=0.55,
        margin_bottom=0.55,
    ),
    "minimalist": DocxTheme(
        name="minimalist",
        font_name="Calibri",
        contact_font_name="Calibri",
        body_size=10.5,
        name_size=22,
        title_size=12,
        contact_size=10,
        section_heading_size=12,
        company_size=11.5,
        role_size=10.5,
        date_size=9.5,
        name_color=_rgb("000000"),
        title_color=_rgb("444444"),
        contact_color=_rgb("555555"),
        link_color="0645AD",
        heading_color=_rgb("000000"),
        role_color=_rgb("333333"),
        date_color=_rgb("555555"),
        tech_color=_rgb("333333"),
        accent_color=_rgb("000000"),
        accent_hex="000000",
        header_align=WD_ALIGN_PARAGRAPH.LEFT,
        title_italic=False,
        role_italic=True,
        role_bold=False,
        show_core_competencies=False,
        header_rule=True,
        section_rule_width=60,
        bullet_prefix=None,
        project_left_border=False,
        margin_left=0.7,
        margin_right=0.7,
        margin_top=0.45,
        margin_bottom=0.45,
    ),
    "creative": DocxTheme(
        name="creative",
        font_name="Segoe UI",
        contact_font_name="Segoe UI",
        body_size=10.5,
        name_size=28,
        title_size=14,
        contact_size=9.5,
        section_heading_size=12,
        company_size=12.5,
        role_size=10.5,
        date_size=9,
        name_color=_rgb("1A1B2E"),
        title_color=_rgb("2B2D42"),
        contact_color=_rgb("6C757D"),
        link_color="EF476F",
        heading_color=_rgb("1A1B2E"),
        role_color=_rgb("EF476F"),
        date_color=_rgb("6C757D"),
        tech_color=_rgb("4A4E69"),
        accent_color=_rgb("EF476F"),
        accent_hex="EF476F",
        header_align=WD_ALIGN_PARAGRAPH.LEFT,
        title_italic=False,
        role_italic=False,
        role_bold=True,
        show_core_competencies=False,
        header_rule=True,
        section_rule_width=40,
        bullet_prefix="▹ ",
        project_left_border=True,
        margin_left=0.75,
        margin_right=0.75,
        margin_top=0.5,
        margin_bottom=0.5,
    ),
}


def get_docx_theme(template_name: str) -> DocxTheme:
    """Return DOCX theme for template name, falling back to modern."""
    key = (template_name or DEFAULT_TEMPLATE).lower()
    if key not in VALID_TEMPLATES:
        key = DEFAULT_TEMPLATE
    return DOCX_THEMES.get(key, DOCX_THEMES[DEFAULT_TEMPLATE])

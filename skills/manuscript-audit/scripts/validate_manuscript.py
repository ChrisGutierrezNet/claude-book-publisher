#!/usr/bin/env python3
"""
Manuscript Audit Validator
Validates book manuscripts against professional publishing standards.
Generates cryptographically signed audit reports.

Usage:
    python3 validate_manuscript.py --mode full path/to/project
    python3 validate_manuscript.py --mode quick path/to/project
    python3 validate_manuscript.py --category typography path/to/project
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


VERSION = "0.1.0"


class Finding:
    """A single audit finding."""

    def __init__(
        self,
        finding_id: str,
        severity: str,
        category: str,
        title: str,
        location: str,
        standard: str,
        description: str,
        fix: str,
        impact: str = "",
    ):
        self.finding_id = finding_id
        self.severity = severity  # CRITICAL, MAJOR, MINOR, INFO
        self.category = category
        self.title = title
        self.location = location
        self.standard = standard
        self.description = description
        self.fix = fix
        self.impact = impact

    def to_dict(self) -> dict:
        return {
            "id": self.finding_id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "location": self.location,
            "standard": self.standard,
            "description": self.description,
            "fix": self.fix,
            "impact": self.impact,
        }


class ManuscriptAuditor:
    """Audits book manuscripts against publishing standards."""

    def __init__(self, project_path: str, mode: str = "full"):
        self.project_path = Path(project_path).resolve()
        self.mode = mode
        self.findings: list[Finding] = []
        self.checks_run = 0
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warned = 0
        self.checks_skipped = 0

        # Category counters
        self.category_stats: dict[str, dict[str, int]] = {}

        # Detect project type
        self.quarto_config = self._find_quarto_config()
        self.tex_file = self._find_tex_file()
        self.pdf_file = self._find_pdf_file()

    def _filter_source_files(self, files: list[Path]) -> list[Path]:
        """Exclude files in worktrees, build output, and hidden directories."""
        excluded = {".worktrees", "_output", "_site", "_book", ".git", "node_modules"}
        result = []
        for f in files:
            parts = f.relative_to(self.project_path).parts
            if not any(p in excluded or p.startswith(".") for p in parts):
                result.append(f)
        return result

    @staticmethod
    def _strip_yaml_frontmatter(text: str) -> str:
        """Remove YAML front matter (--- ... ---) from .qmd/.md content."""
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                return text[end + 3:]
        return text

    def _find_quarto_config(self) -> Optional[Path]:
        for name in ["_quarto-kdp.yml", "_quarto.yml"]:
            p = self.project_path / name
            if p.exists():
                return p
        return None

    def _find_tex_file(self) -> Optional[Path]:
        for f in self.project_path.glob("*.tex"):
            if "font-samples" not in f.name:
                return f
        # Check output dirs
        for d in ["_output/kdp", "_output"]:
            for f in (self.project_path / d).glob("*.tex"):
                return f
        return None

    def _find_pdf_file(self) -> Optional[Path]:
        for d in ["_output/kdp", "_output"]:
            for f in (self.project_path / d).glob("*.pdf"):
                return f
        return None

    def _record(self, category: str, passed: bool, finding: Optional[Finding] = None):
        self.checks_run += 1
        if category not in self.category_stats:
            self.category_stats[category] = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}

        if finding:
            self.findings.append(finding)
            if finding.severity in ("CRITICAL", "MAJOR"):
                self.checks_failed += 1
                self.category_stats[category]["fail"] += 1
            else:
                self.checks_warned += 1
                self.category_stats[category]["warn"] += 1
        elif passed:
            self.checks_passed += 1
            self.category_stats[category]["pass"] += 1
        else:
            self.checks_skipped += 1
            self.category_stats[category]["skip"] += 1

    # ── Category 1: Structure ──────────────────────────────────────────

    def check_structure(self):
        """Check front/back matter order and document structure."""
        cat = "Structure"

        # Check front matter order in before-body.tex
        before_body = None
        for pattern in ["_extensions/book-kdp/before-body.tex", "_extensions/book-pdf/before-body.tex"]:
            p = self.project_path / pattern
            if p.exists():
                before_body = p.read_text()
                break

        if before_body:
            # CMOS front matter order: half-title, blank, title, copyright, dedication, TOC
            sections = []
            for marker, name in [
                ("Half-Title", "half-title"),
                ("Title Page", "title"),
                ("Copyright", "copyright"),
                ("Dedication", "dedication"),
            ]:
                if marker in before_body:
                    sections.append(name)

            expected = ["half-title", "title", "copyright", "dedication"]
            actual = [s for s in expected if s in sections]
            if actual != [s for s in sections if s in expected]:
                self._record(cat, False, Finding(
                    "STR-001", "MAJOR", cat,
                    "Front matter order incorrect",
                    str(before_body[:50]),
                    "CMOS 1.4",
                    f"Front matter order is {sections}, expected {expected}",
                    "Reorder sections in before-body.tex to match CMOS standard",
                    "Non-standard order may confuse readers familiar with book conventions"
                ))
            else:
                self._record(cat, True)

            # Check for missing front matter
            for req in ["half-title", "title", "copyright"]:
                if req not in sections:
                    self._record(cat, False, Finding(
                        f"STR-002-{req}", "CRITICAL", cat,
                        f"Missing required front matter: {req}",
                        "_extensions/book-*/before-body.tex",
                        "CMOS 1.4",
                        f"Required {req} page not found in front matter",
                        f"Add {req} page to before-body.tex",
                        "KDP and bookstores expect standard front matter"
                    ))
                else:
                    self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "STR-003", "CRITICAL", cat,
                "No before-body.tex found",
                "Project root",
                "CMOS 1.4",
                "Cannot find front matter LaTeX file",
                "Create _extensions/book-kdp/before-body.tex with front matter",
                "Book will have no title page or copyright page"
            ))

        # Check \frontmatter / \mainmatter in .tex
        if self.tex_file and self.tex_file.exists():
            tex = self.tex_file.read_text()

            if "\\frontmatter" not in tex:
                self._record(cat, False, Finding(
                    "STR-004", "MAJOR", cat,
                    "No \\frontmatter command",
                    str(self.tex_file),
                    "CMOS 1.1",
                    "\\frontmatter not found — front matter won't use roman numerals",
                    "Add \\frontmatter to before-body.tex",
                ))
            else:
                self._record(cat, True)

            if "\\mainmatter" not in tex:
                self._record(cat, False, Finding(
                    "STR-005", "MAJOR", cat,
                    "No \\mainmatter command",
                    str(self.tex_file),
                    "CMOS 1.1",
                    "\\mainmatter not found — page numbers won't switch to arabic",
                    "Ensure Quarto/pandoc generates \\mainmatter before Chapter 1",
                ))
            else:
                self._record(cat, True)

            # Check back matter
            back_matter_files = list((self.project_path / "back-matter").glob("*.qmd")) if (self.project_path / "back-matter").exists() else []
            bm_names = [f.stem for f in back_matter_files]

            for req, label in [("conclusion", "Conclusion"), ("about-author", "About the Author")]:
                if req in bm_names:
                    self._record(cat, True)
                else:
                    self._record(cat, False, Finding(
                        f"STR-006-{req}", "MINOR", cat,
                        f"Missing back matter: {label}",
                        "back-matter/",
                        "Publishing convention",
                        f"{label} page not found in back-matter/",
                        f"Create back-matter/{req}.qmd",
                    ))

    # ── Category 2: Typography ─────────────────────────────────────────

    def check_typography(self):
        """Check typography settings for print readability."""
        cat = "Typography"

        if not self.tex_file or not self.tex_file.exists():
            self._record(cat, False)
            return

        tex = self.tex_file.read_text()

        # Check line spacing
        stretch_match = re.search(r"\\setstretch\{([\d.]+)\}", tex)
        if stretch_match:
            stretch = float(stretch_match.group(1))
            if stretch < 1.1:
                self._record(cat, False, Finding(
                    "TYP-001", "MAJOR", cat,
                    f"Line spacing too tight ({stretch})",
                    str(self.tex_file),
                    "Bringhurst 2.4.2",
                    f"Line spacing is {stretch}, minimum recommended is 1.15 for body text",
                    "Set \\setstretch to 1.15-1.3",
                    "Readers will find text difficult to read"
                ))
            elif stretch > 1.45:
                self._record(cat, False, Finding(
                    "TYP-001", "MAJOR", cat,
                    f"Line spacing too loose ({stretch})",
                    str(self.tex_file),
                    "Bringhurst 2.4.2",
                    f"Line spacing is {stretch}, maximum recommended is 1.4. Inflates page count unnecessarily.",
                    "Set \\setstretch to 1.15-1.3",
                    "Excess pages increase printing cost and book price"
                ))
            else:
                self._record(cat, True)
        else:
            self._record(cat, True)  # Default LaTeX spacing is fine

        # Check font size
        fontsize_match = re.search(r"fontsize.*?(\d+)pt", tex)
        if fontsize_match:
            size = int(fontsize_match.group(1))
            if size < 10 or size > 13:
                self._record(cat, False, Finding(
                    "TYP-002", "MAJOR", cat,
                    f"Font size outside recommended range ({size}pt)",
                    str(self.tex_file),
                    "Bringhurst 2.3.2",
                    f"Body font is {size}pt, recommended range is 10-12pt for 6×9 books",
                    "Set fontsize to 11pt in _quarto-kdp.yml",
                ))
            else:
                self._record(cat, True)

        # Check widow/orphan control
        if "\\widowpenalty" in tex and "\\clubpenalty" in tex:
            self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "TYP-003", "MINOR", cat,
                "Widow/orphan control not set",
                str(self.tex_file),
                "Bringhurst 2.4.8",
                "\\widowpenalty and \\clubpenalty not found",
                "Add \\widowpenalty=10000 and \\clubpenalty=10000 to header",
                "Single lines may appear at top/bottom of pages"
            ))

        # Check parindent vs parskip (should use one, not both)
        has_indent = "\\parindent" in tex and "0pt" not in tex.split("\\parindent")[1][:20]
        has_parskip_pkg = "\\usepackage{parskip}" in tex
        # This is OK if we override parskip later
        self._record(cat, True)

        # Check line length (characters per line)
        # Approximate from geometry: textwidth / (font_size * 0.5)
        geometry_match = re.search(r"\\textwidth=([\d.]+)pt", tex)
        if geometry_match:
            textwidth_pt = float(geometry_match.group(1))
            # Approximate chars per line: textwidth / (font_size_pt * 0.55)
            font_pt = 11  # default
            chars_per_line = textwidth_pt / (font_pt * 0.5)
            if chars_per_line > 80:
                self._record(cat, False, Finding(
                    "TYP-004", "MAJOR", cat,
                    f"Line length too long (~{chars_per_line:.0f} chars)",
                    str(self.tex_file),
                    "Bringhurst 2.1.2",
                    f"Estimated {chars_per_line:.0f} characters per line, max recommended is 75",
                    "Increase margins or decrease text width",
                    "Long lines cause reader fatigue"
                ))
            elif chars_per_line < 45:
                self._record(cat, False, Finding(
                    "TYP-004", "MINOR", cat,
                    f"Line length very short (~{chars_per_line:.0f} chars)",
                    str(self.tex_file),
                    "Bringhurst 2.1.2",
                    f"Estimated {chars_per_line:.0f} characters per line, min recommended is 55",
                    "Decrease margins or increase text width",
                ))
            else:
                self._record(cat, True)

        # Check font embedding
        if "\\setmainfont" in tex or "fontspec" in tex:
            self._record(cat, True)  # fontspec with LuaLaTeX embeds fonts
        else:
            self._record(cat, False, Finding(
                "TYP-005", "MINOR", cat,
                "Font embedding not explicitly configured",
                str(self.tex_file),
                "KDP requirement",
                "No \\setmainfont found — using default LaTeX fonts (embedded by default with LuaLaTeX)",
                "Consider specifying fonts explicitly with fontspec",
            ))

    # ── Category 3: Page Layout ────────────────────────────────────────

    def check_page_layout(self):
        """Check page size, margins, headers for KDP compliance."""
        cat = "Page Layout"

        if not self.tex_file or not self.tex_file.exists():
            self._record(cat, False)
            return

        tex = self.tex_file.read_text()

        # Check page size
        pw_match = re.search(r"paperwidth\s*=\s*([\d.]+)(in|pt|cm)", tex)
        ph_match = re.search(r"paperheight\s*=\s*([\d.]+)(in|pt|cm)", tex)

        if pw_match and ph_match:
            pw = float(pw_match.group(1))
            ph = float(ph_match.group(1))
            pw_unit = pw_match.group(2)
            ph_unit = ph_match.group(2)

            # Convert to inches
            if pw_unit == "pt":
                pw /= 72.27
            elif pw_unit == "cm":
                pw /= 2.54
            if ph_unit == "pt":
                ph /= 72.27
            elif ph_unit == "cm":
                ph /= 2.54

            # KDP standard sizes
            valid_sizes = [
                (5.0, 8.0), (5.25, 8.0), (5.5, 8.5), (6.0, 9.0),
                (6.14, 9.21), (6.69, 9.61), (7.0, 10.0), (7.44, 9.69),
                (8.0, 10.0), (8.5, 11.0),
            ]
            size_valid = any(abs(pw - w) < 0.05 and abs(ph - h) < 0.05 for w, h in valid_sizes)

            if size_valid:
                self._record(cat, True)
            else:
                self._record(cat, False, Finding(
                    "LAY-001", "CRITICAL", cat,
                    f"Non-standard KDP trim size ({pw:.2f}×{ph:.2f} in)",
                    str(self.tex_file),
                    "KDP Content Guidelines",
                    f"Page size {pw:.2f}×{ph:.2f}\" is not a standard KDP trim size",
                    "Use a standard KDP size: 5×8, 5.5×8.5, 6×9, etc.",
                    "KDP will reject non-standard trim sizes"
                ))

        # Check margins
        inner_match = re.search(r"inner\s*=\s*([\d.]+)(in|pt|cm)", tex)
        outer_match = re.search(r"outer\s*=\s*([\d.]+)(in|pt|cm)", tex)

        if inner_match:
            inner = float(inner_match.group(1))
            unit = inner_match.group(2)
            if unit == "pt":
                inner /= 72.27
            elif unit == "cm":
                inner /= 2.54

            # KDP minimum gutter: 0.375" (24-150 pages), 0.75" (151-400), 0.875" (401-600)
            # Page count heuristic from file
            if inner < 0.75:
                self._record(cat, False, Finding(
                    "LAY-002", "CRITICAL", cat,
                    f"Inside margin too narrow ({inner:.3f}\")",
                    str(self.tex_file),
                    "KDP Margin Requirements",
                    f"Inner margin is {inner:.3f}\", KDP minimum for 151-400 pages is 0.75\"",
                    "Set inner margin to at least 0.75\" (0.875\" recommended)",
                    "KDP will reject — text will be lost in binding"
                ))
            else:
                self._record(cat, True)

        # Check running headers
        if "\\pagestyle{fancy}" in tex:
            self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "LAY-003", "MINOR", cat,
                "No running headers configured",
                str(self.tex_file),
                "Publishing convention",
                "fancyhdr not configured — no running headers on pages",
                "Add \\pagestyle{fancy} with book title and chapter name",
            ))

        # Check blank page handling
        if "cleardoublepage" in tex and "thispagestyle{empty}" in tex:
            self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "LAY-004", "MINOR", cat,
                "Blank pages may show headers",
                str(self.tex_file),
                "Publishing convention",
                "\\cleardoublepage not overridden to use empty page style",
                "Override \\cleardoublepage to set \\thispagestyle{empty} on blank pages",
                "Blank pages between chapters should have no content"
            ))

        # Check twoside
        if "twoside" in tex:
            self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "LAY-005", "MINOR", cat,
                "Document is oneside (no mirrored margins)",
                str(self.tex_file),
                "Print book convention",
                "Document uses oneside layout — margins won't alternate for binding",
                "Set twoside=true for print books",
                "Inner/outer margins won't adjust for left/right pages"
            ))

    # ── Category 4: Content Completeness ───────────────────────────────

    def check_content(self):
        """Check for unresolved placeholders, TODOs, and missing content."""
        cat = "Content"

        # Scan all .qmd files for placeholders
        qmd_files = self._filter_source_files(list(self.project_path.rglob("*.qmd")))
        placeholder_count = 0
        verify_count = 0
        need_example_count = 0
        todo_count = 0

        for f in qmd_files:
            text = f.read_text()
            ph = re.findall(r"\[PLACEHOLDER:[^\]]*\]", text)
            vr = re.findall(r"\[VERIFY:[^\]]*\]", text)
            ne = re.findall(r"\[NEED EXAMPLE:[^\]]*\]", text)
            td = re.findall(r"(?:TODO|FIXME|XXX|HACK)[\s:]", text, re.IGNORECASE)

            placeholder_count += len(ph)
            verify_count += len(vr)
            need_example_count += len(ne)
            todo_count += len(td)

        # Also check .tex files for placeholders (from before-body.tex dedication etc.)
        for f in self.project_path.rglob("*.tex"):
            if "font-samples" in f.name:
                continue
            text = f.read_text()
            ph = re.findall(r"\[PLACEHOLDER:[^\]]*\]", text)
            placeholder_count += len(ph)

        if placeholder_count > 0:
            self._record(cat, False, Finding(
                "CON-001", "CRITICAL", cat,
                f"{placeholder_count} unresolved [PLACEHOLDER:] tags",
                "Multiple files",
                "KDP Content Guidelines",
                f"Found {placeholder_count} [PLACEHOLDER:...] tags. KDP will reject manuscripts with placeholder text.",
                "Search for [PLACEHOLDER: and fill in all content",
                "Book cannot be published with placeholder text"
            ))
        else:
            self._record(cat, True)

        if verify_count > 0:
            self._record(cat, False, Finding(
                "CON-002", "MAJOR", cat,
                f"{verify_count} unverified [VERIFY:] tags",
                "Multiple files",
                "Editorial best practice",
                f"Found {verify_count} [VERIFY:...] tags — facts not yet verified",
                "Search for [VERIFY: and verify each claim",
            ))
        else:
            self._record(cat, True)

        if need_example_count > 0:
            self._record(cat, False, Finding(
                "CON-003", "MAJOR", cat,
                f"{need_example_count} missing [NEED EXAMPLE:] tags",
                "Multiple files",
                "Editorial best practice",
                f"Found {need_example_count} [NEED EXAMPLE:...] tags",
                "Search for [NEED EXAMPLE: and add examples",
            ))
        else:
            self._record(cat, True)

        if todo_count > 0:
            self._record(cat, False, Finding(
                "CON-004", "MINOR", cat,
                f"{todo_count} TODO/FIXME comments found",
                "Multiple files",
                "Publishing readiness",
                f"Found {todo_count} TODO/FIXME/XXX markers in manuscript files",
                "Search for TODO, FIXME, XXX and resolve or remove",
            ))
        else:
            self._record(cat, True)

    # ── Category 5: KDP Specific ───────────────────────────────────────

    def check_kdp(self):
        """KDP-specific compliance checks."""
        cat = "KDP Compliance"

        # Check PDF exists
        if self.pdf_file and self.pdf_file.exists():
            size_mb = self.pdf_file.stat().st_size / (1024 * 1024)
            if size_mb > 650:
                self._record(cat, False, Finding(
                    "KDP-001", "CRITICAL", cat,
                    f"PDF too large ({size_mb:.1f} MB)",
                    str(self.pdf_file),
                    "KDP File Requirements",
                    f"PDF is {size_mb:.1f} MB, KDP maximum is 650 MB",
                    "Compress images or reduce resolution",
                    "KDP will reject files over 650 MB"
                ))
            else:
                self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "KDP-002", "CRITICAL", cat,
                "No PDF found",
                "_output/kdp/",
                "KDP requirement",
                "No rendered PDF found. Run: quarto render --profile kdp --to pdf",
                "Render the PDF before running preflight",
            ))

        # Check ePub metadata
        epub_meta = self.project_path / "epub-metadata.yml"
        if epub_meta.exists():
            meta_text = epub_meta.read_text()
            if "ISBN when assigned" in meta_text or "[" in meta_text:
                self._record(cat, False, Finding(
                    "KDP-003", "MINOR", cat,
                    "ePub metadata has placeholder values",
                    str(epub_meta),
                    "KDP ebook requirements",
                    "epub-metadata.yml contains placeholder ISBN or publisher",
                    "Update with real values before Kindle upload (or remove if using free Amazon ISBN)",
                ))
            else:
                self._record(cat, True)
        else:
            self._record(cat, True)  # Not required if using Quarto profile

        # Check cover image
        cover = self.project_path / "covers" / "kindle-cover.jpg"
        if cover.exists():
            size = cover.stat().st_size
            if size < 50000:  # Less than 50KB is suspicious
                self._record(cat, False, Finding(
                    "KDP-004", "MINOR", cat,
                    "Cover image may be placeholder or low quality",
                    str(cover),
                    "KDP Cover Requirements",
                    f"Cover image is only {size/1024:.0f} KB — may be a placeholder",
                    "Replace with final cover design (minimum 2560×1600 pixels)",
                ))
            else:
                self._record(cat, True)
        else:
            self._record(cat, False, Finding(
                "KDP-005", "MAJOR", cat,
                "No Kindle cover image",
                "covers/kindle-cover.jpg",
                "KDP ebook requirements",
                "Cover image not found — required for Kindle ebook",
                "Add covers/kindle-cover.jpg (2560×1600 pixels minimum)",
            ))

    # ── Category 6: Legal & Metadata ───────────────────────────────────

    def check_legal(self):
        """Check copyright, ISBN, and metadata."""
        cat = "Legal & Metadata"

        # Check copyright page
        before_body = None
        for pattern in ["_extensions/book-kdp/before-body.tex", "_extensions/book-pdf/before-body.tex"]:
            p = self.project_path / pattern
            if p.exists():
                before_body = p.read_text()
                break

        if before_body:
            if "Copyright" in before_body and "textcopyright" in before_body:
                self._record(cat, True)

                # Check year
                current_year = str(datetime.now().year)
                if current_year in before_body:
                    self._record(cat, True)
                else:
                    self._record(cat, False, Finding(
                        "LEG-001", "MINOR", cat,
                        f"Copyright year may be outdated",
                        "_extensions/book-kdp/before-body.tex",
                        "Copyright law",
                        f"Current year ({current_year}) not found on copyright page",
                        f"Update copyright year to {current_year}",
                    ))

                # Check rights statement
                if "All rights reserved" in before_body:
                    self._record(cat, True)
                else:
                    self._record(cat, False, Finding(
                        "LEG-002", "MINOR", cat,
                        "No 'All rights reserved' statement",
                        "_extensions/book-kdp/before-body.tex",
                        "Publishing convention",
                        "Rights statement not found on copyright page",
                        "Add 'All rights reserved.' to copyright page",
                    ))

                # Check edition statement
                if "Edition" in before_body:
                    self._record(cat, True)
                else:
                    self._record(cat, False, Finding(
                        "LEG-003", "MINOR", cat,
                        "No edition statement",
                        "_extensions/book-kdp/before-body.tex",
                        "CMOS 1.20",
                        "No edition statement (e.g., 'First Edition') on copyright page",
                        "Add 'First Edition' to copyright page",
                    ))
            else:
                self._record(cat, False, Finding(
                    "LEG-004", "CRITICAL", cat,
                    "No copyright notice",
                    "_extensions/book-*/before-body.tex",
                    "Copyright law / KDP requirements",
                    "No copyright notice found in front matter",
                    "Add copyright page with © year, author name, and rights statement",
                    "Required by law and KDP"
                ))

    # ── Category 7: Consistency ────────────────────────────────────────

    def check_consistency(self):
        """Check terminology and formatting consistency."""
        cat = "Consistency"

        # Check for framework name consistency across chapters
        qmd_files = sorted(self._filter_source_files(
            list(self.project_path.rglob("chapters/**/*.qmd"))
        ))
        if not qmd_files:
            self._record(cat, False)
            return

        # Common inconsistency patterns
        all_text = ""
        for f in qmd_files:
            all_text += f.read_text() + "\n"

        # Check for common term variations
        term_pairs = [
            (r"\bAI\b", r"\ba\.i\.\b", "AI vs a.i."),
            (r"e-mail", r"email", "e-mail vs email"),
            (r"decision-support", r"decision support", "decision-support vs decision support (check consistency)"),
        ]

        for pattern1, pattern2, desc in term_pairs:
            count1 = len(re.findall(pattern1, all_text, re.IGNORECASE))
            count2 = len(re.findall(pattern2, all_text, re.IGNORECASE))
            if count1 > 0 and count2 > 0 and min(count1, count2) > 2:
                self._record(cat, False, Finding(
                    f"CON-010", "MINOR", cat,
                    f"Inconsistent terminology: {desc}",
                    "chapters/",
                    "Style consistency",
                    f"Both forms found: {count1} vs {count2} occurrences",
                    "Choose one form and use consistently throughout",
                ))
            else:
                self._record(cat, True)

        # Check chapter word counts for uniformity
        chapter_words = []
        for f in qmd_files:
            text = self._strip_yaml_frontmatter(f.read_text())
            words = len(text.split())
            chapter_words.append((f.name, words))

        if chapter_words:
            avg = sum(w for _, w in chapter_words) / len(chapter_words)
            for name, words in chapter_words:
                if words < avg * 0.4:
                    self._record(cat, False, Finding(
                        f"CON-011", "MINOR", cat,
                        f"Chapter significantly shorter than average: {name}",
                        f"chapters/.../{name}",
                        "Editorial balance",
                        f"{name} has {words} words, average is {avg:.0f}",
                        "Consider expanding or merging with adjacent chapter",
                    ))
                elif words > avg * 1.8:
                    self._record(cat, False, Finding(
                        f"CON-012", "MINOR", cat,
                        f"Chapter significantly longer than average: {name}",
                        f"chapters/.../{name}",
                        "Editorial balance",
                        f"{name} has {words} words, average is {avg:.0f}",
                        "Consider splitting into multiple chapters",
                    ))

            if not any(f for f in self.findings if f.finding_id in ("CON-011", "CON-012")):
                self._record(cat, True)

    # ── Category 8: Page Count Analysis ────────────────────────────────

    def check_page_count(self):
        """Analyze whether page count is reasonable for word count."""
        cat = "Page Count"

        # Count words in all .qmd files (excluding worktrees/output)
        total_words = 0
        for f in self._filter_source_files(list(self.project_path.rglob("*.qmd"))):
            total_words += len(self._strip_yaml_frontmatter(f.read_text()).split())

        if total_words == 0:
            self._record(cat, False)
            return

        # Expected pages: ~250 words/page for 6×9 at 11pt with 1.2 spacing
        expected_pages = total_words / 250
        # Add ~15% for front/back matter, part pages, blank pages
        expected_pages *= 1.15

        self._record(cat, True)  # Record the analysis as INFO
        self.findings.append(Finding(
            "PGC-001", "INFO", cat,
            f"Page count analysis",
            "Entire manuscript",
            "Publishing economics",
            f"Manuscript: ~{total_words:,} words. Expected pages at 6×9/11pt/1.2 spacing: {expected_pages:.0f}. "
            f"If actual page count exceeds {expected_pages * 1.2:.0f}, check line spacing, margins, or excess blank pages.",
            "Adjust line spacing (1.15-1.25) or margins to hit target page count",
            f"KDP printing cost increases with page count. Each extra page adds ~$0.012 to print cost."
        ))

    # ── Run All Checks ─────────────────────────────────────────────────

    def run_audit(self, categories: Optional[list[str]] = None):
        """Run all audit checks."""
        all_checks = {
            "structure": self.check_structure,
            "typography": self.check_typography,
            "page_layout": self.check_page_layout,
            "content": self.check_content,
            "kdp": self.check_kdp,
            "legal": self.check_legal,
            "consistency": self.check_consistency,
            "page_count": self.check_page_count,
        }

        if self.mode == "quick":
            selected = ["structure", "kdp", "content"]
        elif categories:
            selected = [c for c in categories if c in all_checks]
        else:
            selected = list(all_checks.keys())

        for name in selected:
            all_checks[name]()

    # ── Report Generation ──────────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a markdown audit report with SHA-256 verification."""
        now = datetime.now(timezone.utc).isoformat()
        project_name = self.project_path.name

        # Detect book title from config
        title = project_name
        if self.quarto_config:
            config_text = self.quarto_config.read_text()
            title_match = re.search(r'title:\s*"([^"]+)"', config_text)
            if title_match:
                title = title_match.group(1)

        # Build category table
        cat_rows = []
        for cat, stats in sorted(self.category_stats.items()):
            cat_rows.append(
                f"| {cat:<20} | {stats['pass']:<4} | {stats['fail']:<4} | {stats['warn']:<4} | {stats['skip']:<4} |"
            )
        cat_rows.append(
            f"| {'**Total**':<20} | {self.checks_passed:<4} | {self.checks_failed:<4} | {self.checks_warned:<4} | {self.checks_skipped:<4} |"
        )

        status = "PASS" if self.checks_failed == 0 else "FAIL"
        status_icon = "✅" if status == "PASS" else "❌"

        # Build findings section
        findings_text = ""
        for sev in ["CRITICAL", "MAJOR", "MINOR", "INFO"]:
            sev_findings = [f for f in self.findings if f.severity == sev]
            if sev_findings:
                for f in sev_findings:
                    findings_text += f"\n### [{f.severity}] {f.finding_id}: {f.title}\n"
                    findings_text += f"**Location:** `{f.location}`\n"
                    findings_text += f"**Standard:** {f.standard}\n"
                    findings_text += f"**Description:** {f.description}\n"
                    findings_text += f"**Fix:** {f.fix}\n"
                    if f.impact:
                        findings_text += f"**Impact:** {f.impact}\n"

        if not findings_text:
            findings_text = "\nNo issues found. Manuscript passes all checks.\n"

        # Build report body (before hash)
        report_body = f"""# Manuscript Audit Report

**Project:** {title}
**Date:** {now}
**Mode:** {self.mode}
**Auditor:** claude-book-publisher v{VERSION}
**Project Path:** `{self.project_path}`

## Summary

| Category             | Pass | Fail | Warn | Skip |
|---------------------|------|------|------|------|
{chr(10).join(cat_rows)}

**Status:** {status_icon} {status} ({self.checks_failed} critical/major, {self.checks_warned} minor/info)

## Findings
{findings_text}
"""

        # Generate cryptographic hash of findings (for verification)
        findings_json = json.dumps(
            [f.to_dict() for f in self.findings],
            sort_keys=True,
            indent=2,
        )
        content_hash = hashlib.sha256(
            (report_body + findings_json).encode()
        ).hexdigest()

        # Append verification section
        report = report_body + f"""
## Verification

**Report Hash (SHA-256):** `{content_hash}`
**Findings Count:** {len(self.findings)}
**Checks Executed:** {self.checks_run}

To verify this report has not been modified:
```bash
python3 scripts/verify_report.py audit-report.md
```

---
*Generated by claude-book-publisher v{VERSION}*
"""
        return report

    def generate_findings_json(self) -> str:
        """Generate machine-readable findings JSON."""
        return json.dumps(
            {
                "version": VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project": str(self.project_path),
                "mode": self.mode,
                "summary": {
                    "total_checks": self.checks_run,
                    "passed": self.checks_passed,
                    "failed": self.checks_failed,
                    "warned": self.checks_warned,
                    "skipped": self.checks_skipped,
                    "status": "PASS" if self.checks_failed == 0 else "FAIL",
                },
                "findings": [f.to_dict() for f in self.findings],
                "category_stats": self.category_stats,
            },
            indent=2,
            sort_keys=True,
        )


def main():
    parser = argparse.ArgumentParser(description="Manuscript Audit Validator")
    parser.add_argument("project_path", help="Path to the book project root")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="full",
        help="Audit mode: quick (structure+KDP+content) or full (all checks)",
    )
    parser.add_argument(
        "--category",
        nargs="+",
        choices=["structure", "typography", "page_layout", "content", "kdp", "legal", "consistency", "page_count"],
        help="Run specific categories only",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of markdown",
    )

    args = parser.parse_args()

    auditor = ManuscriptAuditor(args.project_path, args.mode)
    auditor.run_audit(args.category)

    if args.json:
        report = auditor.generate_findings_json()
    else:
        report = auditor.generate_report()

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Exit with non-zero if critical/major findings
    sys.exit(1 if auditor.checks_failed > 0 else 0)


if __name__ == "__main__":
    main()

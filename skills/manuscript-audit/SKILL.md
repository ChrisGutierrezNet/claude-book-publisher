---
name: manuscript-audit
description: |
  Run a comprehensive manuscript audit against professional publishing standards.
  Checks 80+ quality gates across typography, structure, KDP compliance, and content.
  Generates a cryptographically signed audit report.

  **Perfect for:**
  - Pre-submission QA before uploading to KDP/IngramSpark
  - Manuscript review after editorial passes
  - Catching formatting regressions after config changes
  - Verifying front/back matter completeness
  - Typography validation for print readiness

  **Not ideal for:**
  - Content editing or copyediting (use a human editor)
  - Cover design validation (separate process)
  - Marketing copy review
---

# Manuscript Audit

## Overview

This skill runs a full publishing QA audit on a Quarto/LaTeX book manuscript. It checks 80+ quality gates organized into 8 categories, generates a detailed report with findings, and signs the report with a SHA-256 hash for verification.

## Audit Categories

### 1. Structure (CMOS 1.4–1.107)
- Front matter page order (half-title, title, copyright, dedication, TOC, preface)
- Back matter order (appendices, glossary, bibliography, index, about author)
- \frontmatter / \mainmatter / \backmatter placement
- Part and chapter numbering consistency
- Section hierarchy (no skipped levels)

### 2. Typography (Bringhurst, Elements of Typographic Style)
- Line length: 55–75 characters per line (optimal: 66)
- Leading (line spacing): 120–145% of font size
- Font size: 10–12pt for body text
- Paragraph indent: 1–1.5em (first line)
- No paragraph spacing with indent (choose one, not both)
- Widow/orphan control enabled
- Hyphenation settings reasonable
- Font embedding verified in PDF

### 3. Page Layout (KDP + CMOS)
- Trim size matches declared format
- Margins meet KDP minimums for page count
- Gutter (inside margin) adequate for binding
- Running headers: correct content, suppressed on blank/chapter pages
- Page numbers: roman in front matter, arabic in body
- Blank pages truly blank (no headers/footers)
- Chapter opening pages on recto (right) for print

### 4. Content Completeness
- No unresolved [PLACEHOLDER:...] tags (KDP will reject)
- No [VERIFY:...] tags remaining
- No [NEED EXAMPLE:...] tags remaining
- No TODO/FIXME/XXX comments in manuscript
- All cross-references resolve
- Bibliography entries all cited (no orphans)
- Images referenced exist at adequate resolution (300 DPI for print)

### 5. KDP Compliance
- PDF page size exactly matches declared trim (6×9 = 432×648 pt)
- No crop marks or printer marks
- All fonts embedded (no system font references)
- No color content in B&W interior (grayscale only)
- File size under 650 MB
- No password protection or DRM
- No blank pages at start or end of PDF

### 6. ePub/Kindle Compliance
- Valid ePub 3.x structure
- Cover image present and correct dimensions
- Reflowable layout (no fixed positioning)
- Metadata complete (title, author, description, subject)
- TOC navigation document present
- No JavaScript or external references
- Alt text on all images

### 7. Legal & Metadata
- Copyright page present with correct year
- ISBN format valid (if provided)
- Rights statement present
- Publisher name (or "Independently Published")
- Edition statement
- Country of printing
- BISAC categories appropriate

### 8. Consistency
- Framework/term names consistent throughout
- Character names consistent (no mid-book changes)
- Formatting conventions consistent (bold, italic usage)
- Example coverage across reader segments (if applicable)
- Heading capitalization style consistent

## Running the Audit

### Quick audit (structure + KDP compliance only):
```bash
python3 scripts/validate_manuscript.py --mode quick path/to/project
```

### Full audit (all 80+ checks):
```bash
python3 scripts/validate_manuscript.py --mode full path/to/project
```

### Specific category:
```bash
python3 scripts/validate_manuscript.py --category typography path/to/project
```

## Report Format

The audit generates a markdown report with:

```markdown
# Manuscript Audit Report
**Project:** AI Is Your Intern, Not Your CEO
**Date:** 2026-06-13T12:00:00Z
**Mode:** full
**Auditor:** claude-book-publisher v0.1.0

## Summary
| Category      | Pass | Fail | Warn | Skip |
|--------------|------|------|------|------|
| Structure     | 12   | 1    | 0    | 0    |
| Typography    | 8    | 2    | 1    | 0    |
| ...           | ...  | ...  | ...  | ...  |
| **Total**     | 72   | 5    | 3    | 2    |

**Status:** ❌ FAIL (5 critical/major issues)

## Findings

### [CRITICAL] STR-001: Front matter order incorrect
**Location:** _extensions/book-kdp/before-body.tex
**Standard:** CMOS 1.4
**Description:** Dedication appears before copyright page
**Fix:** Move dedication after copyright page
**Impact:** Non-standard, may confuse readers

### [MAJOR] TYP-003: Line length exceeds 75 characters
...

## Verification
**Report Hash (SHA-256):** a1b2c3d4...
**Verification:** python3 scripts/verify_report.py audit-report.md
```

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| CRITICAL | KDP will reject or major standards violation | Must fix before upload |
| MAJOR | Professional quality issue | Should fix |
| MINOR | Preference or minor inconsistency | Nice to fix |
| INFO | Observation, no action needed | For awareness |

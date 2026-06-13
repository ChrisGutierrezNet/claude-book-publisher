---
name: typography-check
description: |
  Typography and layout quality analysis for print books.
  Validates line length, leading, font choices, paragraph formatting,
  and readability against Bringhurst's Elements of Typographic Style.
---

# Typography Check

## Key Metrics

### Line Length (Bringhurst 2.1.2)
- **Optimal:** 66 characters per line
- **Acceptable:** 55–75 characters per line
- **Calculation:** text_width / (font_size × 0.5) ≈ chars_per_line

### Leading / Line Spacing (Bringhurst 2.4.2)
- **Tight:** 1.0–1.1 (reference books, footnotes)
- **Standard:** 1.15–1.25 (most books)
- **Generous:** 1.3–1.4 (large print, textbooks)
- **Too loose:** >1.45 (inflates page count)

### Font Size (Bringhurst 2.3.2)
- **Standard:** 10–12pt for body text
- **Optimal for 6×9:** 11pt
- **Minimum readable:** 9pt (footnotes only)

### Paragraph Style
- **Indent:** 1–1.5em first line indent, NO inter-paragraph space
- **Block:** No indent, 6–12pt inter-paragraph space
- **Never:** Both indent AND space (choose one)

### Widow/Orphan Control
- **Widow:** Single last line of paragraph at top of page
- **Orphan:** Single first line of paragraph at bottom of page
- **Fix:** \widowpenalty=10000 \clubpenalty=10000

## Font Pairing for Business Books

| Body (Serif) | Heading (Sans) | Character |
|-------------|----------------|-----------|
| Charter     | Helvetica Neue | Clean, modern |
| Palatino    | Gill Sans      | Warm, approachable |
| Garamond    | Futura         | Classic, elegant |
| Baskerville | Avenir         | Refined, professional |
| Minion Pro  | Myriad Pro     | Adobe standard |

## Usage

```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --category typography path/to/project
```

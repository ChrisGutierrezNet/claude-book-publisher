---
name: kdp-preflight
description: |
  Amazon KDP-specific preflight validation. Checks all requirements that cause
  KDP upload rejections: page size, margins, font embedding, file size, content flags.
---

# KDP Preflight

## Checks

1. **Page size** — Must match a standard KDP trim size exactly
2. **Margins** — Must meet minimums based on page count bracket
3. **Font embedding** — All fonts must be embedded in PDF
4. **File size** — Under 650 MB for interior, under 50 MB for cover
5. **Cover dimensions** — Correct for trim size and page count
6. **Content flags** — No placeholder text, no "lorem ipsum"
7. **Bleed** — If using bleed, must extend 0.125" on all sides
8. **Color space** — B&W interior must have no color elements
9. **Image resolution** — Minimum 300 DPI for print
10. **Metadata** — Title and author must match KDP listing

## KDP Margin Requirements

| Page Count | Inside Margin (min) | Outside/Top/Bottom (min) |
|-----------|--------------------|-----------------------|
| 24–150    | 0.375"             | 0.25"                 |
| 151–300   | 0.75"              | 0.25"                 |
| 301–500   | 0.875"             | 0.25"                 |
| 501–700   | 1.0"               | 0.25"                 |
| 701–828   | 1.125"             | 0.25"                 |

## Common KDP Rejection Reasons

1. Placeholder text visible in manuscript
2. Page size doesn't match selected trim
3. Margins too narrow for page count
4. Fonts not embedded (references system fonts)
5. Blank pages at beginning or end
6. Cover spine width incorrect for page count
7. Image resolution below 300 DPI
8. File format not PDF (e.g., Word doc uploaded)

## Usage

```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --category kdp path/to/project
```

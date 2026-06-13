---
name: front-back-matter
description: |
  Validates front and back matter order and completeness against
  Chicago Manual of Style 17th Edition.
---

# Front & Back Matter Validation

## Front Matter Order (CMOS 1.4–1.107)

Standard order for nonfiction:

| # | Page | Required | Recto/Verso | Page Numbers |
|---|------|----------|-------------|--------------|
| 1 | Half-title | Yes | Recto | None |
| 2 | Blank (or series page) | — | Verso | None |
| 3 | Title page | Yes | Recto | None |
| 4 | Copyright page | Yes | Verso | None |
| 5 | Dedication | Optional | Recto | None |
| 6 | Blank | — | Verso | None |
| 7 | Table of Contents | Yes | Recto | Roman |
| 8 | List of Figures | Optional | Recto | Roman |
| 9 | List of Tables | Optional | Recto | Roman |
| 10 | Foreword | Optional | Recto | Roman |
| 11 | Preface | Optional | Recto | Roman |
| 12 | Acknowledgments (alt) | Optional | Recto | Roman |
| 13 | Introduction | Optional | Recto | Roman |

## Back Matter Order (CMOS 1.4)

| # | Page | Required | Notes |
|---|------|----------|-------|
| 1 | Appendix(es) | Optional | Lettered (A, B, C) or numbered |
| 2 | Glossary | Optional | Alphabetical |
| 3 | Bibliography | If cited | APA, Chicago, etc. |
| 4 | Index | Optional | Professional indexer recommended |
| 5 | Acknowledgments (alt) | Optional | Can go here instead of front |
| 6 | About the Author | Recommended | Third person, 150–250 words |

## Copyright Page Requirements

Must include:
- Copyright symbol © + year + author name
- Rights statement ("All rights reserved")
- ISBN (if purchased)
- Edition number
- Country of printing
- Disclaimer (if applicable)
- Publisher name (or "Independently Published")

Optional:
- Library of Congress data
- Permissions acknowledgments
- Design/typesetting credits
- Paper/environmental statement

## Usage

```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --category structure path/to/project
```

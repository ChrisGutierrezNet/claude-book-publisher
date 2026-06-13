# Claude Book Publisher

Professional book publishing QA, formatting validation, and KDP preflight for Claude Code.

Inspired by [anthropics/financial-services](https://github.com/anthropics/financial-services) — same plugin architecture, applied to book publishing.

## What It Does

Audits book manuscripts against 80+ quality gates across 8 categories:

| Category | What It Checks |
|----------|---------------|
| **Structure** | Front/back matter order, CMOS compliance, \frontmatter/\mainmatter |
| **Typography** | Line length, leading, font size, widow/orphan, paragraph style |
| **Page Layout** | Trim size, margins, running headers, blank pages, twoside |
| **Content** | Placeholders, TODOs, cross-refs, unverified claims |
| **KDP Compliance** | Page size, margins, fonts, file size, cover |
| **Legal & Metadata** | Copyright, ISBN, rights, edition, BISAC categories |
| **Consistency** | Term usage, character names, heading style, chapter balance |
| **Page Count** | Words-to-pages ratio, printing cost analysis |

Every audit report is cryptographically signed with SHA-256 for verification.

## Quick Start

### Run a full audit:
```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --mode full /path/to/book
```

### Run KDP preflight only:
```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --category kdp /path/to/book
```

### Output JSON for CI/CD:
```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --json --output report.json /path/to/book
```

### Verify a previous report:
```bash
python3 skills/manuscript-audit/scripts/verify_report.py audit-report.md
```

## Architecture

```
claude-book-publisher/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── agents/
│   └── book-publisher.md        # Agent system prompt
├── skills/
│   ├── manuscript-audit/        # Core audit skill
│   │   ├── SKILL.md             # Skill definition (80+ checks)
│   │   └── scripts/
│   │       ├── validate_manuscript.py  # Audit engine
│   │       └── verify_report.py        # Report verification
│   ├── kdp-preflight/           # KDP-specific checks
│   │   └── SKILL.md
│   ├── typography-check/        # Typography validation
│   │   └── SKILL.md
│   └── front-back-matter/       # CMOS front/back matter
│       └── SKILL.md
├── CLAUDE.md                    # Project instructions
└── README.md
```

## Standards Referenced

- **Chicago Manual of Style** (17th Edition) — Front/back matter, structure
- **Bringhurst, Elements of Typographic Style** — Typography
- **Amazon KDP Content Guidelines** (2024) — Print-on-demand compliance
- **International ISBN Agency** — ISBN formatting
- **BISAC Subject Headings** — Category classification
- **PDF/A-1b** — Archival compliance

## Report Format

Audit reports include:
- Summary table with pass/fail/warn/skip counts per category
- Detailed findings with severity, location, standard, description, and fix
- SHA-256 hash for cryptographic verification
- Machine-readable JSON output option

### Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| CRITICAL | KDP will reject or standards violation | Must fix |
| MAJOR | Professional quality issue | Should fix |
| MINOR | Preference or minor inconsistency | Nice to fix |
| INFO | Observation only | Awareness |

## License

MIT

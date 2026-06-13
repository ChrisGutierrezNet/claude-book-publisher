# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

A Claude Code plugin for professional book publishing QA. Audits manuscripts against Chicago Manual of Style, Amazon KDP requirements, and typography best practices.

## Running the Audit

```bash
python3 skills/manuscript-audit/scripts/validate_manuscript.py --mode full /path/to/book
```

## Architecture

- `skills/manuscript-audit/scripts/validate_manuscript.py` — Core audit engine (all checks)
- `skills/manuscript-audit/scripts/verify_report.py` — Cryptographic report verification
- `skills/*/SKILL.md` — Skill definitions with standards references
- `agents/book-publisher.md` — Agent system prompt

## Standards

All checks cite specific standards: CMOS section numbers, Bringhurst chapters, or KDP guideline sections. Do not add checks without a standards reference.

## Adding New Checks

1. Add the check method to `ManuscriptAuditor` in `validate_manuscript.py`
2. Use `self._record()` to track pass/fail
3. Create `Finding` objects with severity, standard citation, and fix recommendation
4. Update the relevant `SKILL.md` with the new check description

#!/usr/bin/env python3
"""
Editorial Fix Generator for Nonfiction Business Books

Finds editorial issues, generates concrete replacement text,
and outputs a styled HTML report with before/after comparisons.

Usage:
    python3 fix_editorial.py path/to/project
    python3 fix_editorial.py --output fixes.html path/to/project
    python3 fix_editorial.py --chapter ch01 path/to/project
"""

import argparse
import html
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


VERSION = "0.1.0"


# ── Replacement Maps ────────────────────────────────────────────────────

GURU_REPLACEMENTS = {
    "leverage": "use",
    "leveraging": "using",
    "leveraged": "used",
    "Leverage": "Use",
    "Leveraging": "Using",
    "Leveraged": "Used",
    "unlock": "enable",
    "unlocking": "enabling",
    "Unlock": "Enable",
    "Unlocking": "Enabling",
    "unleash": "release",
    "Unleash": "Release",
    "unleashing": "releasing",
    "transformative": "significant",
    "Transformative": "Significant",
    "paradigm shift": "fundamental change",
    "Paradigm shift": "Fundamental change",
    "game-changer": "breakthrough",
    "game changer": "breakthrough",
    "Game-changer": "Breakthrough",
    "synergy": "collaboration",
    "synergies": "combined benefits",
    "Synergy": "Collaboration",
    "Synergies": "Combined benefits",
    "disruptive": "innovative",
    "Disruptive": "Innovative",
    "disrupt": "challenge",
    "Disrupt": "Challenge",
    "empower": "enable",
    "empowering": "enabling",
    "empowerment": "capability",
    "Empower": "Enable",
    "Empowering": "Enabling",
    "Empowerment": "Capability",
    "supercharge": "accelerate",
    "Supercharge": "Accelerate",
    "revolutionize": "fundamentally improve",
    "Revolutionize": "Fundamentally improve",
    "next-level": "advanced",
    "next level": "advanced",
    "Next-level": "Advanced",
    "move the needle": "make measurable progress",
    "Move the needle": "Make measurable progress",
    "boil the ocean": "take on too much at once",
    "exponentially": "rapidly",
    "exponential": "rapid",
    "Exponentially": "Rapidly",
    "Exponential": "Rapid",
}

FILLER_REPLACEMENTS = {
    "it's important to note that": "",
    "it is important to note that": "",
    "at the end of the day": "",
    "the reality is that": "",
    "let's be honest": "",
    "let us be honest": "",
    "here's the thing": "",
    "here is the thing": "",
    "the fact of the matter is": "",
    "it goes without saying": "",
    "needless to say": "",
    "in order to": "to",
    "the bottom line is": "",
    "when all is said and done": "ultimately",
    "as a matter of fact": "",
    "it should be noted that": "",
    "it is worth mentioning that": "",
}

TEXTBOOK_REPLACEMENTS = {
    r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) explore": "Let's dig into",
    r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) discuss": "Here's what matters about",
    r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) examine": "Let's look at",
    r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) cover": "Here's what you need to know about",
    r"[Tt]his chapter covers": "You'll learn",
    r"[Tt]his chapter discusses": "Here's what matters:",
    r"[Tt]his chapter explores": "Let's dig into",
    r"[Tt]his chapter examines": "Let's look at",
    r"[Tt]his section covers": "Here's what you need:",
    r"[Aa]s previously mentioned": "As we saw earlier",
    r"[Aa]s earlier mentioned": "As we covered",
    r"[Tt]he reader should note that": "Notice that",
    r"[Tt]he reader should be aware that": "Keep in mind:",
    r"[Ii]t can be concluded that": "The takeaway:",
    r"[Aa]s we shall see": "You'll see",
    r"[Ii]n the following section": "Next",
}

HEDGING_REPLACEMENTS = {
    r"\bperhaps\b": "[DELETE or state directly]",
    r"\bmaybe\b": "[DELETE or state directly]",
    r"\bsomewhat\b": "[DELETE — either it is or isn't]",
    r"\barguably\b": "[DELETE — make the argument instead]",
    r"\bto some extent\b": "[DELETE or quantify]",
    r"\bit seems\b": "it is",
    r"\bappears to\b": "[state directly]",
    r"\bin my opinion\b": "[DELETE — it's your book]",
    r"\bI think that\b": "[DELETE — just state it]",
    r"\bI believe that\b": "[DELETE — just state it]",
    r"\bI feel that\b": "[DELETE — just state it]",
    r"\bkind of\b": "[DELETE or be specific]",
    r"\bsort of\b": "[DELETE or be specific]",
}

VAGUE_SOURCE_FIXES = {
    r"[Rr]esearch shows": "[Name the researcher/study] found",
    r"[Rr]esearch suggests": "[Name the researcher/study] found",
    r"[Rr]esearch indicates": "[Name the researcher/study] found",
    r"[Rr]esearch has shown": "[Name the researcher/study] found",
    r"[Ss]tudies show": "A [year] [institution] study found",
    r"[Ss]tudies suggest": "A [year] [institution] study found",
    r"[Ss]tudies indicate": "A [year] [institution] study found",
    r"[Ss]tudies have shown": "A [year] [institution] study found",
    r"[Ee]xperts say": "[Named expert] says",
    r"[Ee]xperts agree": "[Named expert] argues",
    r"[Ee]xperts believe": "[Named expert] argues",
    r"[Ee]xperts recommend": "[Named expert] recommends",
    r"[Aa]ccording to (?:some|many|most|several)": "According to [specific source]",
    r"[Dd]ata shows": "[Source]'s data shows",
    r"[Dd]ata suggests": "[Source]'s data shows",
}

PASSIVE_PATTERNS = [
    (r"\b(is|are|was|were|been|being)\s+(\w+ed)\b", "passive voice"),
    (r"\b(is|are|was|were|been|being)\s+(\w+en)\b", "passive voice"),
]

TIME_FRAME_TEMPLATES = [
    "**This week:** ",
    "**Before your next meeting:** ",
    "**In the next 30 minutes:** ",
    "**Monday morning:** ",
    "**Today:** ",
]

ACTION_VERB_TEMPLATES = [
    "**Step 1:** Open [tool/document] and create...",
    "**Step 1:** Write down your top three...",
    "**Step 1:** List every task you...",
    "**Step 1:** Schedule 30 minutes to...",
    "**Step 1:** Send a message to your team about...",
]

HOOK_STORY_TEMPLATE = """**Rewrite as a Story Hook:**

[Name] manages [role] at [company type]. [Specific situation that creates tension].

[What happened — the surprise, failure, or discovery].

[Why this matters to the reader — the universal lesson].

**Example:**
Maya runs customer success for a 200-person SaaS company. Last quarter, she spent
11 hours every week writing the same onboarding emails with minor variations — while
her team's response times crept past the 24-hour mark.

Then she built a workflow that cut those 11 hours to 90 minutes. This chapter shows
you exactly how she did it.
"""


class Fix:
    """A single editorial fix with before/after text."""

    def __init__(self, category: str, severity: str, chapter: str,
                 file_path: str, line_num: int, context_before: str,
                 original: str, replacement: str, explanation: str):
        self.category = category
        self.severity = severity
        self.chapter = chapter
        self.file_path = file_path
        self.line_num = line_num
        self.context_before = context_before
        self.original = original
        self.replacement = replacement
        self.explanation = explanation


class EditorialFixer:
    """Finds issues and generates concrete fixes with replacement text."""

    def __init__(self, project_path: str, chapter_filter: str = None):
        self.project_path = Path(project_path)
        self.chapter_filter = chapter_filter
        self.fixes: list[Fix] = []
        self.chapter_files: list[Path] = []
        self.stats = Counter()

        self._load_chapters()

    def _load_chapters(self):
        excluded = {".worktrees", "_output", "_site", "_book", ".git", "node_modules"}
        for f in sorted(self.project_path.rglob("chapters/**/*.qmd")):
            parts = f.relative_to(self.project_path).parts
            if any(p in excluded or p.startswith(".") for p in parts):
                continue
            if self.chapter_filter and self.chapter_filter not in f.name:
                continue
            content = f.read_text()
            if len(content.split()) > 200:
                self.chapter_files.append(f)

    def _add_fix(self, category, severity, chapter, file_path, line_num,
                 context, original, replacement, explanation):
        self.fixes.append(Fix(
            category, severity, chapter, file_path, line_num,
            context, original, replacement, explanation
        ))
        self.stats[category] += 1

    def _find_line_num(self, text: str, target: str) -> int:
        """Find the line number of target string in text."""
        pos = text.lower().find(target.lower())
        if pos == -1:
            return 0
        return text[:pos].count("\n") + 1

    def _get_context(self, text: str, target: str, window: int = 80) -> str:
        """Get surrounding context for a match."""
        pos = text.lower().find(target.lower())
        if pos == -1:
            return ""
        start = max(0, pos - window)
        end = min(len(text), pos + len(target) + window)
        ctx = text[start:end]
        if start > 0:
            ctx = "..." + ctx
        if end < len(text):
            ctx = ctx + "..."
        return ctx

    # ── Fix Generators ──────────────────────────────────────────────────

    def fix_guru_speak(self):
        """Find and replace guru-speak/buzzwords."""
        for f in self.chapter_files:
            text = f.read_text()
            for guru_word, replacement in GURU_REPLACEMENTS.items():
                # Use word boundary search
                pattern = re.compile(r'\b' + re.escape(guru_word) + r'\b')
                for match in pattern.finditer(text):
                    matched = match.group()
                    context = self._get_context(text, matched,
                                                 window=60)
                    line_num = self._find_line_num(text, matched)
                    self._add_fix(
                        "Guru-Speak", "MAJOR", f.name, str(f), line_num,
                        context, matched, replacement,
                        f'Replace buzzword "{matched}" with concrete language'
                    )

    def fix_filler_phrases(self):
        """Find and remove/replace filler phrases."""
        for f in self.chapter_files:
            text = f.read_text()
            text_lower = text.lower()
            for filler, replacement in FILLER_REPLACEMENTS.items():
                idx = 0
                while True:
                    pos = text_lower.find(filler, idx)
                    if pos == -1:
                        break
                    original = text[pos:pos + len(filler)]
                    context = self._get_context(text, original, window=80)
                    line_num = self._find_line_num(text, original)

                    if replacement:
                        fix_text = replacement
                        expl = f'Replace filler phrase with "{replacement}"'
                    else:
                        # Show the sentence without the filler
                        sent_start = text.rfind(".", 0, pos)
                        sent_end = text.find(".", pos + len(filler))
                        if sent_start == -1:
                            sent_start = 0
                        if sent_end == -1:
                            sent_end = len(text)
                        full_sent = text[sent_start + 1:sent_end + 1].strip()
                        cleaned = re.sub(
                            re.escape(original) + r",?\s*",
                            "", full_sent, count=1
                        ).strip()
                        # Capitalize first letter
                        if cleaned:
                            cleaned = cleaned[0].upper() + cleaned[1:]
                        fix_text = cleaned
                        expl = "Delete filler phrase — start with the actual point"

                    self._add_fix(
                        "Filler Phrases", "MINOR", f.name, str(f), line_num,
                        context, original, fix_text, expl
                    )
                    idx = pos + len(filler)

    def fix_textbook_voice(self):
        """Replace textbook-style phrasing with conversational voice."""
        for f in self.chapter_files:
            text = f.read_text()
            for pattern, replacement in TEXTBOOK_REPLACEMENTS.items():
                for match in re.finditer(pattern, text):
                    original = match.group()
                    context = self._get_context(text, original, window=80)
                    line_num = self._find_line_num(text, original)
                    self._add_fix(
                        "Textbook Voice", "MINOR", f.name, str(f), line_num,
                        context, original, replacement,
                        "Replace academic phrasing with conversational voice"
                    )

    def fix_hedging(self):
        """Flag hedging language with direct alternatives."""
        for f in self.chapter_files:
            text = f.read_text()
            for pattern, replacement in HEDGING_REPLACEMENTS.items():
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    original = match.group()
                    context = self._get_context(text, original, window=80)
                    line_num = self._find_line_num(text, original)
                    self._add_fix(
                        "Hedging Language", "MINOR", f.name, str(f), line_num,
                        context, original, replacement,
                        "Replace hedging with direct statement"
                    )

    def fix_vague_sources(self):
        """Replace vague source references with attribution templates."""
        for f in self.chapter_files:
            text = f.read_text()
            for pattern, replacement in VAGUE_SOURCE_FIXES.items():
                for match in re.finditer(pattern, text):
                    original = match.group()
                    context = self._get_context(text, original, window=100)
                    line_num = self._find_line_num(text, original)
                    self._add_fix(
                        "Vague Sources", "MAJOR", f.name, str(f), line_num,
                        context, original, replacement,
                        "Name the specific study, researcher, or publication"
                    )

    def fix_long_sentences(self):
        """Find sentences over 35 words and suggest split points."""
        for f in self.chapter_files:
            text = f.read_text()
            # Strip YAML
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    text = text[end + 3:]

            # Remove code blocks and tables
            clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
            clean = re.sub(r"\|.*\|", "", clean)
            clean = re.sub(r"^>.*$", "", clean, flags=re.MULTILINE)

            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', clean)
            for sent in sentences:
                words = sent.split()
                if len(words) > 35:
                    # Find natural split points
                    split_words = ["but", "and", "while", "because",
                                   "however", "although", "which",
                                   "where", "when", "—", ";", "that"]
                    split_point = None
                    for sw in split_words:
                        positions = [i for i, w in enumerate(words)
                                     if w.lower().strip(",.;:") == sw and 10 < i < len(words) - 5]
                        if positions:
                            # Pick the split closest to the middle
                            mid = len(words) // 2
                            split_point = min(positions, key=lambda p: abs(p - mid))
                            break

                    if split_point:
                        part1 = " ".join(words[:split_point]).rstrip(",;")  + "."
                        connector = words[split_point].strip(",.;:")
                        part2 = " ".join(words[split_point + 1:])
                        if part2:
                            part2 = part2[0].upper() + part2[1:]
                        replacement = f"{part1} {part2}"
                    else:
                        replacement = f"[Split this {len(words)}-word sentence into two shorter ones at a natural break point]"

                    original = sent[:200] + ("..." if len(sent) > 200 else "")
                    line_num = self._find_line_num(f.read_text(), sent[:50])
                    self._add_fix(
                        "Long Sentences", "MINOR", f.name, str(f), line_num,
                        "", original, replacement,
                        f"Split {len(words)}-word sentence for readability (target: <35 words)"
                    )

    def fix_passive_voice(self):
        """Find passive voice and suggest active alternatives."""
        for f in self.chapter_files:
            text = f.read_text()
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    text_body = text[end + 3:]
                else:
                    text_body = text
            else:
                text_body = text

            # Clean for sentence splitting
            clean = re.sub(r"```.*?```", "", text_body, flags=re.DOTALL)
            clean = re.sub(r"\|.*\|", "", clean)
            clean = re.sub(r"^>.*$", "", clean, flags=re.MULTILINE)

            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', clean)
            passive_count = 0

            for sent in sentences:
                if len(sent.split()) < 4:
                    continue
                # Check for passive constructions
                passive_match = re.search(
                    r"\b(is|are|was|were|been|being|be)\s+(?:\w+ly\s+)?(\w+(?:ed|en|t|wn|ng))\b",
                    sent, re.IGNORECASE
                )
                if passive_match:
                    passive_count += 1
                    if passive_count <= 5:  # Limit per chapter
                        original = sent.strip()[:200]
                        aux = passive_match.group(1)
                        verb = passive_match.group(2)
                        line_num = self._find_line_num(f.read_text(), sent[:40])
                        self._add_fix(
                            "Passive Voice", "MINOR", f.name, str(f), line_num,
                            "", original,
                            f'[Rewrite in active voice: identify who "{aux} {verb}" and make them the subject]',
                            f"Passive construction: '{aux} {verb}' — flip to active voice"
                        )

    def fix_missing_timeframes(self):
        """Add time frame suggestions to action items without them."""
        for f in self.chapter_files:
            text = f.read_text()
            # Find action item sections
            sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
            for section in sections:
                heading = section.split("\n")[0].lower()
                if any(kw in heading for kw in ["action", "monday", "morning",
                                                 "getting started", "your first"]):
                    # Check if it already has a timeframe
                    has_time = bool(re.search(
                        r"\b(?:this week|monday|tomorrow|today|30 minutes|"
                        r"one hour|next meeting|right now|immediately|"
                        r"before (?:your|the) next)\b",
                        section, re.IGNORECASE
                    ))
                    if not has_time:
                        first_line = section.split("\n\n")[1] if "\n\n" in section else section[:200]
                        line_num = self._find_line_num(text, heading)
                        self._add_fix(
                            "Missing Time Frame", "MINOR", f.name, str(f), line_num,
                            first_line[:200],
                            "[No time frame specified]",
                            "Add one of:\n" + "\n".join(TIME_FRAME_TEMPLATES),
                            "Action items need urgency — tell the reader WHEN to do it"
                        )

    def fix_hook_variety(self):
        """Suggest story-based hooks for chapters using weak hook types."""
        for f in self.chapter_files:
            text = f.read_text()
            # Strip YAML
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    text = text[end + 3:]

            # Strip comments
            text = re.sub(r"<!--.*?-->", "", text).strip()

            # Get first section (before second ## heading)
            parts = re.split(r"^##\s+", text, flags=re.MULTILINE)
            if len(parts) < 2:
                continue

            # parts[0] has the # title, parts[1] is the hook section
            hook_heading = parts[1].split("\n")[0]
            hook_body = "\n".join(parts[1].split("\n")[1:]).strip()
            first_para = hook_body.split("\n\n")[0] if hook_body else ""

            # Check if it's a story (has a named character)
            has_name = bool(re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", first_para))
            if not has_name and first_para:
                line_num = self._find_line_num(f.read_text(), hook_heading)
                self._add_fix(
                    "Hook Variety", "MINOR", f.name, str(f), line_num,
                    first_para[:300],
                    "[Hook opens with scenario/statement instead of named story]",
                    HOOK_STORY_TEMPLATE,
                    "Story hooks with named characters are 3x more engaging than generic scenarios"
                )

    def fix_segment_gaps(self):
        """Identify chapters missing reader segments and provide templates."""
        segment_keywords = {
            "Department Head": [r"\bmanager\b", r"\bdirector\b", r"\bteam lead\b",
                                r"\bdepartment\b", r"\bher team\b", r"\bhis team\b"],
            "Individual Contributor": [r"\bindividual contributor\b", r"\bIC\b",
                                       r"\bpersonal productivity\b", r"\bknowledge worker\b"],
            "Small Company CEO": [r"\bsmall (?:company|business)\b", r"\bfounder\b",
                                   r"\bowner\b", r"\bagency\b", r"\b\d+-person\b"],
            "Senior Leader": [r"\bVP\b", r"\bvice president\b", r"\bC-suite\b",
                              r"\bCEO\b", r"\bCOO\b", r"\bCRO\b", r"\bexecutive\b"],
        }

        templates = {
            "Department Head": (
                "**For Department Heads:**\n"
                "[Name], who manages [team] at [company type], applied this by "
                "[specific action]. Within [timeframe], the team saw [specific result]. "
                "The key for managers: [insight specific to managing teams]."
            ),
            "Individual Contributor": (
                "**For Individual Contributors:**\n"
                "If you're applying this to your own work, start with [specific task]. "
                "[Name], a [role] at [company], used this approach to cut [task] from "
                "[old time] to [new time]. No team buy-in required — this is about your "
                "personal workflow."
            ),
            "Small Company CEO": (
                "**For Small Company CEOs:**\n"
                "[Name] runs a [number]-person [industry] firm. With no AI team and "
                "limited budget, [he/she] adapted this by [simplified approach]. "
                "The advantage for small companies: [unique benefit — speed, simplicity, "
                "direct control]."
            ),
            "Senior Leader": (
                "**For Senior Leaders:**\n"
                "At the organizational level, this becomes a [strategic consideration]. "
                "[Name], VP of [function] at [company], used this framework to "
                "[strategic action]. The executive lens: [how this scales and "
                "what policy implications exist]."
            ),
        }

        for f in self.chapter_files:
            text = f.read_text()
            for segment, keywords in segment_keywords.items():
                count = sum(len(re.findall(kw, text, re.IGNORECASE)) for kw in keywords)
                if count == 0:
                    line_num = len(text.split("\n")) - 10  # Near end of chapter
                    self._add_fix(
                        "Segment Coverage", "MINOR", f.name, str(f), line_num,
                        f"[No {segment} examples found in this chapter]",
                        f"[Missing {segment} perspective]",
                        templates[segment],
                        f"Add a {segment} example to this chapter's Applications section"
                    )

    # ── Run All Fixes ───────────────────────────────────────────────────

    def run(self):
        self.fix_guru_speak()
        self.fix_filler_phrases()
        self.fix_textbook_voice()
        self.fix_hedging()
        self.fix_vague_sources()
        self.fix_long_sentences()
        self.fix_passive_voice()
        self.fix_missing_timeframes()
        self.fix_hook_variety()
        self.fix_segment_gaps()

    # ── HTML Report ─────────────────────────────────────────────────────

    def generate_html(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total_words = 0
        for f in self.chapter_files:
            text = f.read_text()
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    text = text[end + 3:]
            total_words += len(text.split())

        # Group fixes by category
        by_category = defaultdict(list)
        for fix in self.fixes:
            by_category[fix.category].append(fix)

        # Group fixes by chapter
        by_chapter = defaultdict(list)
        for fix in self.fixes:
            by_chapter[fix.chapter].append(fix)

        # Severity counts
        sev_counts = Counter(f.severity for f in self.fixes)

        # Category priority order
        cat_order = ["Guru-Speak", "Vague Sources", "Textbook Voice",
                     "Filler Phrases", "Hedging Language", "Long Sentences",
                     "Passive Voice", "Missing Time Frame", "Hook Variety",
                     "Segment Coverage"]

        html_parts = []
        html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Editorial Fixes — {self.project_path.name}</title>
<style>
:root {{
    --bg: #fafaf9;
    --card: #ffffff;
    --border: #e7e5e4;
    --text: #1c1917;
    --muted: #78716c;
    --red: #dc2626;
    --red-bg: #fef2f2;
    --red-border: #fecaca;
    --amber: #d97706;
    --amber-bg: #fffbeb;
    --amber-border: #fde68a;
    --green: #16a34a;
    --green-bg: #f0fdf4;
    --green-border: #bbf7d0;
    --blue: #2563eb;
    --blue-bg: #eff6ff;
    --blue-border: #bfdbfe;
    --purple: #7c3aed;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
    max-width: 1100px;
    margin: 0 auto;
}}
h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; }}
h2 {{ font-size: 1.35rem; font-weight: 600; margin: 2rem 0 1rem; border-bottom: 2px solid var(--border); padding-bottom: 0.5rem; }}
h3 {{ font-size: 1.1rem; font-weight: 600; margin: 1.5rem 0 0.75rem; }}
.subtitle {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 1.5rem; }}
.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}}
.stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}}
.stat-num {{ font-size: 1.8rem; font-weight: 700; }}
.stat-label {{ font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }}
.stat-major .stat-num {{ color: var(--red); }}
.stat-minor .stat-num {{ color: var(--amber); }}
.stat-good .stat-num {{ color: var(--green); }}
.toc {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 2rem;
}}
.toc h3 {{ margin-top: 0; }}
.toc ul {{ list-style: none; padding: 0; }}
.toc li {{ padding: 0.25rem 0; }}
.toc a {{ color: var(--blue); text-decoration: none; }}
.toc a:hover {{ text-decoration: underline; }}
.toc .count {{ color: var(--muted); font-size: 0.85rem; }}
.fix-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    position: relative;
}}
.fix-card.severity-MAJOR {{ border-left: 4px solid var(--red); }}
.fix-card.severity-MINOR {{ border-left: 4px solid var(--amber); }}
.fix-card.severity-INFO {{ border-left: 4px solid var(--blue); }}
.fix-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
    gap: 0.5rem;
}}
.fix-location {{
    font-size: 0.8rem;
    color: var(--muted);
    font-family: 'SF Mono', Consolas, monospace;
}}
.badge {{
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}}
.badge-major {{ background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }}
.badge-minor {{ background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }}
.badge-info {{ background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue-border); }}
.before-after {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin: 0.75rem 0;
}}
@media (max-width: 700px) {{
    .before-after {{ grid-template-columns: 1fr; }}
}}
.before, .after {{
    border-radius: 6px;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}}
.before {{
    background: var(--red-bg);
    border: 1px solid var(--red-border);
}}
.after {{
    background: var(--green-bg);
    border: 1px solid var(--green-border);
}}
.before-label, .after-label {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
}}
.before-label {{ color: var(--red); }}
.after-label {{ color: var(--green); }}
.explanation {{
    font-size: 0.85rem;
    color: var(--muted);
    margin-top: 0.5rem;
    font-style: italic;
}}
.context {{
    font-size: 0.8rem;
    color: var(--muted);
    background: #f5f5f4;
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.75rem;
    font-family: 'SF Mono', Consolas, monospace;
    white-space: pre-wrap;
    word-break: break-word;
}}
.chapter-nav {{
    position: sticky;
    top: 0;
    background: var(--bg);
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    z-index: 10;
    margin-bottom: 1rem;
}}
.chapter-nav select {{
    font-size: 0.9rem;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--card);
}}
footer {{
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.8rem;
    text-align: center;
}}
</style>
</head>
<body>

<h1>Editorial Fix Report</h1>
<p class="subtitle">
    {self.project_path.name} &mdash; {len(self.chapter_files)} chapters &mdash;
    {total_words:,} words &mdash; Generated {now}
</p>

<div class="stats">
    <div class="stat-card stat-major">
        <div class="stat-num">{sev_counts.get('MAJOR', 0)}</div>
        <div class="stat-label">Major Fixes</div>
    </div>
    <div class="stat-card stat-minor">
        <div class="stat-num">{sev_counts.get('MINOR', 0)}</div>
        <div class="stat-label">Minor Fixes</div>
    </div>
    <div class="stat-card stat-good">
        <div class="stat-num">{len(self.fixes)}</div>
        <div class="stat-label">Total Fixes</div>
    </div>
    <div class="stat-card">
        <div class="stat-num">{len(by_category)}</div>
        <div class="stat-label">Categories</div>
    </div>
    <div class="stat-card">
        <div class="stat-num">{len(by_chapter)}</div>
        <div class="stat-label">Chapters Affected</div>
    </div>
</div>
""")

        # Table of contents
        html_parts.append('<div class="toc"><h3>Fix Categories</h3><ul>')
        for cat in cat_order:
            if cat in by_category:
                fixes = by_category[cat]
                majors = sum(1 for f in fixes if f.severity == "MAJOR")
                label = f' <span class="count">({len(fixes)} fixes'
                if majors:
                    label += f", {majors} major"
                label += ")</span>"
                html_parts.append(
                    f'<li><a href="#{cat.lower().replace(" ", "-")}">{cat}</a>{label}</li>'
                )
        html_parts.append("</ul></div>")

        # Fixes by category
        for cat in cat_order:
            if cat not in by_category:
                continue
            fixes = by_category[cat]
            anchor = cat.lower().replace(" ", "-")
            html_parts.append(f'<h2 id="{anchor}">{cat} ({len(fixes)} fixes)</h2>')

            # Group by chapter within category
            by_ch = defaultdict(list)
            for fix in fixes:
                by_ch[fix.chapter].append(fix)

            for ch_name, ch_fixes in sorted(by_ch.items()):
                html_parts.append(f"<h3>{ch_name} ({len(ch_fixes)})</h3>")
                for fix in ch_fixes:
                    sev_class = fix.severity.lower()
                    html_parts.append(f'<div class="fix-card severity-{fix.severity}">')
                    html_parts.append(f'<div class="fix-header">')
                    html_parts.append(f'<span class="badge badge-{sev_class}">{fix.severity}</span>')
                    html_parts.append(f'<span class="fix-location">Line {fix.line_num}</span>')
                    html_parts.append(f'</div>')

                    if fix.context_before:
                        html_parts.append(
                            f'<div class="context">{html.escape(fix.context_before)}</div>'
                        )

                    html_parts.append('<div class="before-after">')
                    html_parts.append('<div>')
                    html_parts.append('<div class="before-label">Before</div>')
                    html_parts.append(f'<div class="before">{html.escape(fix.original)}</div>')
                    html_parts.append('</div>')
                    html_parts.append('<div>')
                    html_parts.append('<div class="after-label">After</div>')
                    html_parts.append(f'<div class="after">{html.escape(fix.replacement)}</div>')
                    html_parts.append('</div>')
                    html_parts.append('</div>')

                    html_parts.append(
                        f'<div class="explanation">{html.escape(fix.explanation)}</div>'
                    )
                    html_parts.append('</div>')

        # Chapter summary
        html_parts.append("<h2>Fixes by Chapter</h2>")
        html_parts.append("""
<table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
<tr style="border-bottom:2px solid var(--border);">
    <th style="text-align:left; padding:0.5rem;">Chapter</th>
    <th style="text-align:center; padding:0.5rem;">Total</th>
    <th style="text-align:center; padding:0.5rem;">Major</th>
    <th style="text-align:center; padding:0.5rem;">Minor</th>
</tr>
""")
        for ch_name in sorted(by_chapter.keys()):
            fixes = by_chapter[ch_name]
            majors = sum(1 for f in fixes if f.severity == "MAJOR")
            minors = sum(1 for f in fixes if f.severity == "MINOR")
            row_style = ' style="background:var(--red-bg);"' if majors > 3 else ""
            html_parts.append(
                f'<tr{row_style}>'
                f'<td style="padding:0.4rem 0.5rem;">{html.escape(ch_name)}</td>'
                f'<td style="text-align:center; padding:0.4rem;">{len(fixes)}</td>'
                f'<td style="text-align:center; padding:0.4rem; color:var(--red);">'
                f'{majors if majors else "-"}</td>'
                f'<td style="text-align:center; padding:0.4rem; color:var(--amber);">'
                f'{minors if minors else "-"}</td></tr>'
            )
        html_parts.append("</table>")

        html_parts.append(f"""
<footer>
    Generated by claude-book-publisher editorial v{VERSION}<br>
    {len(self.fixes)} fixes across {len(by_chapter)} chapters &mdash; {now}
</footer>
</body>
</html>""")

        return "\n".join(html_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Generate editorial fixes with replacement text"
    )
    parser.add_argument("project_path", help="Path to book project")
    parser.add_argument("--output", default="editorial-fixes.html",
                        help="Output HTML file (default: editorial-fixes.html)")
    parser.add_argument("--chapter", help="Only analyze chapters matching this string")

    args = parser.parse_args()

    if not os.path.isdir(args.project_path):
        print(f"Error: {args.project_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    fixer = EditorialFixer(args.project_path, chapter_filter=args.chapter)
    fixer.run()

    html_report = fixer.generate_html()
    output_path = Path(args.project_path) / args.output
    output_path.write_text(html_report)

    print(f"Editorial fix report: {output_path}", file=sys.stderr)
    print(f"  {len(fixer.fixes)} fixes across {len(fixer.stats)} categories", file=sys.stderr)
    for cat, count in sorted(fixer.stats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()

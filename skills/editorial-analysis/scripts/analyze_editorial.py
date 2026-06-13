#!/usr/bin/env python3
"""
Editorial Analysis for Nonfiction Business Books

Analyzes manuscript content quality: voice, structure, narrative flow,
reader engagement, authority, and repetition. Designed for reuse across
any nonfiction business book manuscript.

Usage:
    python3 analyze_editorial.py path/to/project
    python3 analyze_editorial.py --category voice path/to/project
    python3 analyze_editorial.py --chapter ch01 path/to/project
"""

import argparse
import hashlib
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


VERSION = "0.1.0"


# ── Patterns ────────────────────────────────────────────────────────────

PASSIVE_PATTERNS = [
    r"\b(?:is|are|was|were|been|being|be)\s+(?:\w+ly\s+)?(?:\w+ed|built|chosen|done|driven|felt|found|given|gone|grown|held|hit|kept|known|led|lost|made|met|paid|put|read|run|said|seen|sent|set|shown|spoken|spent|stood|taken|thought|told|understood|won|written|broken|chosen|forgotten|frozen|hidden|ridden|risen|stolen|sworn|torn|woken|worn)\b",
]

HEDGING_WORDS = [
    r"\bperhaps\b", r"\bmaybe\b", r"\bmight\b", r"\bcould possibly\b",
    r"\bsomewhat\b", r"\barguably\b", r"\bto some extent\b",
    r"\bit seems\b", r"\bappears to\b", r"\btends to\b",
    r"\bin my opinion\b", r"\bi think that\b", r"\bi believe that\b",
    r"\bi feel that\b", r"\bkind of\b", r"\bsort of\b",
    r"\bmore or less\b", r"\bfor the most part\b",
]

GURU_SPEAK = [
    r"\bunlock(?:ing)?\s+(?:your|the|their)\b", r"\bunleash\b",
    r"\btransformative\b", r"\bparadigm\s+shift\b",
    r"\bgame[- ]?changer\b", r"\bsynergy\b", r"\bsynergies\b",
    r"\bleverage\b(?!\s+ratio)", r"\bdisruptive\b", r"\bdisrupt\b",
    r"\bempower(?:ing|ment|ed)?\b", r"\bsupercharge\b",
    r"\bscale\b.*\b10x\b", r"\bexponential(?:ly)?\b",
    r"\brevolutionize\b", r"\bnext[- ]?level\b",
    r"\bmove the needle\b", r"\bboil the ocean\b",
]

FILLER_PHRASES = [
    r"it'?s important to note that",
    r"at the end of the day",
    r"the reality is that",
    r"let'?s be honest",
    r"here'?s the thing",
    r"the fact of the matter is",
    r"it goes without saying",
    r"needless to say",
    r"in order to",
    r"the bottom line is",
    r"when all is said and done",
    r"as a matter of fact",
    r"it should be noted that",
    r"it is worth mentioning that",
]

TEXTBOOK_VOICE = [
    r"in this chapter,?\s+we (?:will|shall|are going to)\b",
    r"as (?:previously|earlier) mentioned",
    r"the reader should (?:note|be aware)\b",
    r"it can be concluded that",
    r"this (?:chapter|section) (?:will )?(?:discuss|explore|examine|cover)s?\b",
    r"in (?:the following|this) section",
    r"as we (?:shall|will) see",
    r"the (?:above|following) (?:table|figure|example)\b",
]

VAGUE_SOURCING = [
    r"research (?:shows|suggests|indicates|has shown)\b",
    r"studies (?:show|suggest|indicate|have shown)\b",
    r"experts (?:say|agree|believe|recommend)\b",
    r"according to (?:some|many|most|several)\b",
    r"it has been (?:shown|proven|demonstrated)\b",
    r"data (?:shows|suggests|indicates)\b",
]

# Reader segment keywords
SEGMENT_KEYWORDS = {
    "Department Head": [
        r"\bmanager\b", r"\bdirector\b", r"\bteam lead\b", r"\bdepartment\b",
        r"\bteam\s+of\b", r"\bmanage[sd]?\s+(?:a\s+)?team\b", r"\bher team\b",
        r"\bhis team\b", r"\bops director\b", r"\bmarketing head\b",
        r"\bcustomer (?:service|success)\s+(?:manager|director|lead)\b",
    ],
    "Individual Contributor": [
        r"\bindividual contributor\b", r"\bIC\b", r"\bpersonal productivity\b",
        r"\byour own work\b", r"\bknowledge worker\b", r"\banalyst\b",
        r"\byour daily\b", r"\byour workflow\b", r"\bpersonal\s+(?:system|prompt)\b",
    ],
    "Small Company CEO": [
        r"\bsmall (?:company|business)\b", r"\bfounder\b", r"\bowner\b",
        r"\bstartup\b", r"\bentrepreneur\b", r"\b\d+-person\b",
        r"\b(?:5|10|15|20|25|30|35|40|45|50)[- ]employee\b",
        r"\bindependently\b", r"\bwears? many hats\b",
        r"\bagency owner\b", r"\bfirm owner\b",
    ],
    "Senior Leader": [
        r"\bVP\b", r"\bvice president\b", r"\bC-suite\b", r"\bCEO\b",
        r"\bCOO\b", r"\bCFO\b", r"\bCTO\b", r"\bCRO\b", r"\bCMO\b",
        r"\bchief\b", r"\bsenior leader\b", r"\bexecutive\b",
        r"\bboard\b", r"\bstrategic\b", r"\borganizational\b",
    ],
}

ACTION_VERBS = [
    "create", "write", "list", "schedule", "open", "send", "build",
    "document", "score", "map", "identify", "draft", "review", "test",
    "start", "set up", "define", "pick", "choose", "add", "remove",
    "install", "configure", "paste", "copy", "save", "measure",
]


class Finding:
    def __init__(self, finding_id, severity, category, title, location,
                 description, fix, impact=""):
        self.finding_id = finding_id
        self.severity = severity
        self.category = category
        self.title = title
        self.location = location
        self.description = description
        self.fix = fix
        self.impact = impact


class Chapter:
    """Parsed chapter with metadata and content sections."""

    def __init__(self, path: Path, project_path: Path):
        self.path = path
        self.name = path.name
        self.rel_path = str(path.relative_to(project_path))
        raw = path.read_text()

        # Strip YAML front matter
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                raw = raw[end + 3:]

        # Extract HTML comments (status, word count, etc.)
        self.comments = re.findall(r"<!--\s*(.*?)\s*-->", raw)
        self.raw_text = re.sub(r"<!--.*?-->", "", raw).strip()

        # Parse sections by ## headings
        self.title = ""
        self.sections = []
        self._parse_sections()

        # Content metrics
        self.sentences = self._split_sentences(self.body_text)
        self.words = self.body_text.split()
        self.word_count = len(self.words)
        self.paragraphs = [p.strip() for p in self.body_text.split("\n\n") if p.strip()]

    def _parse_sections(self):
        lines = self.raw_text.split("\n")
        current_heading = None
        current_content = []

        for line in lines:
            h1 = re.match(r"^#\s+(.+?)(?:\s*\{.*\})?\s*$", line)
            h2 = re.match(r"^##\s+(.+?)(?:\s*\{.*\})?\s*$", line)

            if h1 and not self.title:
                self.title = h1.group(1).strip()
                continue

            if h2:
                if current_heading is not None:
                    self.sections.append((current_heading, "\n".join(current_content).strip()))
                current_heading = h2.group(1).strip()
                current_content = []
            else:
                current_content.append(line)

        if current_heading is not None:
            self.sections.append((current_heading, "\n".join(current_content).strip()))

    @property
    def body_text(self) -> str:
        """All section content joined."""
        return "\n\n".join(content for _, content in self.sections)

    @property
    def hook_text(self) -> str:
        """First section content (the hook)."""
        if self.sections:
            return self.sections[0][1]
        return ""

    @property
    def section_headings(self) -> list[str]:
        return [h for h, _ in self.sections]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        # Remove markdown formatting
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
        clean = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", clean)  # bold/italic
        clean = re.sub(r"^#+\s+.*$", "", clean, flags=re.MULTILINE)  # headings
        clean = re.sub(r"^[-*]\s+", "", clean, flags=re.MULTILINE)  # list items
        clean = re.sub(r"^\d+\.\s+", "", clean, flags=re.MULTILINE)  # numbered list
        clean = re.sub(r"^>.*$", "", clean, flags=re.MULTILINE)  # blockquotes
        clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)  # code blocks
        clean = re.sub(r"`[^`]+`", "", clean)  # inline code
        clean = re.sub(r"\|.*\|", "", clean)  # table rows

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', clean)
        return [s.strip() for s in sentences if s.strip() and len(s.split()) > 2]


class EditorialAnalyzer:
    """Analyzes nonfiction business book content quality."""

    def __init__(self, project_path: str, category: str = None,
                 chapter_filter: str = None):
        self.project_path = Path(project_path)
        self.category = category
        self.chapter_filter = chapter_filter
        self.findings: list[Finding] = []
        self.checks_run = 0
        self.checks_failed = 0
        self.category_stats: dict[str, dict[str, int]] = {}
        self.chapters: list[Chapter] = []

        self._load_chapters()

    def _load_chapters(self):
        """Load and parse all chapter files."""
        excluded = {".worktrees", "_output", "_site", "_book", ".git", "node_modules"}
        for f in sorted(self.project_path.rglob("chapters/**/*.qmd")):
            parts = f.relative_to(self.project_path).parts
            if any(p in excluded or p.startswith(".") for p in parts):
                continue
            if self.chapter_filter and self.chapter_filter not in f.name:
                continue
            ch = Chapter(f, self.project_path)
            if ch.word_count > 200:  # Skip stubs
                self.chapters.append(ch)

    def _record(self, category: str, passed: bool, finding: Finding = None):
        self.checks_run += 1
        if category not in self.category_stats:
            self.category_stats[category] = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}

        if finding:
            self.findings.append(finding)
            if finding.severity in ("CRITICAL", "MAJOR"):
                self.checks_failed += 1
                self.category_stats[category]["fail"] += 1
            elif finding.severity == "MINOR":
                self.category_stats[category]["warn"] += 1
            else:
                self.category_stats[category]["pass"] += 1
        elif passed:
            self.category_stats[category]["pass"] += 1
        else:
            self.category_stats[category]["fail"] += 1

    # ── Category 1: Chapter Structure ───────────────────────────────────

    def check_chapter_structure(self):
        cat = "Chapter Structure"
        if not self.chapters:
            return

        expected_sections = {
            "hook": ["hook", "the"],
            "framework": ["framework", "main", "core", "model", "system", "approach",
                          "problem", "failure", "why", "how", "what", "cold start",
                          "components", "building", "using", "five"],
            "applications": ["application", "example", "practice", "role", "across",
                             "paths", "two paths", "master prompt"],
            "objections": ["objection", "but what", "common"],
            "action": ["action", "monday", "morning", "your", "step", "getting started",
                       "foundation", "first"],
        }

        for ch in self.chapters:
            headings_lower = [h.lower() for h in ch.section_headings]

            # Check for key sections
            has_hook = len(ch.sections) > 0  # First section is always the hook
            has_objections = any(
                any(kw in h for kw in expected_sections["objections"])
                for h in headings_lower
            )
            has_action = any(
                any(kw in h for kw in expected_sections["action"])
                for h in headings_lower
            )

            if not has_objections:
                self._record(cat, False, Finding(
                    "STR-001", "MINOR", cat,
                    f"No 'Common Objections' section: {ch.name}",
                    ch.rel_path,
                    f"Chapter '{ch.title}' has no objection-handling section",
                    "Add a 'Common Objections' section addressing reader resistance",
                ))

            if not has_action:
                self._record(cat, False, Finding(
                    "STR-002", "MAJOR", cat,
                    f"No action item section: {ch.name}",
                    ch.rel_path,
                    f"Chapter '{ch.title}' has no Monday Morning Action Item",
                    "Add a concrete action item section at the end of the chapter",
                ))

            # Check section count (too few = underdeveloped, too many = unfocused)
            if len(ch.sections) < 3:
                self._record(cat, False, Finding(
                    "STR-003", "MAJOR", cat,
                    f"Too few sections ({len(ch.sections)}): {ch.name}",
                    ch.rel_path,
                    f"Chapter has only {len(ch.sections)} sections. Target: 4-7",
                    "Add more sections to develop the chapter fully",
                ))
            elif len(ch.sections) > 10:
                self._record(cat, False, Finding(
                    "STR-004", "MINOR", cat,
                    f"Many sections ({len(ch.sections)}): {ch.name}",
                    ch.rel_path,
                    f"Chapter has {len(ch.sections)} sections. May feel fragmented",
                    "Consider consolidating related sections",
                ))
            else:
                self._record(cat, True)

    # ── Category 2: Voice & Style ───────────────────────────────────────

    def check_voice_style(self):
        cat = "Voice & Style"
        if not self.chapters:
            return

        all_guru = []
        all_filler = []
        all_textbook = []

        for ch in self.chapters:
            if not ch.sentences:
                continue

            # Passive voice
            passive_count = 0
            for sent in ch.sentences:
                for pat in PASSIVE_PATTERNS:
                    if re.search(pat, sent, re.IGNORECASE):
                        passive_count += 1
                        break
            pct = passive_count / len(ch.sentences) * 100

            if pct > 25:
                self._record(cat, False, Finding(
                    "VOI-001", "MAJOR", cat,
                    f"High passive voice ({pct:.0f}%): {ch.name}",
                    ch.rel_path,
                    f"{passive_count}/{len(ch.sentences)} sentences use passive voice ({pct:.0f}%). Target: <15%",
                    "Rewrite passive constructions to active voice",
                ))
            elif pct > 15:
                self._record(cat, False, Finding(
                    "VOI-001", "MINOR", cat,
                    f"Moderate passive voice ({pct:.0f}%): {ch.name}",
                    ch.rel_path,
                    f"{passive_count}/{len(ch.sentences)} sentences use passive voice ({pct:.0f}%). Target: <15%",
                    "Review passive constructions — some may be intentional",
                ))
            else:
                self._record(cat, True)

            # Hedging
            hedge_count = sum(
                1 for sent in ch.sentences
                for pat in HEDGING_WORDS
                if re.search(pat, sent, re.IGNORECASE)
            )
            hedge_pct = hedge_count / len(ch.sentences) * 100
            if hedge_pct > 10:
                self._record(cat, False, Finding(
                    "VOI-002", "MINOR", cat,
                    f"Hedging language ({hedge_pct:.0f}%): {ch.name}",
                    ch.rel_path,
                    f"{hedge_count} hedging phrases found. Target: <10%",
                    "Replace hedging words with direct statements",
                ))
            else:
                self._record(cat, True)

            # Guru-speak
            for pat in GURU_SPEAK:
                matches = re.findall(pat, ch.body_text, re.IGNORECASE)
                for m in matches:
                    all_guru.append((ch.name, m))

            # Filler phrases
            for pat in FILLER_PHRASES:
                matches = re.findall(pat, ch.body_text, re.IGNORECASE)
                for m in matches:
                    all_filler.append((ch.name, m))

            # Textbook voice
            for pat in TEXTBOOK_VOICE:
                matches = re.findall(pat, ch.body_text, re.IGNORECASE)
                for m in matches:
                    all_textbook.append((ch.name, m))

            # Sentence length variety
            lengths = [len(s.split()) for s in ch.sentences]
            if lengths:
                avg_len = sum(lengths) / len(lengths)
                std_dev = math.sqrt(sum((l - avg_len) ** 2 for l in lengths) / len(lengths))
                coeff_var = std_dev / avg_len if avg_len > 0 else 0

                too_long = [l for l in lengths if l > 35]
                if too_long:
                    self._record(cat, False, Finding(
                        "VOI-005", "MINOR", cat,
                        f"{len(too_long)} sentences over 35 words: {ch.name}",
                        ch.rel_path,
                        f"Found {len(too_long)} sentences exceeding 35 words (avg: {avg_len:.0f})",
                        "Split long sentences for readability",
                    ))

                if coeff_var < 0.25:
                    self._record(cat, False, Finding(
                        "VOI-006", "MINOR", cat,
                        f"Low sentence variety (CV={coeff_var:.2f}): {ch.name}",
                        ch.rel_path,
                        f"Sentence lengths are too uniform (CV={coeff_var:.2f}). Target: >0.30",
                        "Mix short punchy sentences with longer explanatory ones",
                    ))
                else:
                    self._record(cat, True)

        # Report guru-speak across book
        if all_guru:
            instances = "; ".join(f"{ch}: '{m}'" for ch, m in all_guru[:10])
            self._record(cat, False, Finding(
                "VOI-003", "MAJOR", cat,
                f"{len(all_guru)} guru-speak instances found",
                "Multiple chapters",
                f"Found {len(all_guru)} buzzword/guru-speak instances: {instances}",
                "Replace with concrete, specific language",
            ))
        else:
            self._record(cat, True)

        # Report filler phrases
        if all_filler:
            instances = "; ".join(f"{ch}: '{m}'" for ch, m in all_filler[:10])
            self._record(cat, False, Finding(
                "VOI-004", "MINOR", cat,
                f"{len(all_filler)} filler phrases found",
                "Multiple chapters",
                f"Found {len(all_filler)} filler phrases: {instances}",
                "Delete filler phrases — they add no meaning",
            ))
        else:
            self._record(cat, True)

        # Report textbook voice
        if all_textbook:
            instances = "; ".join(f"{ch}: '{m}'" for ch, m in all_textbook[:10])
            self._record(cat, False, Finding(
                "VOI-007", "MINOR", cat,
                f"{len(all_textbook)} textbook-voice phrases found",
                "Multiple chapters",
                f"Found {len(all_textbook)} textbook-style phrases: {instances}",
                "Rewrite in conversational voice — readers aren't students",
            ))
        else:
            self._record(cat, True)

    # ── Category 3: Hook Quality ────────────────────────────────────────

    def check_hooks(self):
        cat = "Hook Quality"
        if not self.chapters:
            return

        hook_types = Counter()

        for ch in self.chapters:
            hook = ch.hook_text
            if not hook:
                self._record(cat, False, Finding(
                    "HOK-001", "CRITICAL", cat,
                    f"No hook/opening section: {ch.name}",
                    ch.rel_path,
                    "Chapter has no opening content before the first heading",
                    "Add an engaging opening story, statistic, or scenario",
                ))
                continue

            hook_words = hook.split()
            first_para = hook.split("\n\n")[0] if hook else ""
            first_sent_words = len(first_para.split(".")[0].split()) if first_para else 0

            # Classify hook type
            has_name = bool(re.search(
                r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", first_para
            ))
            has_number = bool(re.search(r"\b\d+[%,.]?\d*\b", first_para))
            starts_question = first_para.strip().endswith("?") if first_para else False
            starts_definition = bool(re.match(r"^[A-Z]\w+\s+(?:is|are|means)\b", first_para))

            if has_name and not starts_question:
                hook_type = "Story"
            elif has_number:
                hook_type = "Statistic"
            elif starts_question:
                hook_type = "Question"
            elif starts_definition:
                hook_type = "Definition"
            else:
                hook_type = "Scenario"

            hook_types[hook_type] += 1

            # Flag weak hook types
            if hook_type == "Definition":
                self._record(cat, False, Finding(
                    "HOK-002", "MAJOR", cat,
                    f"Weak hook type (Definition): {ch.name}",
                    ch.rel_path,
                    "Chapter opens with a definition — weakest hook type for engagement",
                    "Replace with a story, surprising statistic, or provocative statement",
                ))
            elif hook_type == "Question" and starts_question:
                self._record(cat, False, Finding(
                    "HOK-003", "MINOR", cat,
                    f"Question hook (common, not distinctive): {ch.name}",
                    ch.rel_path,
                    "Opening with a question works but is overused in business books",
                    "Consider leading with a story or statistic instead",
                ))
            else:
                self._record(cat, True)

            # Hook length
            if len(hook_words) < 100:
                self._record(cat, False, Finding(
                    "HOK-004", "MINOR", cat,
                    f"Short hook ({len(hook_words)} words): {ch.name}",
                    ch.rel_path,
                    f"Hook is only {len(hook_words)} words. Target: 200-300",
                    "Expand the opening with more detail, stakes, or context",
                ))
            else:
                self._record(cat, True)

        # Report hook type distribution
        if hook_types:
            dist = ", ".join(f"{t}: {c}" for t, c in hook_types.most_common())
            self._record(cat, True, Finding(
                "HOK-INFO", "INFO", cat,
                f"Hook type distribution across {len(self.chapters)} chapters",
                "All chapters",
                f"Hook types: {dist}",
                "Aim for variety — too many of the same type feels repetitive",
            ))

    # ── Category 4: Reader Segments ─────────────────────────────────────

    def check_reader_segments(self):
        cat = "Reader Segments"
        if not self.chapters:
            return

        book_segments = Counter()
        chapters_missing = defaultdict(list)

        for ch in self.chapters:
            ch_segments = {}
            for segment, keywords in SEGMENT_KEYWORDS.items():
                count = sum(
                    len(re.findall(kw, ch.body_text, re.IGNORECASE))
                    for kw in keywords
                )
                ch_segments[segment] = count
                book_segments[segment] += count

            # Flag chapters with zero coverage for any segment
            for segment, count in ch_segments.items():
                if count == 0:
                    chapters_missing[segment].append(ch.name)

        # Report missing segments
        for segment, chapters in chapters_missing.items():
            if len(chapters) > len(self.chapters) * 0.5:
                self._record(cat, False, Finding(
                    "SEG-001", "MAJOR", cat,
                    f"'{segment}' underrepresented ({len(chapters)} chapters with no mention)",
                    "Multiple chapters",
                    f"Chapters with no {segment} references: {', '.join(chapters[:8])}{'...' if len(chapters) > 8 else ''}",
                    f"Add {segment} examples or context to underrepresented chapters",
                ))
            elif len(chapters) > 3:
                self._record(cat, False, Finding(
                    "SEG-002", "MINOR", cat,
                    f"'{segment}' missing from {len(chapters)} chapters",
                    "Multiple chapters",
                    f"Chapters with no {segment} references: {', '.join(chapters[:8])}",
                    f"Consider adding {segment} perspective where relevant",
                ))
            else:
                self._record(cat, True)

        # Overall balance
        total = sum(book_segments.values())
        if total > 0:
            targets = {"Department Head": 40, "Individual Contributor": 25,
                       "Small Company CEO": 15, "Senior Leader": 20}
            dist = []
            for seg, target in targets.items():
                actual = book_segments[seg] / total * 100
                dist.append(f"{seg}: {actual:.0f}% (target: {target}%)")
            self._record(cat, True, Finding(
                "SEG-INFO", "INFO", cat,
                "Reader segment balance across book",
                "All chapters",
                "Segment distribution: " + "; ".join(dist),
                "Adjust examples to match target audience weights",
            ))

    # ── Category 5: Actionability ───────────────────────────────────────

    def check_actionability(self):
        cat = "Actionability"
        if not self.chapters:
            return

        for ch in self.chapters:
            # Find action item section
            action_section = None
            for heading, content in ch.sections:
                h_lower = heading.lower()
                if any(kw in h_lower for kw in ["action", "monday", "morning",
                                                  "getting started", "step",
                                                  "foundation", "your first"]):
                    action_section = content
                    break

            if not action_section:
                self._record(cat, False, Finding(
                    "ACT-001", "MAJOR", cat,
                    f"No action item section: {ch.name}",
                    ch.rel_path,
                    f"Chapter '{ch.title}' has no actionable takeaway section",
                    "Add a 'Your Monday Morning Action Item' section with concrete steps",
                ))
                continue

            # Check for concrete verbs
            has_verb = any(
                re.search(rf"\b{v}\b", action_section, re.IGNORECASE)
                for v in ACTION_VERBS
            )
            if not has_verb:
                self._record(cat, False, Finding(
                    "ACT-002", "MINOR", cat,
                    f"Vague action item (no concrete verbs): {ch.name}",
                    ch.rel_path,
                    "Action section lacks concrete verbs (create, write, list, etc.)",
                    "Replace 'think about' / 'consider' with specific actions",
                ))
            else:
                self._record(cat, True)

            # Check for time frame
            has_timeframe = bool(re.search(
                r"\b(?:this week|monday|tomorrow|today|tonight|30 minutes|"
                r"one hour|next meeting|this afternoon|right now|immediately|"
                r"before (?:your|the) next)\b",
                action_section, re.IGNORECASE
            ))
            if not has_timeframe:
                self._record(cat, False, Finding(
                    "ACT-003", "MINOR", cat,
                    f"No time frame in action item: {ch.name}",
                    ch.rel_path,
                    "Action section doesn't specify when to do it",
                    "Add a time frame: 'this week', 'before your next meeting', etc.",
                ))
            else:
                self._record(cat, True)

            # Check for numbered steps
            has_steps = bool(re.search(r"\*\*Step \d", action_section))
            if has_steps:
                self._record(cat, True)

    # ── Category 6: Authority & Evidence ────────────────────────────────

    def check_authority(self):
        cat = "Authority & Evidence"
        if not self.chapters:
            return

        vague_total = []

        for ch in self.chapters:
            text = ch.body_text

            # Count specific evidence types
            named_people = re.findall(
                r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text
            )
            statistics = re.findall(
                r"\b\d+(?:\.\d+)?[%]\b|\b\d{1,3}(?:,\d{3})+\b|\$\d+", text
            )
            study_refs = re.findall(
                r"(?:study|research|survey|report|analysis)\s+(?:by|from|at|published)\s+\w+",
                text, re.IGNORECASE
            )

            # Vague sourcing
            vague_count = 0
            for pat in VAGUE_SOURCING:
                matches = re.findall(pat, text, re.IGNORECASE)
                for m in matches:
                    vague_count += 1
                    vague_total.append((ch.name, m))

            if vague_count > 2:
                self._record(cat, False, Finding(
                    "AUT-001", "MAJOR", cat,
                    f"{vague_count} vague source references: {ch.name}",
                    ch.rel_path,
                    f"Found {vague_count} unattributed claims ('research shows...', 'studies suggest...')",
                    "Name specific studies, researchers, or publications",
                ))
            elif vague_count > 0:
                self._record(cat, False, Finding(
                    "AUT-001", "MINOR", cat,
                    f"{vague_count} vague source reference(s): {ch.name}",
                    ch.rel_path,
                    f"Found {vague_count} unattributed claim(s)",
                    "Name specific studies, researchers, or publications",
                ))
            else:
                self._record(cat, True)

            # Low evidence density
            evidence_points = len(statistics) + len(study_refs)
            if evidence_points < 2 and ch.word_count > 1500:
                self._record(cat, False, Finding(
                    "AUT-002", "MINOR", cat,
                    f"Low evidence density ({evidence_points} data points): {ch.name}",
                    ch.rel_path,
                    f"Only {evidence_points} statistics/citations in {ch.word_count} words",
                    "Add 3-5 specific data points, statistics, or study references per chapter",
                ))
            else:
                self._record(cat, True)

    # ── Category 7: Narrative Flow ──────────────────────────────────────

    def check_narrative(self):
        cat = "Narrative Flow"
        if not self.chapters:
            return

        # Cross-references
        total_forward = 0
        total_callback = 0

        for i, ch in enumerate(self.chapters):
            text = ch.body_text

            forward = re.findall(
                r"(?:we'?ll|will)\s+(?:explore|discuss|cover|see|address|return to)\b.*?"
                r"(?:chapter|part|section)\b",
                text, re.IGNORECASE
            )
            callbacks = re.findall(
                r"(?:as we|we)\s+(?:saw|discussed|covered|learned|explored|established)\b.*?"
                r"(?:chapter|part|earlier|previously)\b",
                text, re.IGNORECASE
            )
            chapter_refs = re.findall(
                r"[Cc]hapter\s+\d+", text
            )

            total_forward += len(forward)
            total_callback += len(callbacks) + len(chapter_refs)

            # After chapter 3, should have at least some cross-refs
            if i > 2 and len(callbacks) + len(chapter_refs) == 0 and len(forward) == 0:
                self._record(cat, False, Finding(
                    "NAR-001", "MINOR", cat,
                    f"No cross-references: {ch.name}",
                    ch.rel_path,
                    "Chapter has no references to other chapters (forward or callback)",
                    "Add at least one callback to previous material or forward reference",
                ))
            else:
                self._record(cat, True)

        # Book-level cross-reference density
        if self.chapters:
            refs_per_ch = (total_forward + total_callback) / len(self.chapters)
            self._record(cat, True, Finding(
                "NAR-INFO", "INFO", cat,
                f"Cross-reference density: {refs_per_ch:.1f} per chapter",
                "All chapters",
                f"Forward refs: {total_forward}, Callbacks: {total_callback}, "
                f"Average: {refs_per_ch:.1f} per chapter",
                "Target: 1-2 cross-references per chapter for narrative cohesion",
            ))

    # ── Category 8: Repetition ──────────────────────────────────────────

    def check_repetition(self):
        cat = "Repetition"
        if not self.chapters:
            return

        # Track named characters across chapters
        character_chapters = defaultdict(list)
        # Track repeated phrases
        phrase_counter = Counter()

        for ch in self.chapters:
            text = ch.body_text

            # Named characters (First Last pattern)
            names = re.findall(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", text)
            # Filter common false positives
            noise = {"Monday Morning", "Action Item", "Common Objections",
                     "Part One", "Part Two", "Master Prompt", "Trust Ladder",
                     "Deep Review", "Chapter One"}
            for name in set(names) - noise:
                character_chapters[name].append(ch.name)

            # 3-5 word phrases (ngrams)
            words = re.findall(r"\b[a-z]+\b", text.lower())
            for n in [3, 4]:
                for i in range(len(words) - n):
                    phrase = " ".join(words[i:i + n])
                    # Skip very common phrases
                    if phrase not in {"the end of", "at the end", "one of the",
                                      "in order to", "as well as", "a lot of",
                                      "some of the", "part of the", "the way you",
                                      "you need to", "you want to", "is going to",
                                      "going to be", "the fact that", "in the next",
                                      "is one of", "the rest of", "if you want",
                                      "out of the", "for the first"}:
                        phrase_counter[phrase] += 1

        # Overused phrases (>8 occurrences across book)
        overused = [(p, c) for p, c in phrase_counter.most_common(100)
                    if c > 8 and len(p.split()) >= 3]
        if overused:
            examples = "; ".join(f'"{p}" ({c}x)' for p, c in overused[:10])
            self._record(cat, False, Finding(
                "REP-001", "MINOR", cat,
                f"{len(overused)} overused phrases found",
                "Multiple chapters",
                f"Frequently repeated phrases: {examples}",
                "Vary language — readers notice repetition across chapters",
            ))
        else:
            self._record(cat, True)

        # Characters appearing in only one chapter (potentially underdeveloped)
        recurring = {name: chs for name, chs in character_chapters.items()
                     if len(chs) > 1}
        single_use = {name: chs for name, chs in character_chapters.items()
                      if len(chs) == 1}

        self._record(cat, True, Finding(
            "REP-INFO", "INFO", cat,
            f"Character usage: {len(recurring)} recurring, {len(single_use)} single-use",
            "All chapters",
            f"Recurring characters (appear in 2+ chapters): "
            f"{', '.join(list(recurring.keys())[:10]) or 'none'}",
            "Consider bringing back key characters in later chapters to build familiarity",
        ))

        # Check for filler phrases
        total_filler = 0
        filler_examples = []
        for ch in self.chapters:
            for pat in FILLER_PHRASES:
                matches = re.findall(pat, ch.body_text, re.IGNORECASE)
                total_filler += len(matches)
                for m in matches:
                    filler_examples.append((ch.name, m))

        if total_filler > 5:
            examples = "; ".join(f"{ch}: '{m}'" for ch, m in filler_examples[:8])
            self._record(cat, False, Finding(
                "REP-002", "MINOR", cat,
                f"{total_filler} filler phrases across book",
                "Multiple chapters",
                f"Filler phrases found: {examples}",
                "Delete filler phrases — they add bulk without meaning",
            ))
        elif total_filler > 0:
            self._record(cat, False, Finding(
                "REP-002", "INFO", cat,
                f"{total_filler} filler phrase(s) found",
                "Multiple chapters",
                f"Minor filler detected in {total_filler} instance(s)",
                "Consider removing for tighter prose",
            ))
        else:
            self._record(cat, True)

    # ── Run All Checks ──────────────────────────────────────────────────

    def run(self):
        checks = {
            "structure": self.check_chapter_structure,
            "voice": self.check_voice_style,
            "hooks": self.check_hooks,
            "segments": self.check_reader_segments,
            "actionability": self.check_actionability,
            "authority": self.check_authority,
            "narrative": self.check_narrative,
            "repetition": self.check_repetition,
        }

        if self.category:
            if self.category in checks:
                checks[self.category]()
            else:
                print(f"Unknown category: {self.category}", file=sys.stderr)
                print(f"Available: {', '.join(checks.keys())}", file=sys.stderr)
                sys.exit(1)
        else:
            for check in checks.values():
                check()

    # ── Report Generation ───────────────────────────────────────────────

    def generate_report(self) -> str:
        lines = []
        lines.append("# Editorial Analysis Report")
        lines.append("")
        lines.append(f"**Project:** {self.project_path.name}")
        lines.append(f"**Date:** {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"**Chapters Analyzed:** {len(self.chapters)}")
        total_words = sum(ch.word_count for ch in self.chapters)
        lines.append(f"**Total Words:** {total_words:,}")
        lines.append(f"**Auditor:** claude-book-publisher editorial v{VERSION}")
        lines.append("")

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Category | Pass | Fail | Warn | Info |")
        lines.append("|----------|------|------|------|------|")

        totals = {"pass": 0, "fail": 0, "warn": 0, "info": 0}
        for cat_name in sorted(self.category_stats.keys()):
            s = self.category_stats[cat_name]
            info_count = sum(1 for f in self.findings
                             if f.category == cat_name and f.severity == "INFO")
            lines.append(
                f"| {cat_name} | {s['pass']} | {s['fail']} | "
                f"{s['warn']} | {info_count} |"
            )
            totals["pass"] += s["pass"]
            totals["fail"] += s["fail"]
            totals["warn"] += s["warn"]
            totals["info"] += info_count

        lines.append(
            f"| **Total** | {totals['pass']} | {totals['fail']} | "
            f"{totals['warn']} | {totals['info']} |"
        )
        lines.append("")

        crit_major = sum(1 for f in self.findings if f.severity in ("CRITICAL", "MAJOR"))
        if crit_major:
            lines.append(f"**Status:** NEEDS WORK ({crit_major} critical/major issues)")
        else:
            lines.append("**Status:** GOOD (no critical/major issues)")
        lines.append("")

        # Findings
        if self.findings:
            lines.append("## Findings")
            lines.append("")

            severity_order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}
            sorted_findings = sorted(
                self.findings,
                key=lambda f: (severity_order.get(f.severity, 4), f.category)
            )

            for f in sorted_findings:
                lines.append(f"### [{f.severity}] {f.finding_id}: {f.title}")
                lines.append(f"**Location:** `{f.location}`")
                lines.append(f"**Description:** {f.description}")
                lines.append(f"**Fix:** {f.fix}")
                if f.impact:
                    lines.append(f"**Impact:** {f.impact}")
                lines.append("")

        # Chapter summary
        lines.append("## Chapter Details")
        lines.append("")
        lines.append("| Chapter | Words | Sections | Hook Type |")
        lines.append("|---------|-------|----------|-----------|")
        for ch in self.chapters:
            hook = ch.hook_text
            first_para = hook.split("\n\n")[0] if hook else ""
            has_name = bool(re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", first_para))
            has_num = bool(re.search(r"\b\d+[%,.]?\d*\b", first_para))
            if has_name:
                htype = "Story"
            elif has_num:
                htype = "Statistic"
            elif first_para.strip().endswith("?"):
                htype = "Question"
            else:
                htype = "Scenario"
            lines.append(f"| {ch.name} | {ch.word_count:,} | {len(ch.sections)} | {htype} |")
        lines.append("")

        # Verification
        report_body = "\n".join(lines)
        hash_input = f"{report_body}|{len(self.findings)}|{self.checks_run}"
        report_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        lines.append("## Verification")
        lines.append("")
        lines.append(f"**Report Hash (SHA-256):** `{report_hash}`")
        lines.append(f"**Findings Count:** {len(self.findings)}")
        lines.append(f"**Checks Executed:** {self.checks_run}")
        lines.append("")
        lines.append("---")
        lines.append(f"*Generated by claude-book-publisher editorial v{VERSION}*")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Editorial analysis for nonfiction business books"
    )
    parser.add_argument("project_path", help="Path to book project")
    parser.add_argument("--category", help="Run only specific category "
                        "(structure, voice, hooks, segments, actionability, "
                        "authority, narrative, repetition)")
    parser.add_argument("--chapter", help="Analyze only chapters matching this string")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--output", help="Write report to file")

    args = parser.parse_args()

    if not os.path.isdir(args.project_path):
        print(f"Error: {args.project_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    analyzer = EditorialAnalyzer(
        args.project_path,
        category=args.category,
        chapter_filter=args.chapter,
    )
    analyzer.run()
    report = analyzer.generate_report()

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report, file=sys.stderr)

    # Exit with failure if critical/major issues
    crit_major = sum(1 for f in analyzer.findings if f.severity in ("CRITICAL", "MAJOR"))
    sys.exit(1 if crit_major else 0)


if __name__ == "__main__":
    main()

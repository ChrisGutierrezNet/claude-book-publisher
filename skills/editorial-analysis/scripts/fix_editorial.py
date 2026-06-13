#!/usr/bin/env python3
"""
Editorial Fix Generator for Nonfiction Business Books

Finds editorial issues, generates concrete replacement text with
full sentence before/after comparisons, and outputs a styled HTML report.

Usage:
    python3 fix_editorial.py path/to/project
    python3 fix_editorial.py --output fixes.html path/to/project
    python3 fix_editorial.py --chapter ch01 path/to/project
"""

import argparse
import html as html_mod
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


VERSION = "0.2.0"


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

FILLER_PHRASES = {
    "it's important to note that ": "",
    "it is important to note that ": "",
    "at the end of the day, ": "",
    "at the end of the day ": "",
    "the reality is that ": "",
    "let's be honest, ": "",
    "let's be honest ": "",
    "here's the thing: ": "",
    "here's the thing, ": "",
    "the fact of the matter is ": "",
    "it goes without saying that ": "",
    "needless to say, ": "",
    "needless to say ": "",
    "in order to ": "to ",
    "in order to": "to",
    "the bottom line is ": "",
    "when all is said and done, ": "ultimately, ",
    "as a matter of fact, ": "",
    "it should be noted that ": "",
    "it is worth mentioning that ": "",
}

TEXTBOOK_MAP = [
    (r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) explore\b", "Let's dig into"),
    (r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) discuss\b", "Here's what matters about"),
    (r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) examine\b", "Let's look at"),
    (r"[Ii]n this chapter,?\s*we (?:will|shall|are going to) cover\b", "Here's what you need to know about"),
    (r"[Tt]his chapter covers\b", "You'll learn about"),
    (r"[Tt]his chapter discusses\b", "Here's what matters:"),
    (r"[Tt]his chapter explores\b", "Let's dig into"),
    (r"[Tt]his chapter examines\b", "Let's look at"),
    (r"[Tt]his section covers\b", "Here's what you need:"),
    (r"[Aa]s previously mentioned\b", "As we saw earlier"),
    (r"[Aa]s earlier mentioned\b", "As we covered"),
    (r"[Tt]he reader should note that\b", "Notice that"),
    (r"[Tt]he reader should be aware that\b", "Keep in mind:"),
    (r"[Ii]t can be concluded that\b", "The takeaway:"),
    (r"[Aa]s we shall see\b", "You'll see"),
    (r"[Ii]n the following section\b", "Next"),
]

HEDGING_MAP = [
    (r"\bperhaps\s", ""),
    (r"\bmaybe\s", ""),
    (r"\bsomewhat\s", ""),
    (r"\barguably,?\s", ""),
    (r"\bto some extent,?\s", ""),
    (r"\b[Ii]t seems (that )?", ""),
    (r"\b[Ii]n my opinion,?\s", ""),
    (r"\bI think that\s", ""),
    (r"\bI believe that\s", ""),
    (r"\bI feel that\s", ""),
]

VAGUE_SOURCE_MAP = [
    (r"[Rr]esearch shows\b", "[Name the study] found"),
    (r"[Rr]esearch suggests\b", "[Name the study] suggests"),
    (r"[Rr]esearch indicates\b", "[Name the study] found"),
    (r"[Rr]esearch has shown\b", "[Name the study] found"),
    (r"[Ss]tudies show\b", "A [year] [institution] study found"),
    (r"[Ss]tudies suggest\b", "A [year] [institution] study suggests"),
    (r"[Ss]tudies indicate\b", "A [year] [institution] study found"),
    (r"[Ss]tudies have shown\b", "A [year] [institution] study found"),
    (r"[Ee]xperts say\b", "[Named expert] says"),
    (r"[Ee]xperts agree\b", "[Named expert] argues"),
    (r"[Ee]xperts believe\b", "[Named expert] argues"),
    (r"[Ee]xperts recommend\b", "[Named expert] recommends"),
    (r"[Dd]ata shows\b", "[Source]'s data shows"),
    (r"[Dd]ata suggests\b", "[Source]'s data suggests"),
]

PASSIVE_RE = re.compile(
    r"\b(is|are|was|were|been|being|be)\s+(?:\w+ly\s+)?"
    r"(\w+(?:ed|en|ilt|wn|ght|nt|pt|ade|old|orn|ung|oken|osen|idden|iven|aken|tten))\b",
    re.IGNORECASE
)

TIME_FRAME_EXAMPLE = (
    "Add a time frame. Examples:\n"
    '  "This week, take 30 minutes to..."\n'
    '  "Before your next team meeting..."\n'
    '  "Monday morning, open your..."\n'
    '  "Right now — before you close this book..."'
)

HOOK_STORY_EXAMPLE = (
    "Rewrite the opening with a named character and specific situation:\n\n"
    "EXAMPLE:\n"
    "Maya manages customer success for a 200-person SaaS company. Last quarter,\n"
    "she spent 11 hours every week writing the same onboarding emails with minor\n"
    "variations — while her team's response times crept past the 24-hour mark.\n\n"
    "Then she built a workflow that cut those 11 hours to 90 minutes.\n"
    "This chapter shows you exactly how.\n\n"
    "WHY THIS WORKS: Named characters create empathy. Specific details\n"
    "(11 hours, 200-person, 24-hour mark) create credibility. The gap between\n"
    "problem and solution creates tension that pulls the reader forward."
)

SEGMENT_TEMPLATES = {
    "Department Head": (
        "ADD THIS TO THE APPLICATIONS SECTION:\n\n"
        "### For Department Heads\n\n"
        "[Name], who manages [team size] [function] team at a [company type],\n"
        "applied this by [specific action using the chapter's framework].\n"
        "Within [timeframe], the team saw [specific measurable result].\n\n"
        "The key for managers: [insight specific to managing teams with\n"
        "this framework — delegation, accountability, scaling across reports]."
    ),
    "Individual Contributor": (
        "ADD THIS TO THE APPLICATIONS SECTION:\n\n"
        "### For Individual Contributors\n\n"
        "You don't need team buy-in for this. [Name], a [role] at [company],\n"
        "applied this to [his/her] own [specific daily task]. Time dropped\n"
        "from [old time] to [new time] — and nobody even noticed the change\n"
        "until [he/she] started producing [better result] consistently.\n\n"
        "Start with your most repetitive task. That's your proving ground."
    ),
    "Small Company CEO": (
        "ADD THIS TO THE APPLICATIONS SECTION:\n\n"
        "### For Small Company CEOs\n\n"
        "[Name] runs a [number]-person [industry] firm. No AI team, no IT\n"
        "department, just [him/her] and a browser tab. [He/She] adapted this\n"
        "framework by [simplified version of the chapter's approach].\n\n"
        "The small-company advantage: you can move in a day what enterprises\n"
        "debate for a quarter. [Specific result in specific timeframe]."
    ),
    "Senior Leader": (
        "ADD THIS TO THE APPLICATIONS SECTION:\n\n"
        "### For Senior Leaders\n\n"
        "[Name], VP of [function] at a [size]-person [industry] company,\n"
        "used this framework to [strategic action]. But at the executive\n"
        "level, the real value wasn't personal productivity — it was\n"
        "[organizational insight: policy implications, precedent set,\n"
        "cultural shift enabled].\n\n"
        "Your first win needs to be visible enough to justify the next ten."
    ),
}

# Reader segment detection keywords
SEGMENT_KEYWORDS = {
    "Department Head": [r"\bmanager\b", r"\bdirector\b", r"\bteam lead\b",
                        r"\bdepartment\b", r"\bher team\b", r"\bhis team\b"],
    "Individual Contributor": [r"\bindividual contributor\b", r"\bIC\b",
                               r"\bpersonal productivity\b", r"\bknowledge worker\b"],
    "Small Company CEO": [r"\bsmall (?:company|business)\b", r"\bfounder\b",
                           r"\bowner\b", r"\bagency\b", r"\b\d+-person\b"],
    "Senior Leader": [r"\bVP\b", r"\bvice president\b", r"\bC-suite\b",
                      r"\bCEO\b", r"\bCOO\b", r"\bCRO\b", r"\bexecutive\b"],
}


# ── Sentence Utilities ──────────────────────────────────────────────────

def extract_sentence(text: str, pos: int) -> tuple[str, int, int]:
    """Extract the full sentence containing position `pos`.
    Returns (sentence, start_index, end_index)."""
    # Find sentence start (look back for sentence-ending punctuation or start of text)
    start = 0
    for i in range(pos - 1, -1, -1):
        if text[i] in ".!?" and i < pos - 1:
            # Make sure it's a real sentence boundary, not abbreviation
            after = text[i + 1:i + 3]
            if after and (after[0] == " " or after[0] == "\n"):
                start = i + 1
                break
        elif text[i] == "\n" and (i == 0 or text[i - 1] == "\n"):
            start = i + 1
            break

    # Find sentence end
    end = len(text)
    for i in range(pos, len(text)):
        if text[i] in ".!?":
            # Check it's a real sentence end
            if i + 1 >= len(text) or text[i + 1] in " \n\r":
                end = i + 1
                break

    sentence = text[start:end].strip()
    return sentence, start, end


def find_line_num(text: str, pos: int) -> int:
    """Find line number for character position."""
    return text[:pos].count("\n") + 1


def strip_yaml(text: str) -> str:
    """Remove YAML front matter."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:]
    return text


def strip_markdown_noise(text: str) -> str:
    """Remove code blocks, tables, blockquotes, HTML comments."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>.*$", "", text, flags=re.MULTILINE)
    return text


# ── Fix Data Class ──────────────────────────────────────────────────────

class Fix:
    def __init__(self, category: str, severity: str, chapter: str,
                 file_path: str, line_num: int,
                 sentence_before: str, sentence_after: str,
                 explanation: str, highlight_word: str = ""):
        self.category = category
        self.severity = severity
        self.chapter = chapter
        self.file_path = file_path
        self.line_num = line_num
        self.sentence_before = sentence_before
        self.sentence_after = sentence_after
        self.explanation = explanation
        self.highlight_word = highlight_word


# ── Fixer Engine ────────────────────────────────────────────────────────

class EditorialFixer:
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
            if len(f.read_text().split()) > 200:
                self.chapter_files.append(f)

    def _add(self, category, severity, chapter, fpath, line,
             before, after, explanation, highlight=""):
        self.fixes.append(Fix(category, severity, chapter, fpath, line,
                              before, after, explanation, highlight))
        self.stats[category] += 1

    # ── Guru-Speak ──────────────────────────────────────────────────────

    def fix_guru_speak(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            text = strip_markdown_noise(text)
            for guru_word, replacement in GURU_REPLACEMENTS.items():
                pattern = re.compile(r'\b' + re.escape(guru_word) + r'\b')
                for match in pattern.finditer(text):
                    sentence, s_start, s_end = extract_sentence(text, match.start())
                    if len(sentence) < 10:
                        continue
                    fixed = pattern.sub(replacement, sentence, count=1)
                    line = find_line_num(raw, raw.find(sentence[:40]))
                    self._add(
                        "Guru-Speak", "MAJOR", f.name, str(f), line,
                        sentence, fixed,
                        f'Replace "{guru_word}" with "{replacement}" — concrete language builds trust',
                        guru_word
                    )

    # ── Filler Phrases ──────────────────────────────────────────────────

    def fix_filler_phrases(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            text_lower = text.lower()
            for filler, replacement in FILLER_PHRASES.items():
                idx = 0
                while True:
                    pos = text_lower.find(filler.lower(), idx)
                    if pos == -1:
                        break
                    sentence, _, _ = extract_sentence(text, pos)
                    if len(sentence) < 10:
                        idx = pos + len(filler)
                        continue
                    # Apply fix to the sentence
                    filler_in_sent = re.search(re.escape(filler.strip()),
                                               sentence, re.IGNORECASE)
                    if filler_in_sent:
                        original_phrase = filler_in_sent.group()
                        if replacement:
                            fixed = sentence.replace(original_phrase, replacement.strip(), 1)
                        else:
                            # Remove filler and clean up
                            fixed = re.sub(
                                re.escape(original_phrase) + r",?\s*",
                                "", sentence, count=1
                            ).strip()
                            if fixed and fixed[0].islower():
                                fixed = fixed[0].upper() + fixed[1:]
                    else:
                        fixed = sentence
                    line = find_line_num(raw, raw.lower().find(filler.lower()))
                    self._add(
                        "Filler Phrases", "MINOR", f.name, str(f), line,
                        sentence, fixed,
                        f'Delete "{filler.strip()}" — start with the actual point',
                        filler.strip()
                    )
                    idx = pos + len(filler)

    # ── Textbook Voice ──────────────────────────────────────────────────

    def fix_textbook_voice(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            for pattern, replacement in TEXTBOOK_MAP:
                for match in re.finditer(pattern, text):
                    sentence, _, _ = extract_sentence(text, match.start())
                    if len(sentence) < 10:
                        continue
                    fixed = re.sub(pattern, replacement, sentence, count=1)
                    line = find_line_num(raw, raw.find(match.group()[:30]))
                    self._add(
                        "Textbook Voice", "MINOR", f.name, str(f), line,
                        sentence, fixed,
                        "Replace academic phrasing with conversational voice",
                        match.group()
                    )

    # ── Hedging Language ────────────────────────────────────────────────

    def fix_hedging(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            text = strip_markdown_noise(text)
            for pattern, replacement in HEDGING_MAP:
                for match in re.finditer(pattern, text):
                    sentence, _, _ = extract_sentence(text, match.start())
                    if len(sentence) < 10:
                        continue
                    original_word = match.group().strip()
                    if replacement:
                        fixed = re.sub(pattern, replacement, sentence, count=1)
                    else:
                        # Remove the hedge word and capitalize if needed
                        fixed = re.sub(pattern, "", sentence, count=1).strip()
                        if fixed and fixed[0].islower():
                            fixed = fixed[0].upper() + fixed[1:]
                    line = find_line_num(raw, raw.find(sentence[:40]))
                    self._add(
                        "Hedging Language", "MINOR", f.name, str(f), line,
                        sentence, fixed,
                        f'Remove "{original_word}" — state it directly, you wrote the book',
                        original_word
                    )

    # ── Vague Sources ───────────────────────────────────────────────────

    def fix_vague_sources(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            for pattern, replacement in VAGUE_SOURCE_MAP:
                for match in re.finditer(pattern, text):
                    sentence, _, _ = extract_sentence(text, match.start())
                    if len(sentence) < 10:
                        continue
                    fixed = re.sub(pattern, replacement, sentence, count=1)
                    line = find_line_num(raw, raw.find(match.group()))
                    self._add(
                        "Vague Sources", "MAJOR", f.name, str(f), line,
                        sentence, fixed,
                        "Name the specific study, researcher, or publication — vague sourcing undermines authority",
                        match.group()
                    )

    # ── Long Sentences ──────────────────────────────────────────────────

    def fix_long_sentences(self):
        split_conjunctions = ["but", "and", "while", "because", "however",
                              "although", "which", "where", "when", "yet",
                              "so", "since", "though"]

        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            text = strip_markdown_noise(text)

            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', text)
            for sent in sentences:
                sent = sent.strip()
                words = sent.split()
                if len(words) <= 35 or len(sent) < 20:
                    continue

                # Find best split point
                best_split = None
                mid = len(words) // 2
                for sw in split_conjunctions:
                    positions = [i for i, w in enumerate(words)
                                 if w.lower().strip(",.;:—") == sw and 8 < i < len(words) - 5]
                    if positions:
                        pos = min(positions, key=lambda p: abs(p - mid))
                        if best_split is None or abs(pos - mid) < abs(best_split[1] - mid):
                            best_split = (sw, pos)

                # Also check for em-dash and semicolon splits
                for i, w in enumerate(words):
                    if ("—" in w or w == ";") and 8 < i < len(words) - 5:
                        if best_split is None or abs(i - mid) < abs(best_split[1] - mid):
                            best_split = (w, i)

                if best_split:
                    sw, pos = best_split
                    part1_words = words[:pos]
                    part2_words = words[pos + 1:] if sw.strip(",.;:—") in split_conjunctions else words[pos + 1:]

                    part1 = " ".join(part1_words).rstrip(",.;:—") + "."
                    part2 = " ".join(part2_words)
                    if part2:
                        part2 = part2[0].upper() + part2[1:]
                    fixed = f"{part1} {part2}"
                else:
                    fixed = f"[SPLIT THIS {len(words)}-WORD SENTENCE — find a natural break point where the idea shifts]"

                line = find_line_num(raw, raw.find(sent[:50]))
                self._add(
                    "Long Sentences", "MINOR", f.name, str(f), line,
                    sent, fixed,
                    f"Split this {len(words)}-word sentence — target: under 35 words per sentence",
                )

    # ── Passive Voice ───────────────────────────────────────────────────

    def fix_passive_voice(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            text = strip_markdown_noise(text)

            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', text)
            count = 0
            for sent in sentences:
                sent = sent.strip()
                if len(sent.split()) < 5:
                    continue
                match = PASSIVE_RE.search(sent)
                if match:
                    count += 1
                    if count > 8:  # Cap per chapter to avoid noise
                        continue
                    aux = match.group(1)
                    verb = match.group(2)
                    # Build active voice suggestion
                    fixed = (
                        f"[REWRITE IN ACTIVE VOICE] "
                        f'Identify who performs the action "{verb}" and make them the subject. '
                        f'Example: "{aux} {verb} by X" becomes "X {verb.rstrip("ed")}s..."'
                    )
                    line = find_line_num(raw, raw.find(sent[:40]))
                    self._add(
                        "Passive Voice", "MINOR", f.name, str(f), line,
                        sent, fixed,
                        f'Passive: "{aux} {verb}" — flip to active voice for stronger writing',
                        f"{aux} {verb}"
                    )

    # ── Missing Time Frames ─────────────────────────────────────────────

    def fix_missing_timeframes(self):
        for f in self.chapter_files:
            raw = f.read_text()
            sections = re.split(r"^(##\s+.+)$", raw, flags=re.MULTILINE)

            for i, section in enumerate(sections):
                if not section.startswith("##"):
                    continue
                heading = section.lower()
                if not any(kw in heading for kw in ["action", "monday", "morning",
                                                     "getting started", "your first"]):
                    continue
                # The content is the next element
                if i + 1 >= len(sections):
                    continue
                content = sections[i + 1]

                has_time = bool(re.search(
                    r"\b(?:this week|monday|tomorrow|today|tonight|30 minutes|"
                    r"one hour|next meeting|this afternoon|right now|immediately|"
                    r"before (?:your|the) next)\b",
                    content, re.IGNORECASE
                ))
                if not has_time:
                    # Get the first real sentence
                    lines = [l.strip() for l in content.split("\n") if l.strip()
                             and not l.strip().startswith("#")
                             and not l.strip().startswith("**Step")]
                    first_sent = lines[0] if lines else content[:200]
                    line = find_line_num(raw, raw.find(section))

                    fixed = (
                        f'This week, {first_sent[0].lower()}{first_sent[1:]}'
                        if first_sent and first_sent[0].isupper()
                        else f'This week: {first_sent}'
                    )
                    self._add(
                        "Missing Time Frame", "MINOR", f.name, str(f), line,
                        first_sent, fixed,
                        TIME_FRAME_EXAMPLE,
                    )

    # ── Hook Variety ────────────────────────────────────────────────────

    def fix_hook_variety(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            text = re.sub(r"<!--.*?-->", "", text).strip()

            # Find the first ## section (the hook)
            parts = re.split(r"^##\s+", text, flags=re.MULTILINE)
            if len(parts) < 2:
                continue

            hook_content = "\n".join(parts[1].split("\n")[1:]).strip()
            first_para = hook_content.split("\n\n")[0] if hook_content else ""
            if not first_para or len(first_para) < 50:
                continue

            # Check for named character (First Last pattern)
            has_name = bool(re.search(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b", first_para))
            if not has_name:
                # Get first 2-3 sentences for the "before"
                hook_sentences = re.split(r'(?<=[.!?])\s+', first_para)
                before_text = " ".join(hook_sentences[:3])
                line = find_line_num(raw, raw.find(first_para[:40]))
                self._add(
                    "Hook Variety", "MINOR", f.name, str(f), line,
                    before_text,
                    HOOK_STORY_EXAMPLE,
                    "Story hooks with named characters are significantly more engaging than generic scenarios — "
                    "21 of 28 chapters currently open without a named character",
                )

    # ── Segment Coverage ────────────────────────────────────────────────

    def fix_segment_gaps(self):
        for f in self.chapter_files:
            raw = f.read_text()
            text = strip_yaml(raw)
            for segment, keywords in SEGMENT_KEYWORDS.items():
                count = sum(len(re.findall(kw, text, re.IGNORECASE)) for kw in keywords)
                if count == 0:
                    # Find the Applications or Examples section to suggest where to add
                    app_match = re.search(r"^##\s+.*(Application|Example|Practice|Role).*$",
                                          raw, re.MULTILINE | re.IGNORECASE)
                    if app_match:
                        line = find_line_num(raw, app_match.start())
                        context_sent = app_match.group().strip()
                    else:
                        line = len(raw.split("\n")) - 20
                        context_sent = "[No Applications section found — add one]"

                    self._add(
                        "Segment Coverage", "MINOR", f.name, str(f), line,
                        f"[No {segment} examples in this chapter]",
                        SEGMENT_TEMPLATES[segment],
                        f"This chapter has zero {segment} references — add an example "
                        f"to reach all four reader segments",
                    )

    # ── Run All ─────────────────────────────────────────────────────────

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

    # ── HTML Generation ─────────────────────────────────────────────────

    def _highlight(self, text: str, word: str) -> str:
        """HTML-escape text and highlight the target word."""
        escaped = html_mod.escape(text)
        if word:
            escaped_word = html_mod.escape(word)
            escaped = re.sub(
                re.escape(escaped_word),
                f'<mark style="background:#fecaca;padding:1px 3px;border-radius:3px;">'
                f'{escaped_word}</mark>',
                escaped, count=1, flags=re.IGNORECASE
            )
        return escaped

    def generate_html(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total_words = sum(
            len(strip_yaml(f.read_text()).split()) for f in self.chapter_files
        )

        by_category = defaultdict(list)
        for fix in self.fixes:
            by_category[fix.category].append(fix)

        by_chapter = defaultdict(list)
        for fix in self.fixes:
            by_chapter[fix.chapter].append(fix)

        sev_counts = Counter(f.severity for f in self.fixes)

        cat_order = ["Guru-Speak", "Vague Sources", "Textbook Voice",
                     "Filler Phrases", "Hedging Language", "Long Sentences",
                     "Passive Voice", "Missing Time Frame", "Hook Variety",
                     "Segment Coverage"]

        parts = []
        parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Editorial Fixes — {html_mod.escape(self.project_path.name)}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #fafaf9; color: #1c1917; line-height: 1.6;
    padding: 2rem; max-width: 1200px; margin: 0 auto;
}}
h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }}
h2 {{ font-size: 1.4rem; font-weight: 600; margin: 2.5rem 0 1rem;
      border-bottom: 2px solid #e7e5e4; padding-bottom: 0.5rem; }}
h3 {{ font-size: 1.05rem; font-weight: 600; margin: 1.5rem 0 0.75rem; color: #57534e; }}
.sub {{ color: #78716c; font-size: 0.9rem; margin-bottom: 1.5rem; }}
.stats {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.75rem; margin-bottom: 2rem;
}}
.sc {{ background: #fff; border: 1px solid #e7e5e4; border-radius: 8px;
       padding: 0.75rem; text-align: center; }}
.sc .n {{ font-size: 1.7rem; font-weight: 700; }}
.sc .l {{ font-size: 0.75rem; color: #78716c; text-transform: uppercase; letter-spacing:0.05em; }}
.sc.red .n {{ color: #dc2626; }}
.sc.amber .n {{ color: #d97706; }}
.sc.green .n {{ color: #16a34a; }}
.toc {{ background: #fff; border: 1px solid #e7e5e4; border-radius: 8px;
        padding: 1rem 1.25rem; margin-bottom: 2rem; }}
.toc ul {{ list-style: none; padding: 0; columns: 2; }}
.toc li {{ padding: 0.2rem 0; }}
.toc a {{ color: #2563eb; text-decoration: none; }}
.toc a:hover {{ text-decoration: underline; }}
.cnt {{ color: #78716c; font-size: 0.8rem; }}
.card {{
    background: #fff; border: 1px solid #e7e5e4; border-radius: 8px;
    padding: 1.25rem; margin-bottom: 0.75rem;
}}
.card.sev-MAJOR {{ border-left: 4px solid #dc2626; }}
.card.sev-MINOR {{ border-left: 4px solid #d97706; }}
.hdr {{ display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.4rem; }}
.loc {{ font-size: 0.78rem; color: #78716c; font-family: 'SF Mono', Consolas, monospace; }}
.badge {{ display: inline-block; font-size: 0.65rem; font-weight: 600;
          padding: 0.12rem 0.45rem; border-radius: 999px; text-transform: uppercase; }}
.badge.major {{ background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }}
.badge.minor {{ background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }}
.ba {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin: 0.6rem 0; }}
@media (max-width: 750px) {{ .ba {{ grid-template-columns: 1fr; }} }}
.ba > div {{ border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.88rem;
             line-height: 1.55; white-space: pre-wrap; word-break: break-word; }}
.bf {{ background: #fef2f2; border: 1px solid #fecaca; }}
.af {{ background: #f0fdf4; border: 1px solid #bbf7d0; }}
.bl {{ font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
       letter-spacing: 0.05em; margin-bottom: 0.2rem; }}
.bl.r {{ color: #dc2626; }} .bl.g {{ color: #16a34a; }}
.expl {{ font-size: 0.82rem; color: #78716c; margin-top: 0.4rem; }}
mark {{ background: #fecaca; padding: 1px 3px; border-radius: 3px; }}
.gm {{ background: #bbf7d0; padding: 1px 3px; border-radius: 3px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 0.5rem; }}
th {{ text-align: left; padding: 0.5rem; border-bottom: 2px solid #e7e5e4; }}
td {{ padding: 0.4rem 0.5rem; border-bottom: 1px solid #f5f5f4; }}
tr.hot {{ background: #fef2f2; }}
footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e7e5e4;
          color: #78716c; font-size: 0.78rem; text-align: center; }}
</style>
</head>
<body>
<h1>Editorial Fix Report</h1>
<p class="sub">{html_mod.escape(self.project_path.name)} &mdash; {len(self.chapter_files)} chapters
&mdash; {total_words:,} words &mdash; {now}</p>

<div class="stats">
<div class="sc red"><div class="n">{sev_counts.get('MAJOR', 0)}</div><div class="l">Major</div></div>
<div class="sc amber"><div class="n">{sev_counts.get('MINOR', 0)}</div><div class="l">Minor</div></div>
<div class="sc green"><div class="n">{len(self.fixes)}</div><div class="l">Total Fixes</div></div>
<div class="sc"><div class="n">{len(by_category)}</div><div class="l">Categories</div></div>
<div class="sc"><div class="n">{len(by_chapter)}</div><div class="l">Chapters</div></div>
</div>
""")

        # TOC
        parts.append('<div class="toc"><h3 style="margin-top:0">Categories</h3><ul>')
        for cat in cat_order:
            if cat in by_category:
                n = len(by_category[cat])
                maj = sum(1 for fx in by_category[cat] if fx.severity == "MAJOR")
                extra = f", {maj} major" if maj else ""
                parts.append(
                    f'<li><a href="#{cat.lower().replace(" ", "-")}">{cat}</a> '
                    f'<span class="cnt">({n}{extra})</span></li>'
                )
        parts.append("</ul></div>")

        # Fixes by category
        for cat in cat_order:
            if cat not in by_category:
                continue
            fixes = by_category[cat]
            aid = cat.lower().replace(" ", "-")
            parts.append(f'<h2 id="{aid}">{cat} <span class="cnt">({len(fixes)} fixes)</span></h2>')

            grouped = defaultdict(list)
            for fx in fixes:
                grouped[fx.chapter].append(fx)

            for ch, ch_fixes in sorted(grouped.items()):
                parts.append(f'<h3>{ch} ({len(ch_fixes)})</h3>')
                for fx in ch_fixes:
                    sc = fx.severity.lower()
                    before_html = self._highlight(fx.sentence_before, fx.highlight_word)
                    # For the after, highlight the replacement in green
                    after_escaped = html_mod.escape(fx.sentence_after)
                    if fx.highlight_word and fx.highlight_word in GURU_REPLACEMENTS:
                        rep = GURU_REPLACEMENTS[fx.highlight_word]
                        after_escaped = re.sub(
                            re.escape(html_mod.escape(rep)),
                            f'<span class="gm">{html_mod.escape(rep)}</span>',
                            after_escaped, count=1
                        )

                    parts.append(f'<div class="card sev-{fx.severity}">')
                    parts.append(f'<div class="hdr"><span class="badge {sc}">{fx.severity}</span>'
                                 f'<span class="loc">{fx.chapter}:{fx.line_num}</span></div>')
                    parts.append('<div class="ba"><div>')
                    parts.append(f'<div class="bl r">BEFORE</div><div class="bf">{before_html}</div>')
                    parts.append('</div><div>')
                    parts.append(f'<div class="bl g">AFTER</div><div class="af">{after_escaped}</div>')
                    parts.append('</div></div>')
                    parts.append(f'<div class="expl">{html_mod.escape(fx.explanation)}</div>')
                    parts.append('</div>')

        # Chapter summary table
        parts.append('<h2>Fixes by Chapter</h2><table>')
        parts.append('<tr><th>Chapter</th><th style="text-align:center">Total</th>'
                     '<th style="text-align:center">Major</th>'
                     '<th style="text-align:center">Minor</th></tr>')
        for ch in sorted(by_chapter.keys()):
            fixes = by_chapter[ch]
            maj = sum(1 for fx in fixes if fx.severity == "MAJOR")
            minor = sum(1 for fx in fixes if fx.severity == "MINOR")
            cls = ' class="hot"' if maj > 3 else ""
            parts.append(
                f'<tr{cls}><td>{html_mod.escape(ch)}</td>'
                f'<td style="text-align:center">{len(fixes)}</td>'
                f'<td style="text-align:center;color:#dc2626">{maj or "-"}</td>'
                f'<td style="text-align:center;color:#d97706">{minor or "-"}</td></tr>'
            )
        parts.append('</table>')

        parts.append(f"""
<footer>
claude-book-publisher editorial v{VERSION} &mdash;
{len(self.fixes)} fixes across {len(by_chapter)} chapters &mdash; {now}
</footer>
</body></html>""")

        return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Generate editorial fixes with full sentence before/after")
    parser.add_argument("project_path", help="Path to book project")
    parser.add_argument("--output", default="editorial-fixes.html", help="Output HTML file")
    parser.add_argument("--chapter", help="Only analyze chapters matching this string")
    args = parser.parse_args()

    if not os.path.isdir(args.project_path):
        print(f"Error: {args.project_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    fixer = EditorialFixer(args.project_path, chapter_filter=args.chapter)
    fixer.run()
    html = fixer.generate_html()

    out = Path(args.project_path) / args.output
    out.write_text(html)

    print(f"Report: {out}", file=sys.stderr)
    print(f"  {len(fixer.fixes)} fixes across {len(fixer.stats)} categories", file=sys.stderr)
    for cat, count in sorted(fixer.stats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()

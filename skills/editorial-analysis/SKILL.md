---
name: editorial-analysis
description: |
  Deep editorial analysis for nonfiction business books.
  Checks 60+ quality signals across voice, structure, narrative,
  reader engagement, and authority. Designed for reuse across any
  nonfiction business manuscript.
---

# Editorial Analysis

## Overview

Analyzes manuscript content quality against nonfiction business book best practices. Unlike the manuscript-audit skill (which checks formatting/KDP compliance), this skill evaluates the writing itself: clarity, engagement, structure, and persuasiveness.

## Analysis Categories

### 1. Chapter Structure Adherence

Every business book chapter should follow a predictable structure that readers can trust:

| Section           | Purpose                                               | Target Length     |
| ----------------- | ----------------------------------------------------- | ----------------- |
| Hook              | Story, statistic, or provocation that earns attention | 200-300 words     |
| Core Framework    | Main teaching content                                 | 1,500-2,000 words |
| Applications      | Role-specific examples across reader segments         | 600-800 words     |
| Common Objections | Address "but what about..." resistance                | 300-400 words     |
| Action Item       | Specific thing reader does Monday morning             | 100-200 words     |

**Checks:**

- Missing sections (no hook, no action item, etc.)
- Section order violations
- Section length outside target range
- Hook type classification (story, statistic, question, scenario)

### 2. Voice & Style

Business books fail when they sound like textbooks, TED talks, or LinkedIn posts.

**Passive Voice:**

- Target: <15% of sentences
- Warning: 15-25%
- Fail: >25%

**Hedging Language:**

- Weak: "might", "could", "perhaps", "somewhat", "arguably"
- Strong: "is", "does", "will", "creates", "destroys"
- Target: <10% hedging sentences

**Guru-Speak / Buzzwords:**

- Flagged terms: "unlock", "unleash", "transform", "revolutionize", "game-changer", "paradigm shift", "synergy", "leverage" (as verb), "disrupt", "empower", "supercharge"
- Target: 0 instances in final manuscript

**Sentence Variety:**

- Average length: 12-20 words
- Variation coefficient: >0.3 (mix short punchy with longer explanatory)
- Max consecutive same-length sentences: 3

**Paragraph Length:**

- Target: 2-4 sentences per paragraph
- Warning: >6 sentences (wall of text)
- Short paragraphs (<2 sentences) OK for emphasis, flag if >30%

### 3. Reader Segment Coverage

For multi-audience business books, every major concept needs examples for all segments:

| Segment                     | Weight | Description                               |
| --------------------------- | ------ | ----------------------------------------- |
| Department/Function Leaders | 40%    | CS managers, ops directors, teams of 5-50 |
| Individual Contributors     | 25%    | Knowledge workers, personal productivity  |
| Small Company CEOs          | 15%    | Founders/owners, 5-50 employees           |
| Senior Leaders              | 20%    | VPs, C-suite, organizational direction    |

**Checks:**

- Segment mention frequency per chapter
- Chapters with zero coverage for any segment
- Overall book segment balance vs target weights
- Named character diversity (not all examples about the same type)

### 4. Hook Quality

The opening 300 words determine whether readers continue.

**Hook Types (best to worst for business books):**

1. **Story** — Named character, specific situation, tension/resolution
2. **Surprising Statistic** — Concrete number that challenges assumptions
3. **Provocative Statement** — Contrarian claim that demands explanation
4. **Question** — Rhetorical question (weaker, overused)
5. **Definition** — "X is..." (weakest, textbook-like)

**Checks:**

- Hook type classification
- Named character present? (strongest signal)
- Specific numbers/data in opening?
- First sentence length (<20 words preferred)
- First paragraph grabs attention vs. eases in?

### 5. Actionability

Business books succeed when readers DO something after each chapter.

**Action Item Quality:**

- **Specific:** "Open a new document and write your Master Prompt"
- **Vague:** "Think about how you might use AI differently"
- **Missing:** No action item at all

**Checks:**

- Action item present in every chapter
- Contains concrete verb (create, write, list, schedule, open, send)
- Includes time frame ("this week", "Monday morning", "in 30 minutes")
- Numbered steps preferred over prose
- Measurable outcome stated

### 6. Authority & Evidence

Readers trust books backed by evidence, not just opinions.

**Evidence Types:**

- Named sources (studies, books, researchers)
- Specific statistics with attribution
- Named real-world examples (companies, people)
- Personal experience with specific details
- Frameworks with clear structure

**Checks:**

- Data points per chapter (target: 3-5)
- Source citations per chapter
- Ratio of claims to evidence
- Personal anecdotes with specific details vs. vague references
- "Research shows..." without naming the research

### 7. Narrative Progression

The book should build complexity progressively.

**Checks:**

- Concept dependency — does Ch.N reference concepts from Ch.N-1?
- Forward references ("we'll explore this in Chapter X")
- Callbacks ("as we saw in Chapter X")
- Part-level coherence — chapters within a part share theme
- Complexity escalation — later chapters can assume earlier knowledge

### 8. Repetition & Freshness

**Checks:**

- Overused phrases (same phrase >3 times across chapters)
- Repeated examples (same story told twice)
- Framework re-explanation (redefining a concept already defined)
- Transition staleness ("In this chapter, we'll..." every chapter)
- Filler phrases ("It's important to note that", "At the end of the day")

## Severity Levels

| Level    | Meaning                                      | Action        |
| -------- | -------------------------------------------- | ------------- |
| CRITICAL | Undermines book's credibility or readability | Must fix      |
| MAJOR    | Reduces engagement or clarity significantly  | Should fix    |
| MINOR    | Style preference or minor quality issue      | Nice to fix   |
| INFO     | Observation, potential improvement           | For awareness |

## Usage

```bash
python3 skills/editorial-analysis/scripts/analyze_editorial.py path/to/project
python3 skills/editorial-analysis/scripts/analyze_editorial.py --category voice path/to/project
python3 skills/editorial-analysis/scripts/analyze_editorial.py --chapter ch01 path/to/project
```

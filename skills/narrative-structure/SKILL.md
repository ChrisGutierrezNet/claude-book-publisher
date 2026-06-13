---
name: narrative-structure
description: |
  Narrative arc and story structure validation for nonfiction business books.
  Ensures progressive complexity, proper callbacks, and coherent part-level themes.
---

# Narrative Structure

## Book-Level Arc (Nonfiction Business)

A business book should follow a transformation arc:

```
Problem Recognition → Framework Introduction → Skill Building → Mastery → Independence
```

| Phase              | Chapters | Reader State                    |
| ------------------ | -------- | ------------------------------- |
| **Awareness**      | 1-3      | "I'm doing this wrong"          |
| **Assessment**     | 4-6      | "Here's where I actually stand" |
| **Foundation**     | 7-10     | "I can build basic workflows"   |
| **Sophistication** | 11-16    | "I understand nuance and risk"  |
| **Scaling**        | 17-19    | "I can bring others along"      |
| **Creation**       | 20-23    | "I can build with AI"           |
| **Integration**    | 24-28    | "This is part of who I am"      |

## Part-Level Coherence

Each part should:

- Open with a clear theme statement
- Build toward a part-level conclusion
- Connect to the next part's theme

## Chapter-Level Narrative

Each chapter should:

1. Open with tension (problem, story, surprise)
2. Build understanding progressively
3. Provide proof (evidence, examples)
4. Address resistance (objections)
5. Close with action (what to do next)

## Cross-References

**Forward References:** "We'll explore this in Chapter X" — builds anticipation.
**Callbacks:** "As we saw in Chapter X" — reinforces learning.
**Target:** At least 1 cross-reference per chapter after Chapter 3.

## Concept Dependencies

Later chapters should build on earlier ones. Flag:

- Concepts used without prior introduction
- Chapters that could be read in any order (lack of progression)
- Redundant explanations of previously covered material

## Usage

```bash
python3 skills/editorial-analysis/scripts/analyze_editorial.py --category narrative path/to/project
```

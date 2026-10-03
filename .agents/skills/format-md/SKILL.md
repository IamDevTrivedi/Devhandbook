---
name: format-md
description: >-
  Format a markdown document to this repo's house style: title-case headings,
  strict heading hierarchy (no level jump greater than one), no premature line
  breaks in prose, code blocks wrapped to fit the PDF build, bold pseudo-headings
  converted to real ATX headings, YAML frontmatter preserved byte-for-byte.
  Use whenever the user says "format" a markdown doc/README
  (e.g. "format this markdown doc", "format topics/lld/README.md").
---

# format-md — house-style markdown formatter

Reformats a markdown document to the house style below. These documents are the
source for the automated PDF pipeline (`convertor/`), so code blocks must fit the
page width of the compiled PDF.

## Input

- The user must supply a **path to the markdown file** (the "reference"). One or
  more paths are accepted.
- If no path is given, ask which file to format. Do not guess or pick a file
  yourself.

## Rules (in priority order)

### 1. Frontmatter Formatting

The Frontmatter of each `README.md` follows the strict structure as below

```md
---
title: "<Topic Name>"
---
```

If the file starts with a YAML frontmatter block (`---` … `---`), preserve it byte-for-byte. No key reordering, no re-quoting, no whitespace changes.

If the file does not contain a YAML frontmatter block, flag it to the user and add relevant frontmatter to the document depending on the content of the document.

### 2. Headings use Title Case

- Capitalize the first and last word, plus every word except the _small words_:
  articles (`a`, `an`, `the`), coordinating conjunctions (`and`, `but`, `or`,
  `nor`, `for`, `so`, `yet`), and short prepositions (`of`, `in`, `on`, `at`,
  `to`, `by`, `up`, `as`, `via`, `per`, `with`, `from`, `into`, `over`) —
  unless one of them is the first or last word.
- Keep acronyms fully uppercase: `API`, `HTTP`, `URL`, `SQL`, `LLD`, `HLD`,
  `OOP`, `SOLID`, …
- Never alter code spans inside headings: `` `useState` `` stays as-is.
- Strip bold/italic markers from heading text — headings must be plain
  (`## **Cache**` → `## Cache`).

### 3. Strict heading hierarchy

- A heading may be **at most one level deeper** than the heading before it:
  `H1→H2→H3→H2→H1` is fine; `H1→H3` is not (demote the `H3` to `H2`).
- Moving _up_ any number of levels (`H4→H1`) is always fine.
- Fix violations by **demoting the offending heading** — never by promoting
  earlier headings or renumbering the whole document.
- The very first heading in the file may start at any level; the rule only
  governs increases.

### 4. Bold pseudo-headings become real headings

A paragraph that is only a bold phrase (e.g. `**Choosing a Database**`) and
functions as a section title must become an ATX heading:

- Pick the level from context: normally **one level deeper than the heading of
  the section it opens** (a bold title under an `H2` section → `H3`).
- The result must still satisfy rule 3.
- Remove the `**` markers.
- Bold text that is just emphasis inside a sentence is NOT a heading — leave it.

### 5. No premature line breaks in prose

- A paragraph must be a single line. Join hard-wrapped lines into one, separated
  by a single space.
- Also join wrapped continuation lines of list items (keep the list marker and
  indentation).
- Do NOT touch: code fences, tables, blockquotes (joining within the same quote
  block is OK if it is one paragraph), HTML blocks, frontmatter.
- A line ending in two trailing spaces is an _intentional_ markdown line break —
  keep it.

### 6. Code blocks must fit the PDF page

The PDF build (pandoc + xelatex, 1in margins) truncates long code lines.

- No line inside a fenced code block may exceed **78 characters**.
- Wrap longer lines at points that are safe for the language, keeping the code's
  meaning identical:
  - shell: break after `|`, `&&`, `||`, or add a `\` continuation
  - Python: break after commas / inside brackets, or use implicit continuation;
    re-indent consistently
  - JS/TS/Java/etc.: break after commas, operators, or dots; re-indent
  - URLs or long strings that cannot be broken safely: leave them and flag them
    in the final report (truncation risk) instead of corrupting the code
- Never change what the code does — wrapping is the only allowed edit.
- 78 is a default. If the user gives a different width budget, use that instead.

### 7. Everything else stays intact

No rewording, no re-paragraphing, no link/emphasis/list-style normalization, no
whitespace churn beyond what rules 1–7 require. The diff should be explainable
line by line.

## Procedure

1. Read the whole file (use chunked reads for large files — never format from a
   partial view).
2. Apply rules 1–6 with `Edit`, section by section. Prefer several small,
   targeted edits over rewriting the whole file.
3. Run the checker and fix everything it reports:
   ```bash
   python3 .agents/skills/format-md/scripts/check.py <file>
   ```
   (Add `--max-code-width N` if the user gave a different width budget.)
4. Report a short summary: counts of headings recased, heading levels demoted,
   bold-titles converted to headings, paragraphs joined, code lines wrapped,
   plus any lines that could not be wrapped safely.

## Checker

`scripts/check.py` validates a formatted file: heading-level jumps, title-case
violations, bold pseudo-headings, oversized code lines, and premature prose
line breaks. It is a safety net — apply judgment first, then let it catch what
you missed. Exit code is non-zero if any issue remains.

#!/usr/bin/env python3
"""Check a markdown file against the format-md house style.

Usage:
    python3 check.py FILE [--max-code-width N]

Exit code 0 = clean, 1 = issues found. It is a safety net — the human/agent
applies judgment first, this catches what was missed.

Checks:
  - heading level jumps greater than one
  - title-case violations in heading text
  - bold markers in headings / bold-only pseudo-headings
  - code lines exceeding the PDF-safe width
  - premature line breaks inside prose paragraphs and wrapped list items
"""
from __future__ import annotations

import argparse
import re
import sys

SMALL_WORDS = {
    "a", "an", "the",
    "and", "but", "or", "nor", "for", "so", "yet",
    "of", "in", "on", "at", "to", "by", "up", "as", "via", "per", "vs",
    "with", "from", "into", "over",
}

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_RE = re.compile(r"^\s*([-*+]|\d{1,9}[.)])\s")
BOLD_ONLY_RE = re.compile(r"^\*\*[^*]+\*\*:?\s*$")
STRIP_PUNCT = ".,:;!?()[]{}\"'"


def word_case_problem(word: str, is_edge: bool) -> str | None:
    """Return an issue description for a title-case violation, else None."""
    w = word.strip(STRIP_PUNCT)
    if not w:
        return None
    lower = w.lower()
    if lower in SMALL_WORDS:
        # small words are lowercase except at the edges
        return None if (is_edge or w[0].islower()) else f"small word {w!r} should be lowercase"
    if w.isupper() or any(c.isdigit() for c in w) or not w[0].isalpha():
        # acronym / contains a digit / code-ish / non-alpha — skip
        return None
    if w[0].islower():
        return f"word {w!r} should be capitalized"
    return None


def check_heading(title: str, lineno: int, issues: list[str]) -> None:
    if "**" in title or title.startswith("__"):
        issues.append(f"{lineno}: heading contains bold markers: {title!r}")
    # Ignore code spans and emphasis (italic) spans for the case check: rule 7
    # says non-heading content stays intact, so we don't title-case inside them.
    stripped = re.sub(r"`[^`]*`", "", title)
    stripped = re.sub(r"[_*][^_*]+[_*]", "", stripped)
    words = stripped.split()
    for idx, word in enumerate(words):
        problem = word_case_problem(word, idx == 0 or idx == len(words) - 1)
        if problem:
            issues.append(f"{lineno}: title case: {problem} (heading: {title!r})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--max-code-width", type=int, default=78)
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    issues: list[str] = []

    # Skip frontmatter (--- ... --- at the very top).
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() not in ("---", "..."):
            i += 1
        i += 1  # past the closing fence

    in_code = False
    fence_char = ""
    in_table = False
    prev_level = 0
    prev_kind: str | None = None
    prev_lineno = 0
    para_start = 0  # line number where the current paragraph/list-run began

    def kind(line: str) -> str:
        s = line.strip()
        if not s:
            return "blank"
        if HEADING_RE.match(line):
            return "heading"
        if FENCE_RE.match(line):
            return "fence"
        if LIST_RE.match(line):
            return "list"
        if s.startswith("|"):
            return "table"
        if re.match(r"^---+\s*$", s):
            return "hr"
        if s.startswith(">"):
            return "quote"
        if s.startswith("<"):
            return "html"
        return "prose"

    while i < len(lines):
        lineno = i + 1
        line = lines[i]

        if in_code:
            close = re.fullmatch(r"\s*(`{3,}|~{3,})\s*", line)
            if close and close.group(1)[0] == fence_char:
                in_code = False
            elif len(line) > args.max_code_width:
                issues.append(
                    f"{lineno}: code line is {len(line)} chars (max {args.max_code_width})"
                )
            i += 1
            continue

        k = kind(line)

        if k == "fence":
            fence_char = FENCE_RE.match(line).group(1)[0]
            in_code = True
        elif k == "heading":
            m = HEADING_RE.match(line)
            level, title = len(m.group(1)), m.group(2)
            if prev_level and level > prev_level + 1:
                issues.append(f"{lineno}: heading jumps H{prev_level} -> H{level}: {title!r}")
            check_heading(title, lineno, issues)
            prev_level = level
        elif k == "prose":
            if BOLD_ONLY_RE.match(line.strip()):
                issues.append(f"{lineno}: bold-only line, possible pseudo-heading: {line.strip()!r}")
            if prev_kind == "prose" and not lines[prev_lineno - 1].endswith("  "):
                issues.append(f"{lineno}: premature line break (paragraph started at line {para_start})")
            elif prev_kind == "list" and line.startswith((" ", "\t")):
                issues.append(f"{lineno}: possible wrapped list-item continuation (item started at line {para_start})")
            else:
                para_start = lineno
        elif k == "list":
            para_start = lineno
        elif k == "table":
            if not in_table:
                in_table = True
            para_start = 0
        else:  # blank, quote, html, hr
            if in_table:
                in_table = False
            para_start = 0

        prev_kind = k
        prev_lineno = lineno
        i += 1

    if issues:
        print(f"{args.file}: {len(issues)} issue(s):")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print(f"{args.file}: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
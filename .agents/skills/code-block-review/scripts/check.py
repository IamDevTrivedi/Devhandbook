#!/usr/bin/env python3
"""Deterministically check the fenced code blocks in a markdown file.

Usage:
    python3 check.py FILE

Reports (does NOT fix — the code-block-review skill does that):
  - code fences with no language tag
  - code that writes to stdout with no following output block
  - output blocks that are empty
  - mermaid syntax problems (static / structural)

Exit code 0 = no issues, 1 = issues found.
"""
from __future__ import annotations

import argparse
import re
import sys

# Languages we treat as code that can produce stdout.
CODE_LANGS = {
    "cpp", "c++", "cc", "cxx", "c", "java", "python", "py", "py3",
    "javascript", "js", "typescript", "ts", "bash", "sh", "shell", "zsh",
    "go", "rust", "rs", "ruby", "rb", "swift", "kotlin", "csharp", "cs",
}

# Fence languages that denote a plain-text output block.
OUTPUT_LANGS = {"text", "output", "plain", "plaintext", "console", "stdout", "txt"}

# stdout-producing constructs per language (case-insensitive match).
STDOUT_RE = {
    frozenset(("cpp", "c++", "cc", "cxx", "c")): re.compile(
        r"\b(std::cout|cout|std::cerr|cerr|std::clog|clog)\s*(<<)?\s*"
        r"|\b(printf|fprintf|puts|putchar)\s*\("
    ),
    frozenset(("java",)): re.compile(
        r"\bSystem\.(out|err)\.(print|println|printf)\s*\("
    ),
    frozenset(("python", "py", "py3")): re.compile(
        r"\b(print|sys\.stdout\.write|sys\.stderr\.write)\s*\("
    ),
    frozenset(("javascript", "js", "typescript", "ts", "node")): re.compile(
        r"\b(console\.(log|info|warn|error|debug))\s*\("
        r"|\bprocess\.stdout\.write\s*\("
    ),
    frozenset(("bash", "sh", "shell", "zsh")): re.compile(
        r"(^|\s)(echo|printf|cat|head|tail|ls|grep|awk|sed)\b"
    ),
}

MERMAID_TYPES = {
    "flowchart", "flowchart-v2", "graph", "sequenceDiagram", "classDiagram",
    "classDiagram-v2", "stateDiagram", "stateDiagram-v2", "erDiagram", "gantt",
    "pie", "journey", "mindmap", "timeline", "gitGraph", "quadrantChart",
    "block-beta", "sankey-beta", "xychart-beta", "C4Context", "C4Container",
    "C4Component", "C4Dynamic", "C4Deployment", "info",
}

FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_+-]*)\s*$")
FENCE_CLOSE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")

PAIR_MAP = {"{": "}", "[": "]", "(": ")"}
OPEN = set(PAIR_MAP)
CLOSE = set(PAIR_MAP.values())

# Match a class-declaration opening line "class <Name> {" in a classDiagram block.
# If we see this, we look at the following non-blank line — if it is just "}",
# the class is empty (invalid: use "class <Name>" with no braces).
CLASS_OPEN_RE = re.compile(r"^\s*class\s+(\w+)\s*\{\s*$")
CLASS_CLOSE_ONLY_RE = re.compile(r"^\s*\}\s*$")


def stdout_issue(line: str, lang: str) -> bool:
    """True if this code line writes to stdout (best effort)."""
    langs = frozenset((lang,))
    for key, pat in STDOUT_RE.items():
        if langs <= key or langs & key:
            return bool(pat.search(line))
    return False


def mermaid_issues(block: str, start_line: int) -> list[str]:
    """Static/structural validation of a mermaid block. Returns issue strings."""
    issues: list[str] = []
    lines = [ln for ln in block.split("\n")]
    first = next((ln.strip() for ln in lines if ln.strip()), "")

    if not first:
        issues.append(f"{start_line}: empty mermaid block")
        return issues

    # 1) valid diagram type declaration
    m = re.match(r"^([A-Za-z][A-Za-z0-9-]*)(\s|$)", first)
    if not m:
        issues.append(f"{start_line}: mermaid block has no diagram type declaration")
    elif m.group(1) not in MERMAID_TYPES:
        issues.append(
            f"{start_line}: unknown mermaid diagram type {m.group(1)!r}"
        )

    # 2) balanced delimiters and quoted labels
    stack: list[str] = []
    quote: str | None = None
    for idx, ln in enumerate(lines, start=start_line):
        i = 0
        while i < len(ln):
            ch = ln[i]
            if quote:
                if ch == quote:
                    if i + 1 < len(ln) and ln[i + 1] == quote:
                        i += 2  # escaped quote
                        continue
                    quote = None
                elif ch == "\\":
                    i += 2
                    continue
            elif ch in ("'", '"'):
                quote = ch
            elif ch in OPEN:
                stack.append(ch)
            elif ch in CLOSE:
                if not stack or PAIR_MAP[stack[-1]] != ch:
                    issues.append(f"{idx}: mismatched '{ch}' in mermaid block")
                    return issues
                stack.pop()
            i += 1
    if quote:
        issues.append(f"{start_line}: unterminated quoted label in mermaid block")
    if stack:
        issues.append(f"{start_line}: unbalanced delimiters (unclosed: {''.join(stack)})")

    # 3) classDiagram: flag "class <Name> { ... }" with empty body as invalid.
    #    Correct form for an empty class is "class <Name>" with no braces.
    if m and m.group(1) in ("classDiagram", "classDiagram-v2"):
        i = 0
        while i < len(lines):
            open_match = CLASS_OPEN_RE.match(lines[i])
            if open_match:
                # Look at subsequent non-blank lines: if the first is just "}",
                # this is an empty class — invalid.
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == "":
                        continue
                    if CLASS_CLOSE_ONLY_RE.match(lines[j]):
                        issues.append(
                            f"{start_line + i}: empty-class declaration has invalid "
                            f"braces (use 'class {open_match.group(1)}' without "
                            f"'{{}}')"
                        )
                    break
            i += 1

    return issues


def extract_blocks(text: str) -> list[dict]:
    """Return fenced blocks: {lang, start, content, char}."""
    blocks: list[dict] = []
    lines = text.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        m = FENCE_OPEN_RE.match(lines[i])
        if m:
            fence_char = m.group(1)[0]
            lang = m.group(2)
            start = i + 1
            content: list[str] = []
            i += 1
            while i < n:
                c = FENCE_CLOSE_RE.match(lines[i])
                if c and c.group(1)[0] == fence_char:
                    break
                content.append(lines[i])
                i += 1
            # i is now on the closing fence (or past EOF if unclosed)
            blocks.append(
                {"lang": lang, "start": start, "content": "\n".join(content),
                 "char": fence_char}
            )
        i += 1
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        text = fh.read()

    blocks = extract_blocks(text)
    issues: list[str] = []

    for bi, b in enumerate(blocks):
        lang = b["lang"].lower()
        start = b["start"]
        content = b["content"]

        # ---- check 1: language tag present (unless it's an output block) ----
        is_output = lang in OUTPUT_LANGS
        if not lang and not is_output:
            issues.append(f"{start}: code fence has no language tag")
            continue

        # ---- check 2: stdout -> output block must follow ----
        if lang in CODE_LANGS or (lang == "" or lang in OUTPUT_LANGS):
            writes_stdout = False
            for ln in content.split("\n"):
                if stdout_issue(ln, lang):
                    writes_stdout = True
                    break
            if writes_stdout:
                # look for an output block among the next blocks
                following = blocks[bi + 1:]
                out_block = None
                for nxt in following:
                    nl = nxt["lang"].lower()
                    if nl in CODE_LANGS or nl in MERMAID_TYPES:
                        break  # a code/mermaid block interrupts; stop looking
                    if nl in OUTPUT_LANGS or (nl == "" and nxt is following[0]):
                        out_block = nxt
                        break
                if out_block is None:
                    issues.append(
                        f"{start}: this code writes to stdout but no output block "
                        f"follows it"
                    )
                elif out_block["content"].strip() == "":
                    issues.append(f"{out_block['start']}: output block is empty")

        # ---- check 3: mermaid syntax ----
        if lang in {"mermaid", "mmd"}:
            issues.extend(mermaid_issues(content, start))

    if issues:
        print(f"{args.file}: {len(issues)} issue(s):")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print(f"{args.file}: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())

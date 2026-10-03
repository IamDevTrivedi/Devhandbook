---
name: code-block-review
description: >-
  Review the fenced code blocks in a markdown document: every code fence must
  declare its language, any code that writes to stdout must have a matching
  output code block (added/corrected if missing or wrong), and mermaid blocks
  are statically validated.
  Use whenever the user says "code-block-review" and gives a markdown file
  (e.g. "code-block-review topics/lld/README.md").
---

# code-block-review — code fences, outputs, pointers, mermaid

Reviews every fenced code block in a markdown document and fixes or reports the
issues below. Works on the same documents the PDF pipeline (`convertor/`)
compiles, so accurate, well-tagged fences matter.

## Input

- The user supplies a **path to the markdown file** to review. If none is
  given, ask which file. Do not pick one yourself.

## Checks (apply in this order)

### 1. Code fences must declare a language

- Every fenced code block must carry a language tag: `cpp`, `java`, `python`,
  `js`, `bash`, `mermaid`, etc. A bare ` ``` ` with no language is an issue.
- **Exception:** the _output_ blocks from check 2 are exempt — they are meant
  to be plain text (see check 2 for their expected tag).
- **Fix:** if the language is confidently inferable from the content, add it;
  otherwise report it with a suggested tag.

### 2. stdout requires a matching output block

- If a code block writes to stdout (e.g. `std::cout <<`, `printf(`, `puts(`,
  `cout<<`, `System.out.print`, `print(` in Python, `console.log`,
  `echo` in shell, …), then a fenced **output block** must immediately follow it
  showing the program's stdout.
- **Fix:** the user has authorized auto-fixing this — add the output block if
  missing, or correct it if the output is wrong or empty.
  - To get _accurate_ output, run the code when a compiler/interpreter is
    available and the block is complete enough to run. Otherwise derive the
    output by careful trace and mark it as best-effort.
  - Tag output blocks `text` (or `output`) so they are not confused with code.

### 3. Mermaid blocks are statically validated

- For `mermaid` blocks, check the syntax structurally (no rendering):
  - the first non-blank line declares a valid diagram type
    (`flowchart`/`graph`, `sequenceDiagram`, `classDiagram`, `stateDiagram`/
    `stateDiagram-v2`, `erDiagram`, `gantt`, `pie`, `journey`, `mindmap`,
    `timeline`, `gitGraph`, `quadrantChart`, `block-beta`, `sankey-beta`,
    `xychart-beta`, `C4Context`, …)
  - braces `{}`, brackets `[]`, parens `()` and quoted labels are balanced
    and closed
  - edge statements look well-formed (e.g. `A --> B`, `A -->|label| B`)
  - for `classDiagram`, flag `class <Name> {}` (empty braces) as invalid.
    The correct syntax for an empty class is `class <Name>` with no braces.
    Empty braces are syntactically wrong in mermaid even though they look
    balanced; report and fix by removing the `{}`.

- **Report** syntax errors with line numbers. Fix only obvious, safe typos;
  otherwise surface the issue.

### 4. Everything else is untouched

Only the code-fence-related changes above are made. Do not edit prose, headings,
or the meaning of any code outside the fences.

## Procedure

1. Read the whole file (chunked reads for large files).
2. Run the checker to get a baseline:
   ```bash
   python3 .agents/skills/code-block-review/scripts/check.py <file>
   ```
3. Address each finding with `Edit`:
   - missing/incorrect language tags (check 1)
   - add or correct output blocks (check 2) — run code when feasible
   - fix obvious mermaid syntax errors (check 3)
4. Re-run the checker until the output-block and mermaid categories are clean.
5. Report a summary: blocks reviewed, language tags added, output blocks
   added/corrected, mermaid errors found/fixed, and any output that was
   best-effort rather than run.

## Checker

`scripts/check.py` deterministically extracts every fenced block and reports:
fences missing a language, stdout-writing blocks without a following output
block, empty output blocks, and mermaid syntax problems. It does **not** run
code or fix anything — the agent does that per the procedure above. Exit code
is non-zero if issues remain.

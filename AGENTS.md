# Guidelines for AI Agents

Instructions for AI coding agents working in this repository.

## Repository Overview

### Intent of the Repository

DevHandbook is a knowledge base of computer-science study notes. Content is authored in Markdown under `topics/` and is the single source of truth. A CI pipeline (`.github/workflows/sync-compiled.yml`) automatically compiles every `topics/*/README.md` to a PDF and force-pushes the result to a separate `compiled` branch — agents and authors edit Markdown only; PDFs are a derived artifact.

### Folder Structure

A short tour of the tracked tree. Each folder has a single responsibility; cross-reference the section below for the rules that govern it.

#### `.agents/skills/`

Local skills live in `.agents/skills/`. Each skill is a self-contained package with its own `SKILL.md` describing purpose, rules, and invocation. When the user prompts a task, check whether a skill in `.agents/skills/` applies. If yes, load and use it. If not, continue with the task as normal.

Read the skill's `SKILL.md` before running it; the rules there are authoritative.

#### `.github/`

Holds the single workflow `workflows/sync-compiled.yml`. It runs on every push to `main`, renders each `topics/*/README.md` to PDF via the `convertor/` pipeline, and force-pushes everything as a single squashed commit to the orphan branch `compiled`. `complied` is CI-owned; do not edit it manually. `workflows/sync-compiled.yml` mirrors the origin main branch to the orphan compiled branch, replacing all the markdown files under `topics/` with their PDF equivalents. The workflow is triggered by pushes to `main`.

#### `convertor/`

The PDF build environment. `convert.sh` wraps pandoc + xelatex + mermaid-filter; `Dockerfile` builds the image; `docker-compose.yml` mounts `./workdir` as `/data`; `puppeteer-config.json` configures chromium. `workdir/.gitkeep` is the volume mount point — never commit other files from there.

#### `topics/`

One folder per topic. Each folder contains `README.md` (the source content) and a `.gitkeep`. No PDFs ever live on `main`; the CI emits them only on the `compiled` branch.

Example: `topics/docker/README.md` is the Markdown source for the Docker topic. The CI pipeline renders it to PDF and force-pushes it to `compiled`.

## How Changes Flow

- Any edits `topics/<topic_name>/README.md` on `main` gets pushed to the repo.
- CI builds the converter image, renders every `topics/*/README.md` to PDF, and force-pushes them as a single squashed commit to the orphan branch `compiled`.
- You do not push to `compiled`, do not open PRs against it, and do not need to re-run CI manually for a normal edit.

```
edit topics/*/README.md  →  push main  →  CI builds PDF  →  compiled branch updated
```

## Version-Control Rules

These rules apply to every VCS action — read them again before any commit.

- NEVER run `git add`, `git commit`, or `git push` without explicit permission from the user.
- Never stage, commit, or force-push to the `compiled` branch.
- Never use `git push --force` on any shared branch unless the user explicitly asks for it.
- Before committing, present exactly what you intend to stage and wait for approval.
- Leave the working tree and index exactly as the user set them unless instructed otherwise.

## Hard Don'ts

- Do not edit the `compiled` branch (CI-owned, orphan, force-pushed).
- Do not commit PDFs to `main`.
- Do not modify `convertor/**/*` without the user's instruction.
- Do not rephrase prose in topic READMEs unless the user asked for an edit to that specific text.
- Do not bump versions of pinned tooling (e.g. `@mermaid-js/mermaid-cli@11.16.0`, `texlive/texlive:latest`) without asking.

#!/bin/bash
set -euo pipefail

INPUT="${1:-input.md}"
OUTPUT="${2:-output.pdf}"

# Set NUMBER_SECTIONS=false (env var) to get unnumbered headings.
# Numbered is the default, matching the original setup.
NUMBER_SECTIONS="${NUMBER_SECTIONS:-false}"

if [ ! -f "$INPUT" ]; then
    echo "Input file not found: $INPUT (looked in $(pwd), which should be your mounted volume)" >&2
    exit 1
fi

PANDOC_ARGS=(
    "$INPUT"
    -o "$OUTPUT"
    --pdf-engine=xelatex
    --template=/opt/template.tex
    --toc
    --toc-depth=6
    --syntax-highlighting=tango
    --filter=mermaid-filter
    --standalone
    -V geometry:margin=1in
    -V colorlinks=true
)

if [ "$NUMBER_SECTIONS" = "true" ]; then
    PANDOC_ARGS+=(--number-sections -V secnumdepth=5)
fi

pandoc "${PANDOC_ARGS[@]}"

echo "Done -> $OUTPUT"

#!/usr/bin/env bash
# Generates a 2-up side-by-side A4 printable sheet (Landscape)
# containing two copies of mapa_cartosul_2026.pdf
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

INPUT_PDF="mapa_cartosul_2026.pdf"
OUTPUT_PDF="mapa_cartosul_2026_2up.pdf"
OUTPUT_PNG="mapa_cartosul_2026_2up.png"

if [ ! -f "${INPUT_PDF}" ]; then
    echo "Error: ${INPUT_PDF} not found." >&2
    exit 1
fi

echo "Composing 2-up side-by-side A4 sheet from ${INPUT_PDF}..."
pdfjam "${INPUT_PDF}" '1,1' --nup 2x1 --landscape --paper a4paper --outfile "${OUTPUT_PDF}"
pdftoppm -png -r 200 -singlefile "${OUTPUT_PDF}" "${OUTPUT_PDF%.pdf}"

echo "Done! Generated:"
echo "  - PDF: ${OUTPUT_PDF}"
echo "  - PNG: ${OUTPUT_PNG}"

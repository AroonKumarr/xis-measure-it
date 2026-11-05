#!/usr/bin/env bash
# ==============================================================================
# XIS Measure It — Production Measurement & Live Loom Demonstration Launcher
# Assessment Version 2.0 (Candidate: Aroon Kumar)
#
# Usage:
#   bash run_loom_demo.sh <path_to_photograph>
# Example:
#   bash run_loom_demo.sh fresh_photo.jpg
#   bash run_loom_demo.sh measurement/fresh_captures/IMG_8164.JPG
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

IMAGE_PATH="${1:-}"

if [[ -z "${IMAGE_PATH}" ]]; then
    echo "======================================================================"
    echo " ERROR: No input photograph specified."
    echo " Usage:"
    echo "   bash run_loom_demo.sh <path_to_photo.jpg|path_to_photo.heic>"
    echo " Example:"
    echo "   bash run_loom_demo.sh fresh_photo.jpg"
    echo "   bash run_loom_demo.sh measurement/fresh_captures/IMG_8164.JPG"
    echo "======================================================================"
    exit 1
fi

if [[ ! -f "${IMAGE_PATH}" ]]; then
    echo "======================================================================"
    echo " ERROR: File not found: ${IMAGE_PATH}"
    echo " Please capture a photo with your iPhone 15 Pro, transfer it to your"
    echo " Mac, and place it at the specified path."
    echo "======================================================================"
    exit 1
fi

# Detect Python interpreter
PYTHON_BIN=""
if [[ -f "${SCRIPT_DIR}/venv/bin/python3" ]]; then
    PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python3"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "ERROR: python3 interpreter not found. Please install Python 3.11+."
    exit 1
fi

# Execute the production measurement pipeline
"${PYTHON_BIN}" "${SCRIPT_DIR}/measurement/measure.py" --image "${IMAGE_PATH}"
EXIT_CODE=$?

if [[ ${EXIT_CODE} -eq 0 ]]; then
    STEM="$(basename "${IMAGE_PATH%.*}")"
    OVERLAY_PATH="${SCRIPT_DIR}/measurement/reports/measure_overlay_${STEM}.jpg"
    echo ""
    echo "----------------------------------------------------------------------"
    echo " [LOOM DEMO HELPER] Quick View Overlay:"
    echo "   open \"${OVERLAY_PATH}\""
    echo "----------------------------------------------------------------------"
    exit 0
else
    echo ""
    echo "----------------------------------------------------------------------"
    echo " [MEASUREMENT REFUSED] Pipeline safety gate active. Exit code: ${EXIT_CODE}"
    echo "----------------------------------------------------------------------"
    exit ${EXIT_CODE}
fi

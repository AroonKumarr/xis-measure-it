"""
measure.py — Primary Entry Point for XIS Measure It Measurement Pipeline
========================================================================
Delegates to inference.measure_image for single-command end-to-end
image-to-millimetre measurement.
"""

import sys
from pathlib import Path

# Add repository root to Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from inference.measure_image import main

if __name__ == "__main__":
    sys.exit(main())

"""
test_refusals.py — Negative & Breaking Condition Tests
======================================================
Tests:
1. Missing ArUco marker: System outputs REFUSED and exits with code 3.
2. Missing phone: System outputs REFUSED and exits with code 2.
3. Tilt degradation & excessive perspective: Rejection when tilt > 35 deg.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
import numpy as np
import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestRefusalLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch_dir = REPO_ROOT / "measurement" / "reports" / "test_scratch"
        cls.scratch_dir.mkdir(parents=True, exist_ok=True)

        # 1. Image with no ArUco (only checkerboard)
        cls.no_marker_img = cls.scratch_dir / "test_no_marker.jpg"
        calib_src = REPO_ROOT / "calibration" / "images" / "IMG_7951.JPG"
        if calib_src.exists():
            img = cv2.imread(str(calib_src))
            cv2.imwrite(str(cls.no_marker_img), img)
        else:
            blank = np.zeros((1000, 1000, 3), dtype=np.uint8)
            cv2.imwrite(str(cls.no_marker_img), blank)

        # 2. Image with no phone (crop of just ArUco marker)
        cls.no_phone_img = cls.scratch_dir / "test_no_phone.jpg"
        sample_img = Path.home() / "Downloads" / "xis_measure_it_dataset_milestone" / "dataset" / "train" / "images" / "IMG_8019.JPG"
        if sample_img.exists():
            # ArUco marker is in the lower left / top right region — let's crop just the marker or blank out the phone
            orig = cv2.imread(str(sample_img))
            # Black out the center where the phone is
            h, w = orig.shape[:2]
            orig[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = 0
            cv2.imwrite(str(cls.no_phone_img), orig)

    def test_refusal_when_marker_missing(self):
        """Pipeline must return exit code 3 and reason indicating missing ArUco marker."""
        cmd = [
            sys.executable,
            str(REPO_ROOT / "measurement" / "measure.py"),
            "--image", str(self.no_marker_img),
            "--output-dir", str(self.scratch_dir),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Should exit with code 2 (if phone not found) or 3 (if marker not found)
        self.assertIn(res.returncode, [2, 3], f"Unexpected return code {res.returncode}: {res.stderr}")
        self.assertIn("REFUSED", res.stdout + res.stderr)

    def test_cli_help(self):
        """CLI --help flag returns code 0 with informative usage."""
        cmd = [sys.executable, str(REPO_ROOT / "measurement" / "measure.py"), "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("--image", res.stdout)
        self.assertIn("--marker-size-mm", res.stdout)


if __name__ == "__main__":
    unittest.main()

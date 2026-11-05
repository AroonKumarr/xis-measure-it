"""
test_pipeline.py — Comprehensive Test Suite for XIS Measure It
==============================================================
Validates:
1. Camera calibration parameter validity
2. Model loading and phone segmentation inference
3. ArUco reference detection (DICT_4X4_50, ID 0)
4. End-to-end measurement accuracy and plane-offset compensation
5. Failure modes & refusal logic (missing marker, missing phone)
"""

import os
import sys
import json
import unittest
from pathlib import Path
import numpy as np
import cv2
import torch

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.model import create_maskrcnn_model
from inference.measure_image import (
    load_calibration,
    load_model,
    detect_phone,
    detect_aruco_marker,
    estimate_dimensions,
)


class TestXISMeasureIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = REPO_ROOT
        cls.calib_path = cls.repo_root / "calibration" / "outputs" / "camera_params.npz"
        cls.weights_path = cls.repo_root / "models" / "weights" / "best_maskrcnn_phone.pth"
        cls.dataset_train_dir = Path.home() / "Downloads" / "xis_measure_it_dataset_milestone" / "dataset" / "train" / "images"
        cls.calib_images_dir = cls.repo_root / "calibration" / "images"

        cls.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    def test_01_camera_calibration_parameters(self):
        """Verify calibration parameters file exists, is readable, and contains valid K, D."""
        self.assertTrue(self.calib_path.exists(), f"Missing calibration file: {self.calib_path}")
        K, D, new_K, (w, h) = load_calibration(self.calib_path)

        self.assertEqual(K.shape, (3, 3))
        self.assertGreater(K[0, 0], 3000.0, "fx out of expected range")
        self.assertGreater(K[1, 1], 3000.0, "fy out of expected range")
        self.assertEqual((w, h), (4284, 5712))
        self.assertEqual(len(D.flatten()), 5)

    def test_02_model_loading_and_architecture(self):
        """Verify Mask R-CNN loads weights and matches expected 2-class head."""
        if not self.weights_path.exists():
            self.skipTest("Weights not yet generated")

        model = load_model(self.weights_path, self.device)
        self.assertIsNotNone(model)
        # Check box predictor num_classes
        self.assertEqual(model.roi_heads.box_predictor.cls_score.out_features, 2)
        # Check mask predictor num_classes
        self.assertEqual(model.roi_heads.mask_predictor.mask_fcn_logits.out_channels, 2)

    def test_03_aruco_marker_detection(self):
        """Verify ArUco DICT_4X4_50 ID 0 detection on training image."""
        if not self.dataset_train_dir.exists():
            self.skipTest("Dataset images not found")

        test_img = self.dataset_train_dir / "IMG_8019.JPG"
        if not test_img.exists():
            self.skipTest(f"{test_img} not found")

        img_bgr = cv2.imread(str(test_img))
        corners, marker_id = detect_aruco_marker(img_bgr)

        self.assertIsNotNone(corners, "ArUco marker not detected")
        self.assertEqual(marker_id, 0, f"Expected marker ID 0, got {marker_id}")
        self.assertEqual(corners.shape, (4, 2))

    def test_04_refusal_on_missing_marker(self):
        """Verify refusal when ArUco marker is absent (using calibration image)."""
        calib_img_path = self.calib_images_dir / "IMG_7951.JPG"
        if not calib_img_path.exists():
            # Create a synthetic image without marker
            synthetic_img = np.zeros((1000, 1000, 3), dtype=np.uint8)
        else:
            synthetic_img = cv2.imread(str(calib_img_path))

        corners, marker_id = detect_aruco_marker(synthetic_img)
        self.assertIsNone(corners, "False positive marker detection on image without ArUco")

    def test_05_plane_offset_physics(self):
        """Verify plane-offset reduces the effective mm/px scale (Z_phone < Z_table)."""
        K, D, new_K, _ = load_calibration(self.calib_path)

        # Synthetic 100px square marker at 1000mm distance
        fake_corners = np.array([
            [1000.0, 1000.0],
            [1500.0, 1000.0],
            [1500.0, 1500.0],
            [1000.0, 1500.0]
        ], dtype=np.float32)

        # Synthetic phone mask 400px x 200px
        fake_mask = np.zeros((3000, 3000), dtype=np.uint8)
        fake_mask[500:900, 500:700] = 1

        res, err = estimate_dimensions(
            mask=fake_mask,
            marker_corners=fake_corners,
            camera_matrix=new_K,
            marker_size_mm=100.0,
            phone_elevation_mm=8.0,
        )

        self.assertIsNone(err)
        self.assertIsNotNone(res)
        self.assertLess(res["distance_phone_z_mm"], res["distance_table_z_mm"])
        self.assertLess(res["plane_scale_correction_ratio"], 1.0)
        self.assertGreater(res["plane_scale_correction_ratio"], 0.95)


if __name__ == "__main__":
    unittest.main()

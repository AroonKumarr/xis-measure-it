"""
tilt_analysis.py — Systematic Breaking Condition Experiment (Assessment Item 8)
==============================================================================
Evaluates measurement error degradation as camera tilt angle increases (0° to 45°).
Generates degradation table and summary metrics for docs/Objectives.md.
"""

import json
import math
import sys
from pathlib import Path
import cv2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from inference.measure_image import (
    load_calibration,
    load_model,
    detect_phone,
    detect_aruco_marker,
    estimate_dimensions,
)


def run_tilt_analysis():
    print("=" * 70)
    print("XIS Measure It — Camera Tilt Degradation Experiment (Item 8)")
    print("=" * 70)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    calib_path = REPO_ROOT / "calibration" / "outputs" / "camera_params.npz"
    weights_path = REPO_ROOT / "models" / "weights" / "best_maskrcnn_phone.pth"
    reports_dir = REPO_ROOT / "measurement" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not weights_path.exists():
        print(f"ERROR: Model weights not found: {weights_path}", file=sys.stderr)
        return 1

    K, D, new_K, _ = load_calibration(calib_path)
    model = load_model(weights_path, device)

    # Search through all available images in the milestone dataset
    dataset_root = Path.home() / "Downloads" / "xis_measure_it_dataset_milestone" / "dataset"
    all_images = sorted(list(dataset_root.glob("*/*/*.JPG")))

    results = []
    NOMINAL_L = 157.0
    NOMINAL_W = 72.0

    print(f"Scanning {len(all_images)} images for varying tilt perspectives...")
    for img_path in all_images:
        raw_bgr = cv2.imread(str(img_path))
        if raw_bgr is None:
            continue

        undist_bgr = cv2.undistort(raw_bgr, K, D, None, new_K)
        corners, marker_id = detect_aruco_marker(undist_bgr)
        if corners is None:
            continue

        # SolvePnP for tilt angle
        s = 100.0
        obj_pts = np.array([
            [-s / 2.0,  s / 2.0, 0.0],
            [ s / 2.0,  s / 2.0, 0.0],
            [ s / 2.0, -s / 2.0, 0.0],
            [-s / 2.0, -s / 2.0, 0.0]
        ], dtype=np.float32)

        success, rvec, tvec = cv2.solvePnP(obj_pts, corners.astype(np.float32), new_K, None)
        if not success:
            continue

        R, _ = cv2.Rodrigues(rvec)
        cos_tilt = abs(R[2, 2])
        tilt_deg = math.degrees(math.acos(min(1.0, max(-1.0, cos_tilt))))

        # Detect phone
        undist_rgb = cv2.cvtColor(undist_bgr, cv2.COLOR_BGR2RGB)
        mask, _, conf = detect_phone(model, undist_rgb, device, conf_thresh=0.5)
        if mask is None:
            continue

        # Estimate dimensions without tilt refusal filter (allow max_tilt up to 90 deg)
        metrics, err = estimate_dimensions(
            mask=mask,
            marker_corners=corners,
            camera_matrix=new_K,
            marker_size_mm=100.0,
            phone_elevation_mm=8.0,
            max_tilt_deg=90.0,
        )
        if err is not None:
            continue

        err_l = abs(metrics["length_mm"] - NOMINAL_L)
        err_w = abs(metrics["width_mm"] - NOMINAL_W)
        mae = (err_l + err_w) / 2.0

        results.append({
            "filename": img_path.name,
            "tilt_deg": round(tilt_deg, 2),
            "z_mm": metrics["distance_table_z_mm"],
            "length_mm": metrics["length_mm"],
            "width_mm": metrics["width_mm"],
            "length_error_mm": round(err_l, 2),
            "width_error_mm": round(err_w, 2),
            "mae_mm": round(mae, 2),
            "refused_under_35deg_policy": tilt_deg > 35.0,
        })

    # Sort by tilt angle
    results.sort(key=lambda x: x["tilt_deg"])

    # Bucket into tilt bins
    bins = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50)]
    bin_stats = []

    print("\n" + "=" * 75)
    print(f"{'Tilt Range':<15} {'Sample Count':<14} {'Mean L-Err (mm)':<18} {'Mean W-Err (mm)':<18} {'Mean MAE (mm)':<15}")
    print("-" * 75)

    for low, high in bins:
        in_bin = [r for r in results if low <= r["tilt_deg"] < high]
        if in_bin:
            mean_l = float(np.mean([r["length_error_mm"] for r in in_bin]))
            mean_w = float(np.mean([r["width_error_mm"] for r in in_bin]))
            mean_mae = float(np.mean([r["mae_mm"] for r in in_bin]))
            bin_stats.append({
                "range": f"{low}° - {high}°",
                "count": len(in_bin),
                "mean_l_err_mm": round(mean_l, 2),
                "mean_w_err_mm": round(mean_w, 2),
                "mean_mae_mm": round(mean_mae, 2),
            })
            print(f"{low}° - {high}°{'':<6} {len(in_bin):<14} {mean_l:<18.2f} {mean_w:<18.2f} {mean_mae:<15.2f}")
        else:
            bin_stats.append({
                "range": f"{low}° - {high}°",
                "count": 0,
                "mean_l_err_mm": None,
                "mean_w_err_mm": None,
                "mean_mae_mm": None,
            })
            print(f"{low}° - {high}°{'':<6} 0 (no images in bin)")

    print("-" * 75)

    out_json = reports_dir / "tilt_degradation_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_evaluated": len(results),
            "bin_statistics": bin_stats,
            "individual_runs": results,
        }, f, indent=2)

    print(f"\nSaved tilt degradation report to: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(run_tilt_analysis())

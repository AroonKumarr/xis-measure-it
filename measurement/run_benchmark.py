"""
run_benchmark.py — Comprehensive Benchmark & Empirical Verification Suite
========================================================================
Executes:
1. End-to-end measurement across Training, Validation, and Test splits.
2. Latency benchmark across multiple repeated runs (Assessment MO-2).
3. Empirical comparison: Undistorted vs. Raw images (Assessment Item 6).
4. Physical ablation: Tabletop scale vs. Plane-height offset compensation.
5. Populates measurement/results.csv and generates structured markdown summary.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np
import torch

from inference.measure_image import (
    load_calibration,
    load_model,
    detect_phone,
    detect_aruco_marker,
    estimate_dimensions,
    render_overlay,
)


NOMINAL_LENGTH_MM = 157.0
NOMINAL_WIDTH_MM = 72.0
PHONE_ELEVATION_MM = 8.0


def run_single_measurement(
    image_path: Path,
    model,
    K,
    D,
    new_K,
    device,
    apply_undistortion: bool = True,
    apply_plane_offset: bool = True,
    output_dir: Path = None,
):
    raw_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if raw_bgr is None:
        return {"status": "ERROR", "reason": f"Cannot load image {image_path}"}

    h, w = raw_bgr.shape[:2]

    # Latency timing
    t0 = time.perf_counter()

    # Step 1: Undistortion
    if apply_undistortion:
        proc_bgr = cv2.undistort(raw_bgr, K, D, None, new_K)
        cam_matrix = new_K
    else:
        proc_bgr = raw_bgr
        cam_matrix = K

    proc_rgb = cv2.cvtColor(proc_bgr, cv2.COLOR_BGR2RGB)

    # Step 2: Phone Segmentation
    mask, box, conf = detect_phone(model, proc_rgb, device, conf_thresh=0.5)
    if mask is None:
        return {
            "status": "REFUSED",
            "reason": "Phone not detected",
            "filename": image_path.name,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    # Step 3: ArUco Detection
    corners, marker_id = detect_aruco_marker(proc_bgr)
    if corners is None:
        return {
            "status": "REFUSED",
            "reason": "ArUco marker not detected",
            "filename": image_path.name,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    # Step 4: Metric Estimation
    elevation = PHONE_ELEVATION_MM if apply_plane_offset else 0.0
    metrics, err = estimate_dimensions(
        mask=mask,
        marker_corners=corners,
        camera_matrix=cam_matrix,
        marker_size_mm=100.0,
        phone_elevation_mm=elevation,
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    if err is not None:
        return {
            "status": "REFUSED",
            "reason": err,
            "filename": image_path.name,
            "latency_ms": elapsed_ms,
        }

    # Step 5: Render Overlay
    overlay_path_str = ""
    if output_dir is not None:
        overlay = render_overlay(
            proc_bgr, mask, box, corners, marker_id, metrics, conf
        )
        suffix = "undist" if apply_undistortion else "raw"
        if not apply_plane_offset:
            suffix += "_no_offset"
        out_file = output_dir / f"overlay_{image_path.stem}_{suffix}.jpg"
        cv2.imwrite(str(out_file), overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])
        overlay_path_str = str(out_file)

    err_l = abs(metrics["length_mm"] - NOMINAL_LENGTH_MM)
    err_w = abs(metrics["width_mm"] - NOMINAL_WIDTH_MM)

    return {
        "status": "SUCCESS",
        "filename": image_path.name,
        "undistorted": apply_undistortion,
        "plane_offset": apply_plane_offset,
        "length_mm": metrics["length_mm"],
        "width_mm": metrics["width_mm"],
        "aspect_ratio": metrics["aspect_ratio"],
        "length_error_mm": round(err_l, 2),
        "width_error_mm": round(err_w, 2),
        "length_error_pct": round(err_l / NOMINAL_LENGTH_MM * 100, 2),
        "width_error_pct": round(err_w / NOMINAL_WIDTH_MM * 100, 2),
        "distance_z_mm": metrics["distance_table_z_mm"],
        "tilt_deg": metrics["marker_tilt_deg"],
        "phone_confidence": round(conf, 4),
        "latency_ms": elapsed_ms,
        "overlay_path": overlay_path_str,
    }


def main():
    print("=" * 75)
    print("XIS Measure It — Comprehensive Benchmark & Empirical Verification Suite")
    print("=" * 75)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Compute Device: {device}")

    calib_path = REPO_ROOT / "calibration" / "outputs" / "camera_params.npz"
    weights_path = REPO_ROOT / "models" / "weights" / "best_maskrcnn_phone.pth"
    reports_dir = REPO_ROOT / "measurement" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not weights_path.exists():
        print(f"ERROR: Model weights not found at {weights_path}", file=sys.stderr)
        return 1

    K, D, new_K, _ = load_calibration(calib_path)
    model = load_model(weights_path, device)
    print("Loaded camera calibration and Mask R-CNN model.\n")

    dataset_root = Path.home() / "Downloads" / "xis_measure_it_dataset_milestone" / "dataset"
    train_dir = dataset_root / "train" / "images"
    val_dir = dataset_root / "val" / "images"
    test_dir = dataset_root / "test" / "images"

    # Select representative test images across splits
    test_cases = [
        ("train", train_dir / "IMG_8019.JPG"),
        ("train", train_dir / "IMG_8022.JPG"),
        ("train", train_dir / "IMG_8030.JPG"),
        ("train", train_dir / "IMG_8035.JPG"),
        ("train", train_dir / "IMG_8072.JPG"),
        ("val", val_dir / "IMG_7993.JPG"),
        ("val", val_dir / "IMG_8001.JPG"),
        ("val", val_dir / "IMG_8010.JPG"),
        ("val", val_dir / "IMG_8015.JPG"),
        ("val", val_dir / "IMG_8018.JPG"),
        ("test", test_dir / "IMG_8057.JPG"),
        ("test", test_dir / "IMG_8061.JPG"),
        ("test", test_dir / "IMG_8065.JPG"),
        ("test", test_dir / "IMG_8147.JPG"),
        ("test", test_dir / "IMG_8153.JPG"),
    ]

    all_results = []
    comparison_results = []

    print(f"{'Split':<6} {'Filename':<14} {'Length (mm)':<12} {'Width (mm)':<12} {'Ratio':<7} {'L-Err':<8} {'W-Err':<8} {'Tilt':<6} {'Latency':<8} {'Status'}")
    print("-" * 95)

    for split, img_path in test_cases:
        if not img_path.exists():
            print(f"Skipping missing: {img_path}")
            continue

        # Standard pipeline (Undistorted + Plane Offset)
        res = run_single_measurement(
            img_path, model, K, D, new_K, device,
            apply_undistortion=True,
            apply_plane_offset=True,
            output_dir=reports_dir,
        )
        res["split"] = split
        all_results.append(res)

        if res["status"] == "SUCCESS":
            print(
                f"{split:<6} {res['filename']:<14} "
                f"{res['length_mm']:>7.1f} mm    "
                f"{res['width_mm']:>7.1f} mm    "
                f"{res['aspect_ratio']:>5.2f}  "
                f"{res['length_error_mm']:>5.1f} mm  "
                f"{res['width_error_mm']:>5.1f} mm  "
                f"{res['tilt_deg']:>4.1f}° "
                f"{res['latency_ms']:>6.1f}ms "
                f"{res['status']}"
            )

            # Empirical Undistortion comparison (Raw vs Undistorted)
            raw_res = run_single_measurement(
                img_path, model, K, D, new_K, device,
                apply_undistortion=False,
                apply_plane_offset=True,
                output_dir=None,
            )

            # Plane offset ablation (Undistorted without offset)
            no_offset_res = run_single_measurement(
                img_path, model, K, D, new_K, device,
                apply_undistortion=True,
                apply_plane_offset=False,
                output_dir=None,
            )

            comparison_results.append({
                "filename": res["filename"],
                "split": split,
                "undist_length": res["length_mm"],
                "raw_length": raw_res.get("length_mm", np.nan),
                "no_offset_length": no_offset_res.get("length_mm", np.nan),
                "undist_width": res["width_mm"],
                "raw_width": raw_res.get("width_mm", np.nan),
                "no_offset_width": no_offset_res.get("width_mm", np.nan),
                "undist_l_err": res["length_error_mm"],
                "raw_l_err": raw_res.get("length_error_mm", np.nan),
                "no_offset_l_err": no_offset_res.get("length_error_mm", np.nan),
            })
        else:
            print(f"{split:<6} {res.get('filename', img_path.name):<14} REFUSED: {res.get('reason')}")

    print("-" * 95)

    # Latency benchmark across 5 repeated runs
    print("\nRunning Latency Benchmark (5 repeated executions on same image)...")
    latencies = []
    bench_img = train_dir / "IMG_8019.JPG"
    for i in range(5):
        t_start = time.perf_counter()
        _ = run_single_measurement(
            bench_img, model, K, D, new_K, device,
            apply_undistortion=True,
            apply_plane_offset=True,
            output_dir=None,
        )
        lat = (time.perf_counter() - t_start) * 1000
        latencies.append(lat)
        print(f"  Run {i+1}: {lat:.1f} ms")

    med_lat = float(np.median(latencies))
    mean_lat = float(np.mean(latencies))
    std_lat = float(np.std(latencies))
    print(f"Median Pipeline Latency: {med_lat:.1f} ms (Mean: {mean_lat:.1f} ± {std_lat:.1f} ms)")

    # Write results.csv
    csv_path = REPO_ROOT / "measurement" / "results.csv"
    fieldnames = [
        "split", "filename", "status", "length_mm", "width_mm",
        "aspect_ratio", "length_error_mm", "width_error_mm",
        "length_error_pct", "width_error_pct", "distance_z_mm",
        "tilt_deg", "phone_confidence", "latency_ms", "undistorted",
        "plane_offset", "overlay_path", "reason"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    print(f"\nSaved benchmark results to: {csv_path}")

    # Save summary report JSON
    valid_success = [r for r in all_results if r["status"] == "SUCCESS"]
    if valid_success:
        lengths = [r["length_mm"] for r in valid_success]
        widths = [r["width_mm"] for r in valid_success]
        l_errs = [r["length_error_mm"] for r in valid_success]
        w_errs = [r["width_error_mm"] for r in valid_success]
        l_pcts = [r["length_error_pct"] for r in valid_success]
        w_pcts = [r["width_error_pct"] for r in valid_success]

        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_tested": len(test_cases),
            "total_success": len(valid_success),
            "nominal_target": {"length_mm": NOMINAL_LENGTH_MM, "width_mm": NOMINAL_WIDTH_MM},
            "mean_measured": {"length_mm": round(float(np.mean(lengths)), 2), "width_mm": round(float(np.mean(widths)), 2)},
            "mae_mm": {"length": round(float(np.mean(l_errs)), 2), "width": round(float(np.mean(w_errs)), 2)},
            "mpe_pct": {"length": round(float(np.mean(l_pcts)), 2), "width": round(float(np.mean(w_pcts)), 2)},
            "latency_ms": {"median": round(med_lat, 1), "mean": round(mean_lat, 1), "std": round(std_lat, 1)},
            "comparisons": comparison_results,
        }
        sum_path = reports_dir / "benchmark_summary.json"
        with open(sum_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved benchmark summary to: {sum_path}")

        print("\n" + "=" * 75)
        print(f"BENCHMARK SUMMARY:")
        print(f"  Length MAE: {summary['mae_mm']['length']} mm ({summary['mpe_pct']['length']}%)")
        print(f"  Width  MAE: {summary['mae_mm']['width']} mm ({summary['mpe_pct']['width']}%)")
        print(f"  Median Latency: {med_lat:.1f} ms")
        print("=" * 75)

    return 0


if __name__ == "__main__":
    sys.exit(main())

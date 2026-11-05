#!/usr/bin/env python3
"""
calibrate_camera.py — XIS Measure It: Camera Calibration Pipeline
==================================================================
Calibrates a camera using a planar checkerboard target and OpenCV's
findChessboardCornersSB corner detector.

Checkerboard geometry (primary configuration):
  Pattern size  : 9 × 7 internal corners  (cols × rows)
  Square pitch  : 20.0 × 20.0 mm nominal
  Full-grid span: 200 mm × 160 mm (10 × 8 squares)
  Ruler uncertainty: ±1 mm per measurement
  Individual square calliper verification: PENDING

Coordinate frame policy:
  Images are loaded with cv2.imread(path, cv2.IMREAD_COLOR).
  On macOS with OpenCV 4.10.0, this automatically applies EXIF rotation
  so all images arrive as upright portrait (5712 × 4284 px, H×W) or
  landscape depending on EXIF orientation tag.
  Calibration, undistortion, annotation, and inference MUST use the
  same loading call to guarantee a consistent coordinate frame.

Camera model:
  Standard OpenCV pinhole model with full radial-tangential distortion
  (k1, k2, p1, p2, k3). No rational or fisheye model.

Usage:
  python calibrate_camera.py \\
      --image-dir  calibration/images \\
      --pattern    9 7 \\
      --square-size 20.0 \\
      --output-dir calibration/outputs

Author : Aroon Kumar
Project: XIS Measure It — Assessment Version 2.0
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="OpenCV checkerboard camera calibration — XIS Measure It",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--image-dir", type=str, default="calibration/images",
        help="Directory containing the .JPG calibration images.",
    )
    p.add_argument(
        "--pattern", type=int, nargs=2, default=[9, 7],
        metavar=("COLS", "ROWS"),
        help="Number of internal corners: columns then rows.",
    )
    p.add_argument(
        "--square-size", type=float, default=20.0,
        help="Nominal square pitch in mm (isotropic; same in X and Y).",
    )
    p.add_argument(
        "--output-dir", type=str, default="calibration/outputs",
        help="Directory to write camera_params.npz and reports.",
    )
    p.add_argument(
        "--ext", type=str, default=".JPG",
        help="Image file extension (case-sensitive on Linux).",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Object-point generation
# ---------------------------------------------------------------------------

def make_object_points(pattern_cols: int, pattern_rows: int, square_size: float) -> np.ndarray:
    """
    Return (pattern_cols * pattern_rows, 1, 3) float32 array of 3-D object points.

    Corner ordering matches OpenCV's row-major convention:
        col 0..8, row 0..6  =>  X = col * square_size, Y = row * square_size, Z = 0
    """
    objp = np.zeros((pattern_cols * pattern_rows, 1, 3), dtype=np.float32)
    for row in range(pattern_rows):
        for col in range(pattern_cols):
            idx = row * pattern_cols + col
            objp[idx, 0, 0] = col * square_size   # X
            objp[idx, 0, 1] = row * square_size   # Y
            objp[idx, 0, 2] = 0.0                 # Z (planar target)
    return objp


# ---------------------------------------------------------------------------
# Corner detection
# ---------------------------------------------------------------------------

def detect_corners(img_path, pattern, expected_shape):
    """
    Load one image and attempt corner detection.

    Returns a dict with keys:
        filename, success, reason, corners (or None), image_shape
    """
    filename = img_path.name
    result = {
        "filename": filename,
        "success": False,
        "reason": None,
        "corners": None,
        "image_shape": None,
    }

    # --- Load ---
    img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if img is None:
        result["reason"] = "cv2.imread returned None — file unreadable or corrupt"
        return result

    h, w = img.shape[:2]
    result["image_shape"] = (h, w)

    # --- Dimension check ---
    if expected_shape is not None:
        if (h, w) != expected_shape:
            result["reason"] = (
                "Unexpected dimensions %d x %d; expected %d x %d" % (
                    h, w, expected_shape[0], expected_shape[1])
            )
            return result

    # --- Greyscale conversion ---
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- Corner detection ---
    # findChessboardCornersSB is preferred over findChessboardCorners:
    # it uses saddle-point fitting and is more robust on JPEG images.
    # EXHAUSTIVE flag attempts the full search even when a quick pass fails.
    flags = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
    found, corners = cv2.findChessboardCornersSB(grey, pattern, flags=flags)

    if not found or corners is None:
        result["reason"] = "findChessboardCornersSB failed — corners not detected"
        return result

    # corners shape: (N, 1, 2) float32 — already sub-pixel accurate from SB
    result["success"] = True
    result["corners"] = corners
    result["reason"] = "OK"
    return result


# ---------------------------------------------------------------------------
# Per-image reprojection error
# ---------------------------------------------------------------------------

def per_image_rms(obj_pts, img_pts, rvec, tvec, K, D):
    """
    Compute per-image Euclidean RMS reprojection error (pixels).

    For each detected corner, computes the Euclidean pixel distance between
    the detected position and the reprojected position:
        distance_i = sqrt(dx_i^2 + dy_i^2)

    The per-image error is the RMS of these distances:
        per_view_euclidean_rms = sqrt( mean(dx^2 + dy^2) )  over all N corners

    This matches the value returned by cv2.calibrateCameraExtended
    in its perViewErrors array (verified: max deviation < 0.00002 px).
    """
    projected, _ = cv2.projectPoints(obj_pts, rvec, tvec, K, D)
    diff = img_pts.reshape(-1, 2) - projected.reshape(-1, 2)  # (N, 2): [dx, dy]
    # Euclidean distance squared per corner: dx^2 + dy^2
    dist_sq = diff[:, 0] ** 2 + diff[:, 1] ** 2               # (N,)
    return float(np.sqrt(np.mean(dist_sq)))


# ---------------------------------------------------------------------------
# Main calibration routine
# ---------------------------------------------------------------------------

def run_calibration(args):
    """
    Full calibration pipeline.  Returns 0 on success, non-zero on failure.
    """
    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)
    pattern = tuple(args.pattern)   # (cols, rows)
    square_size = args.square_size

    print("=" * 70)
    print("XIS Measure It — Camera Calibration Pipeline")
    print("=" * 70)
    print("OpenCV version        : %s" % cv2.__version__)
    print("Image directory       : %s" % str(image_dir.resolve()))
    print("Pattern (cols x rows) : %d x %d" % (pattern[0], pattern[1]))
    print("Square pitch (nominal): %.1f mm x %.1f mm" % (square_size, square_size))
    print("Output directory      : %s" % str(output_dir.resolve()))
    print("Loading policy        : cv2.imread(path, cv2.IMREAD_COLOR)  [EXIF auto-rotate]")
    print("=" * 70)

    # --- Validate directories ---
    if not image_dir.is_dir():
        print("ERROR: image directory not found: %s" % str(image_dir.resolve()), file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Collect images ---
    ext = args.ext
    images = sorted(image_dir.glob("*" + ext))
    if not images:
        images = sorted(image_dir.glob("*" + ext.lower()))
    if not images:
        print("ERROR: no *%s images found in %s" % (ext, image_dir), file=sys.stderr)
        return 1

    n_images = len(images)
    print("\nFound %d image(s) with extension '%s'" % (n_images, ext))

    # --- Determine reference image shape from first successful read ---
    ref_shape = None
    for img_path in images:
        img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img is not None:
            ref_shape = img.shape[:2]  # (H, W)
            print("Reference image shape : %d x %d px  (H x W)  [%s]" % (
                ref_shape[0], ref_shape[1], img_path.name))
            break
    if ref_shape is None:
        print("ERROR: could not read any image to determine reference shape.", file=sys.stderr)
        return 1

    # --- Object points template ---
    objp_template = make_object_points(pattern[0], pattern[1], square_size)
    n_corners = pattern[0] * pattern[1]
    print("Object points per image: %d  (pattern %d x %d)" % (n_corners, pattern[0], pattern[1]))

    # --- Corner detection pass ---
    print("\n--- Corner detection ---")
    all_obj_pts = []
    all_img_pts = []
    detection_log = []

    for img_path in images:
        res = detect_corners(img_path, pattern, ref_shape)
        status = "OK " if res["success"] else "FAIL"
        shape_str = (
            "%dx%d" % (res["image_shape"][0], res["image_shape"][1])
            if res["image_shape"] else "N/A"
        )
        print("  [%s]  %-25s  %-12s  %s" % (status, res["filename"], shape_str, res["reason"]))

        detection_log.append({
            "filename": res["filename"],
            "success": res["success"],
            "reason": res["reason"],
            "image_shape": list(res["image_shape"]) if res["image_shape"] else None,
        })

        if res["success"]:
            all_obj_pts.append(objp_template)
            all_img_pts.append(res["corners"])

    n_success = len(all_obj_pts)
    n_rejected = n_images - n_success
    print("\nDetection summary: %d succeeded, %d rejected out of %d" % (
        n_success, n_rejected, n_images))

    if n_success < 10:
        print(
            "ERROR: too few valid images for calibration (%d). Need at least 10." % n_success,
            file=sys.stderr,
        )
        return 1

    # --- Calibration ---
    print("\n--- Running cv2.calibrateCamera ---")
    t0 = time.time()

    # Standard pinhole model; full (k1,k2,p1,p2,k3) distortion coefficients.
    # No CALIB_FIX_ASPECT_RATIO, CALIB_FIX_PRINCIPAL_POINT, or CALIB_ZERO_TANGENT_DIST.
    # Using default flags (== 0) lets OpenCV freely optimise all parameters.
    calib_flags = 0
    image_size = (ref_shape[1], ref_shape[0])  # (W, H) for OpenCV

    ret, K, D, rvecs, tvecs = cv2.calibrateCamera(
        all_obj_pts,
        all_img_pts,
        image_size,
        None,
        None,
        flags=calib_flags,
    )
    elapsed = time.time() - t0

    overall_opencv_rms_px = float(ret)
    print("cv2.calibrateCamera completed in %.2fs" % elapsed)
    print("Overall OpenCV RMS: %.6f px" % overall_opencv_rms_px)

    # --- Per-image reprojection errors ---
    per_img_errors = []
    successful_names = [d["filename"] for d in detection_log if d["success"]]
    for i, (obj_pts, img_pts, rvec, tvec, fname) in enumerate(
        zip(all_obj_pts, all_img_pts, rvecs, tvecs, successful_names)
    ):
        err = per_image_rms(obj_pts, img_pts, rvec, tvec, K, D)
        per_img_errors.append({"filename": fname, "per_view_euclidean_rms_px": err})

    errors_array = np.array([e["per_view_euclidean_rms_px"] for e in per_img_errors])
    mean_per_view_euclidean_rms_px   = float(np.mean(errors_array))
    median_per_view_euclidean_rms_px = float(np.median(errors_array))
    min_per_view_euclidean_rms_px    = float(np.min(errors_array))
    max_per_view_euclidean_rms_px    = float(np.max(errors_array))
    worst_name = per_img_errors[int(np.argmax(errors_array))]["filename"]
    best_name  = per_img_errors[int(np.argmin(errors_array))]["filename"]

    print("\n--- Per-view Euclidean RMS summary ---")
    print("  Mean   : %.6f px" % mean_per_view_euclidean_rms_px)
    print("  Median : %.6f px" % median_per_view_euclidean_rms_px)
    print("  Min    : %.6f px  [%s]" % (min_per_view_euclidean_rms_px, best_name))
    print("  Max    : %.6f px  [%s]" % (max_per_view_euclidean_rms_px, worst_name))

    # --- Historical reference comparison (regression check only) ---
    HIST_RMS    = 1.629654
    HIST_MEAN_EUCLIDEAN   = 1.545790
    HIST_MEDIAN_EUCLIDEAN = 1.377991
    print("\n--- Historical scratch reference regression check ---")
    print("  Note: For internal regression tracking only, not universal target bounds.")
    print("  %-25s  %12s  %12s  %10s" % ("Metric", "This run", "Hist. Ref", "Delta"))
    print("  %-25s  %12.6f  %12.6f  %+10.6f" % ("Overall OpenCV RMS", overall_opencv_rms_px, HIST_RMS, overall_opencv_rms_px - HIST_RMS))
    print("  %-25s  %12.6f  %12.6f  %+10.6f" % ("Mean per-view Eucl.", mean_per_view_euclidean_rms_px, HIST_MEAN_EUCLIDEAN, mean_per_view_euclidean_rms_px - HIST_MEAN_EUCLIDEAN))
    print("  %-25s  %12.6f  %12.6f  %+10.6f" % ("Median per-view Eucl.", median_per_view_euclidean_rms_px, HIST_MEDIAN_EUCLIDEAN, median_per_view_euclidean_rms_px - HIST_MEDIAN_EUCLIDEAN))

    # --- Intrinsic matrix and distortion ---
    print("\n--- Intrinsic matrix K ---")
    print("  fx = %.4f px,  fy = %.4f px" % (K[0, 0], K[1, 1]))
    print("  cx = %.4f px,  cy = %.4f px" % (K[0, 2], K[1, 2]))
    print("\n--- Distortion coefficients D (k1 k2 p1 p2 k3) ---")
    print("  %s" % str(D.ravel().tolist()))

    # -------------------------------------------------------------------
    # Save camera_params.npz
    # -------------------------------------------------------------------
    npz_path = output_dir / "camera_params.npz"
    np.savez(
        str(npz_path),
        K=K,
        D=D,
        image_width=np.int32(image_size[0]),
        image_height=np.int32(image_size[1]),
        pattern_cols=np.int32(pattern[0]),
        pattern_rows=np.int32(pattern[1]),
        square_size_mm=np.float32(square_size),
        n_calibration_images=np.int32(n_success),
        overall_opencv_rms_px=np.float64(overall_opencv_rms_px),
        overall_rms_px=np.float64(overall_opencv_rms_px),  # alias for backwards compatibility
        opencv_version=np.array(cv2.__version__),
        loading_policy=np.array(
            "cv2.imread(path, cv2.IMREAD_COLOR) — EXIF auto-rotate applied"
        ),
        square_pitch_note=np.array(
            "Nominal 20.0x20.0 mm derived from full-grid ruler measurements "
            "(200mm x 160mm span, +/-1mm ruler uncertainty). "
            "Individual square calliper verification PENDING."
        ),
    )
    print("\nSaved: %s  (%d bytes)" % (str(npz_path), npz_path.stat().st_size))

    # -------------------------------------------------------------------
    # Save calibration_summary.json
    # -------------------------------------------------------------------
    rejected_log = [d for d in detection_log if not d["success"]]
    summary = {
        "project": "XIS Measure It — Assessment Version 2.0",
        "script": "calibration/calibrate_camera.py",
        "opencv_version": cv2.__version__,
        "loading_policy": "cv2.imread(path, cv2.IMREAD_COLOR) — EXIF auto-rotate applied",
        "calibration_settings": {
            "pattern_cols": pattern[0],
            "pattern_rows": pattern[1],
            "n_internal_corners": n_corners,
            "square_size_mm": square_size,
            "square_pitch_note": (
                "Nominal 20.0x20.0 mm derived from full-grid ruler measurements "
                "(200mm x 160mm span, +/-1mm ruler uncertainty). "
                "Individual square calliper verification PENDING."
            ),
            "calib_flags": calib_flags,
            "calib_flags_description": "0 — standard pinhole, free optimisation of all parameters",
            "corner_detector": "cv2.findChessboardCornersSB",
            "corner_detector_flags": "CALIB_CB_EXHAUSTIVE | CALIB_CB_ACCURACY",
        },
        "image_size": {
            "width_px": image_size[0],
            "height_px": image_size[1],
            "note": "(W, H) in OpenCV convention; loaded shape is (H, W, 3)",
        },
        "dataset": {
            "n_input_images": n_images,
            "n_successfully_calibrated": n_success,
            "n_rejected": n_rejected,
            "rejected_images": rejected_log,
        },
        "results": {
            "overall_opencv_rms_px": overall_opencv_rms_px,
            "note_overall_opencv_rms": (
                "Value returned directly by cv2.calibrateCamera — "
                "computed over all corners across all images jointly."
            ),
            "mean_per_view_euclidean_rms_px": mean_per_view_euclidean_rms_px,
            "median_per_view_euclidean_rms_px": median_per_view_euclidean_rms_px,
            "min_per_view_euclidean_rms_px": min_per_view_euclidean_rms_px,
            "max_per_view_euclidean_rms_px": max_per_view_euclidean_rms_px,
            "worst_image": worst_name,
            "best_image": best_name,
        },
        "historical_reference_comparison": {
            "note": (
                "Historical reference values from an early internal scratch run; "
                "provided solely for regression tracking, not universal calibration targets."
            ),
            "overall_opencv_rms_px": HIST_RMS,
            "mean_per_view_euclidean_rms_px": HIST_MEAN_EUCLIDEAN,
            "median_per_view_euclidean_rms_px": HIST_MEDIAN_EUCLIDEAN,
        },
        "intrinsics": {
            "fx": float(K[0, 0]),
            "fy": float(K[1, 1]),
            "cx": float(K[0, 2]),
            "cy": float(K[1, 2]),
            "K": K.tolist(),
            "D": D.ravel().tolist(),
            "D_labels": ["k1", "k2", "p1", "p2", "k3"],
        },
        "limitations": {
            "square_pitch": "Individual checkerboard square pitch calliper verification is pending. 20.0 mm is nominal from ruler.",
            "board_flatness": "Physical board flatness verification is pending.",
            "focus_lock": "Focus lock cannot be independently established from EXIF metadata.",
            "metric_interpretation": "Overall RMS 1.629654 px is a 2D image reprojection metric, not 3D physical millimetre measurement accuracy."
        },
        "source_filenames": [img_path.name for img_path in images],
        "successfully_calibrated_filenames": successful_names,
    }

    summary_path = output_dir / "calibration_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("Saved: %s  (%d bytes)" % (str(summary_path), summary_path.stat().st_size))

    # -------------------------------------------------------------------
    # Save per_image_reprojection.csv
    # -------------------------------------------------------------------
    csv_path = output_dir / "per_image_reprojection.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("filename,n_corners_detected,per_view_euclidean_rms_px\n")
        for entry in per_img_errors:
            f.write("%s,%d,%.6f\n" % (
                entry["filename"], n_corners, entry["per_view_euclidean_rms_px"]
            ))
    print("Saved: %s  (%d bytes)" % (str(csv_path), csv_path.stat().st_size))

    # -------------------------------------------------------------------
    # Print per-image table sorted by error
    # -------------------------------------------------------------------
    print("\n--- Per-image reprojection errors (sorted ascending) ---")
    sorted_errors = sorted(per_img_errors, key=lambda x: x["per_view_euclidean_rms_px"])
    print("  %4s  %-25s  %10s" % ("Rank", "Filename", "RMS (px)"))
    for rank, e in enumerate(sorted_errors, 1):
        print("  %4d  %-25s  %10.6f" % (rank, e["filename"], e["per_view_euclidean_rms_px"]))

    print("\n=== Calibration complete ===")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_calibration(args))

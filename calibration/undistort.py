#!/usr/bin/env python3
"""
undistort.py — XIS Measure It: Batch Image Undistortion
========================================================
Loads a calibrated camera parameter file (camera_params.npz) and applies
OpenCV lens undistortion to one or more input images.

Coordinate frame policy:
  Images are loaded with cv2.imread(path, cv2.IMREAD_COLOR).
  This matches the loading policy used during calibration, ensuring a
  consistent image coordinate frame throughout the pipeline.

Safety protections:
  1. Loads NPZ with allow_pickle=False.
  2. Validates K shape (3,3), D size 5, positive dimensions, and 0 <= alpha <= 1.
  3. Resolves all paths via pathlib.Path.resolve().
  4. Rejects identical input and output directories.
  5. Refuses to overwrite source original images under all circumstances.
  6. Refuses to overwrite existing output files by default.
  7. Provides an explicit --overwrite flag.
  8. Reopens each saved image after writing, confirms decodability and exact
     calibrated dimensions, and records verified decoded shapes.
  9. Protects undistort_report.json: refuses to overwrite without --overwrite;
     uses microsecond collision-safe exclusive creation mode ("x") if existing
     report is present, or replaces explicitly with --overwrite.
  10. Returns a non-zero exit code if any image fails or is skipped.

Author : Aroon Kumar
Project: XIS Measure It — Assessment Version 2.0
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Safe batch lens undistortion using calibrated camera parameters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--params", type=str, required=True,
        help="Path to camera_params.npz from calibrate_camera.py.",
    )
    p.add_argument(
        "--input", type=str, required=True,
        help="Path to a single image file OR a directory of images.",
    )
    p.add_argument(
        "--output-dir", type=str, required=True,
        help="Directory to write undistorted images.",
    )
    p.add_argument(
        "--ext", type=str, default=".JPG",
        help="Extension filter when --input is a directory.",
    )
    p.add_argument(
        "--alpha", type=float, default=1.0,
        help=(
            "Free scaling parameter for getOptimalNewCameraMatrix. "
            "0.0 = crop to valid pixels only; 1.0 = retain all pixels."
        ),
    )
    p.add_argument(
        "--overwrite", action="store_true", default=False,
        help="Explicitly permit overwriting existing output files in --output-dir.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Load camera parameters
# ---------------------------------------------------------------------------

def load_params(npz_path: Path):
    """
    Load and rigorously validate K, D, and image dimensions from camera_params.npz.
    Uses allow_pickle=False for security and format integrity.

    Returns (K, D, (W, H)).
    """
    if not npz_path.is_file():
        raise FileNotFoundError("camera_params.npz not found: %s" % str(npz_path.resolve()))

    # Enforce allow_pickle=False
    data = np.load(str(npz_path.resolve()), allow_pickle=False)

    required = ["K", "D", "image_width", "image_height"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError("camera_params.npz is missing required keys: %s" % missing)

    K = data["K"]
    D = data["D"]

    # Validate K shape
    if K.shape != (3, 3):
        raise ValueError("Intrinsic matrix K must have shape (3, 3); got %s" % str(K.shape))

    # Validate D size (must have exactly 5 distortion coefficients k1, k2, p1, p2, k3)
    if D.size != 5:
        raise ValueError("Distortion vector D must contain exactly 5 coefficients; got %d" % D.size)

    W = int(data["image_width"])
    H = int(data["image_height"])

    if W <= 0 or H <= 0:
        raise ValueError("Calibrated dimensions must be positive integers; got W=%d, H=%d" % (W, H))

    print("Loaded camera_params.npz (allow_pickle=False verified)")
    print("  Calibrated image size : %d x %d px  (W x H)" % (W, H))
    print("  fx=%.4f  fy=%.4f  cx=%.4f  cy=%.4f" % (K[0, 0], K[1, 1], K[0, 2], K[1, 2]))
    print("  D (k1, k2, p1, p2, k3) = %s" % str(D.ravel().tolist()))

    return K, D, (W, H)


# ---------------------------------------------------------------------------
# Undistort one image with full safety and post-write verification checks
# ---------------------------------------------------------------------------

def process_image(img_path: Path, out_path: Path, K, D, calib_size, new_K, roi, overwrite: bool) -> dict:
    """
    Validates, undistorts, writes, and re-reads one image to verify file integrity.
    Returns result dictionary with status: 'ok', 'skipped', or 'failed'.
    """
    res = {
        "filename": img_path.name,
        "input_path": str(img_path.resolve()),
        "output_path": str(out_path.resolve()),
        "status": "pending",
        "reason": None,
        "output_shape": None,
        "verified_decoded_shape": None,
        "output_bytes": 0,
    }

    # Safety check: input path cannot be identical to output path
    if img_path.resolve() == out_path.resolve():
        res["status"] = "failed"
        res["reason"] = "Refusing to overwrite original source image (input == output path)."
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    # Safety check: destination exists and overwrite not enabled
    if out_path.exists() and not overwrite:
        res["status"] = "skipped"
        res["reason"] = "Output file already exists and --overwrite was not specified."
        print("  SKIP  %s — %s" % (img_path.name, res["reason"]))
        return res

    # Load image using documented coordinate policy
    img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if img is None:
        res["status"] = "failed"
        res["reason"] = "cv2.imread returned None (unreadable or corrupted file)."
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    h, w = img.shape[:2]
    calib_w, calib_h = calib_size

    # Validate resolution matches calibration
    if (w, h) != (calib_w, calib_h):
        res["status"] = "failed"
        res["reason"] = (
            "Image dimensions (%d x %d) do not match calibrated size (%d x %d)."
            % (w, h, calib_w, calib_h)
        )
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    # Apply lens undistortion
    undistorted = cv2.undistort(img, K, D, None, new_K)

    # Validate in-memory output dimensions
    uh, uw = undistorted.shape[:2]
    if (uw, uh) != (calib_w, calib_h):
        res["status"] = "failed"
        res["reason"] = (
            "Undistorted shape (%d x %d) does not match expected (%d x %d)."
            % (uw, uh, calib_w, calib_h)
        )
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    # Write output file
    success = cv2.imwrite(str(out_path), undistorted)
    if not success:
        res["status"] = "failed"
        res["reason"] = "cv2.imwrite failed to write destination file."
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    # --- Post-write verification: reopen saved image from disk ---
    verified_img = cv2.imread(str(out_path), cv2.IMREAD_COLOR)
    if verified_img is None:
        res["status"] = "failed"
        res["reason"] = "Post-write verification failed: saved output file could not be read back by cv2.imread."
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    vh, vw = verified_img.shape[:2]
    if (vw, vh) != (calib_w, calib_h):
        res["status"] = "failed"
        res["reason"] = (
            "Post-write verification failed: decoded dimensions (%d x %d) differ from calibrated (%d x %d)."
            % (vw, vh, calib_w, calib_h)
        )
        print("  FAIL  %s — %s" % (img_path.name, res["reason"]), file=sys.stderr)
        return res

    res["status"] = "ok"
    res["output_shape"] = list(undistorted.shape)
    res["verified_decoded_shape"] = list(verified_img.shape)
    res["output_bytes"] = out_path.stat().st_size
    print("  OK    %s  ->  %s  (%d bytes, shape=%s verified)" % (
        img_path.name, out_path.name, res["output_bytes"], str(res["verified_decoded_shape"])
    ))
    return res


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Validate alpha
    if not (0.0 <= args.alpha <= 1.0):
        print("ERROR: --alpha must be between 0.0 and 1.0; got %f" % args.alpha, file=sys.stderr)
        return 1

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    params_path = Path(args.params).resolve()

    print("=" * 70)
    print("XIS Measure It — Safe Lens Undistortion Pipeline")
    print("=" * 70)
    print("Params file   : %s" % str(params_path))
    print("Input path    : %s" % str(input_path))
    print("Output dir    : %s" % str(output_dir))
    print("Alpha         : %.2f" % args.alpha)
    print("Overwrite     : %s" % str(args.overwrite))
    print("Loading policy: cv2.imread(path, cv2.IMREAD_COLOR)  [EXIF auto-rotate]")
    print("=" * 70)

    # Safety check: input directory cannot be the same as output directory
    if input_path.is_dir() and input_path == output_dir:
        print(
            "ERROR: Output directory cannot be identical to input directory: %s" % str(output_dir),
            file=sys.stderr,
        )
        return 1

    # Load and validate calibration parameters
    try:
        K, D, calib_size = load_params(params_path)
    except Exception as e:
        print("ERROR loading camera parameters: %s" % e, file=sys.stderr)
        return 1

    # Collect images
    if input_path.is_file():
        images = [input_path]
    elif input_path.is_dir():
        ext = args.ext
        images = sorted(input_path.glob("*" + ext))
        if not images:
            images = sorted(input_path.glob("*" + ext.lower()))
        if not images:
            print("ERROR: No *%s images found in %s" % (ext, str(input_path)), file=sys.stderr)
            return 1
    else:
        print("ERROR: --input is neither an existing file nor directory: %s" % str(input_path), file=sys.stderr)
        return 1

    print("\nFound %d image(s) to process." % len(images))

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Compute optimal new camera matrix and ROI
    new_K, roi = cv2.getOptimalNewCameraMatrix(K, D, calib_size, alpha=args.alpha)
    print("Optimal new camera matrix computed (alpha=%.2f):" % args.alpha)
    print("  new_fx=%.4f  new_fy=%.4f  new_cx=%.4f  new_cy=%.4f" % (
        new_K[0, 0], new_K[1, 1], new_K[0, 2], new_K[1, 2]
    ))
    print("  Valid pixel ROI (x, y, w, h): %s" % str(roi))

    # Process all images
    print("\n--- Undistorting images ---")
    results = []
    n_ok = 0
    n_skipped = 0
    n_failed = 0

    for img_path in images:
        out_path = output_dir / img_path.name
        res = process_image(
            img_path=img_path,
            out_path=out_path,
            K=K,
            D=D,
            calib_size=calib_size,
            new_K=new_K,
            roi=roi,
            overwrite=args.overwrite,
        )
        results.append(res)
        if res["status"] == "ok":
            n_ok += 1
        elif res["status"] == "skipped":
            n_skipped += 1
        else:
            n_failed += 1

    # Determine report path and enforce collision-safe exclusive creation mode ("x")
    report_default_path = output_dir / "undistort_report.json"
    report_overwritten = False
    target_report_path = None

    report_content = {
        "timestamp_iso": datetime.datetime.now().isoformat(),
        "params_file": str(params_path),
        "alpha": args.alpha,
        "calibrated_dimensions_wh": list(calib_size),
        "new_camera_matrix_K": new_K.tolist(),
        "valid_pixel_roi": list(roi),
        "total_images": len(images),
        "succeeded_count": n_ok,
        "skipped_count": n_skipped,
        "failed_count": n_failed,
        "overwrite_permitted": args.overwrite,
        "per_image_results": results,
    }

    if report_default_path.exists() and not args.overwrite:
        # Refuse to overwrite undistort_report.json without --overwrite.
        # Find a collision-safe unique filename with microsecond timestamp using exclusive creation mode ("x")
        timestamp_base = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        counter = 0
        while True:
            suffix = f"_{counter}" if counter > 0 else ""
            candidate_path = output_dir / f"undistort_report_{timestamp_base}{suffix}.json"
            try:
                with open(candidate_path, "x", encoding="utf-8") as f_rep:
                    json.dump(report_content, f_rep, indent=2)
                target_report_path = candidate_path
                break
            except FileExistsError:
                counter += 1
        print(
            "\nNOTE: %s already exists and --overwrite was not specified."
            % str(report_default_path.name)
        )
        print("Refusing to overwrite existing report. Exclusively created unique file: %s"
              % str(target_report_path.name))
    else:
        target_report_path = report_default_path
        if report_default_path.exists() and args.overwrite:
            report_overwritten = True
            with open(target_report_path, "w", encoding="utf-8") as f_rep:
                json.dump(report_content, f_rep, indent=2)
        else:
            # Use exclusive creation mode ("x") for new default report as well
            with open(target_report_path, "x", encoding="utf-8") as f_rep:
                json.dump(report_content, f_rep, indent=2)

    print("Saved processing report: %s (%d bytes)" % (str(target_report_path), target_report_path.stat().st_size))

    print("\n--- Summary ---")
    print("  Succeeded : %d" % n_ok)
    print("  Skipped   : %d" % n_skipped)
    print("  Failed    : %d" % n_failed)

    # Return nonzero exit code if any image failed or was skipped
    if n_failed > 0 or n_skipped > 0:
        print("Execution completed with warnings/errors (non-zero exit).", file=sys.stderr)
        return 1

    print("\n=== Undistortion completed successfully ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

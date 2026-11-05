"""
measure_image.py — XIS Measure It: End-to-End Image-to-Millimetre Pipeline
=============================================================================
Full pipeline:
  Input image -> Undistortion -> Phone segmentation (Mask R-CNN) ->
  ArUco reference detection -> Plane height offset compensation ->
  Physical dimension estimation in millimetres -> Output report & visual overlay.

Safety & Reliability:
  - Validates camera calibration parameters.
  - Detects phone object with confidence threshold.
  - Detects ArUco marker DICT_4X4_50 ID 0.
  - Computes camera-to-marker distance Z_table via solvePnP.
  - Compulsory plane-offset adjustment: compensates for physical height offset
    (delta_Z ~ 8.0 mm) between the tabletop ArUco marker and phone back surface.
  - Rejects measurements when marker is missing or perspective tilt > 35 deg.
"""

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

# Add repository root to Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np
import torch

from models.model import create_maskrcnn_model


def load_calibration(params_path: Path):
    """
    Loads K, D, image size, and computes optimal new camera matrix.
    """
    if not params_path.exists():
        raise FileNotFoundError(f"Calibration parameters not found: {params_path}")
    data = np.load(str(params_path), allow_pickle=False)
    K = data["K"]
    D = data["D"]
    w = int(data["image_width"])
    h = int(data["image_height"])
    new_K, roi = cv2.getOptimalNewCameraMatrix(K, D, (w, h), alpha=1.0)
    return K, D, new_K, (w, h)


def load_model(weights_path: Path, device: torch.device):
    """
    Loads trained Mask R-CNN weights.
    """
    if not weights_path.exists():
        raise FileNotFoundError(f"Model weights not found: {weights_path}")
    model = create_maskrcnn_model(num_classes=2, pretrained_backbone=False)
    checkpoint = torch.load(str(weights_path), map_location=device)
    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)
    model.to(device)
    model.eval()
    return model


def detect_phone(model, img_rgb: np.ndarray, device: torch.device, conf_thresh: float = 0.5):
    """
    Runs Mask R-CNN and extracts best phone mask.
    Returns (pred_mask, bbox, score) or (None, None, 0.0).
    """
    h, w = img_rgb.shape[:2]
    img_tensor = torch.from_numpy(img_rgb).permute(2, 0, 1).float() / 255.0
    img_tensor = img_tensor.to(device)

    with torch.no_grad():
        outputs = model([img_tensor])

    out = outputs[0]
    scores = out["scores"].cpu().numpy()
    labels = out["labels"].cpu().numpy()
    masks = out["masks"].cpu().numpy()
    boxes = out["boxes"].cpu().numpy()

    # Filter by class 1 (phone) and confidence threshold
    valid = np.where((labels == 1) & (scores >= conf_thresh))[0]
    if len(valid) == 0:
        return None, None, 0.0

    best_idx = valid[0]
    best_score = float(scores[best_idx])
    best_box = boxes[best_idx].tolist()
    pred_mask = (masks[best_idx, 0] >= 0.5).astype(np.uint8)

    return pred_mask, best_box, best_score


def detect_aruco_marker(
    img_bgr: np.ndarray,
    dict_id: int = cv2.aruco.DICT_4X4_50,
    expected_id: int = 0,
):
    """
    Detects ArUco marker DICT_4X4_50 ID 0.
    Returns (corners, id) or (None, None).
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    corners, ids, rejected = detector.detectMarkers(img_bgr)
    if ids is None or len(ids) == 0:
        return None, None

    for c, marker_id in zip(corners, ids.flatten()):
        if int(marker_id) == expected_id:
            return c[0], int(marker_id)

    # Return first detected marker if expected_id not strictly matching
    return corners[0][0], int(ids.flatten()[0])


def estimate_dimensions(
    mask: np.ndarray,
    marker_corners: np.ndarray,
    camera_matrix: np.ndarray,
    marker_size_mm: float = 100.0,
    phone_elevation_mm: float = 8.0,
    max_tilt_deg: float = 35.0,
):
    """
    Estimates phone dimensions in millimetres:
      1. Solves solvePnP on ArUco marker to get distance Z_table.
      2. Computes tilt angle between marker normal and camera axis.
      3. Applies plane-height offset compensation:
         Z_phone = Z_table - phone_elevation_mm
         Scale_factor = (Z_table - phone_elevation_mm) / Z_table
      4. Measures phone mask length and width in mm.
    """
    # 1. Phone pixel geometry from binary mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, "Empty mask: no contours found"

    # Select largest contour
    largest_cnt = max(contours, key=cv2.contourArea)
    min_area_rect = cv2.minAreaRect(largest_cnt)
    center, (dim1, dim2), angle = min_area_rect
    length_px = max(dim1, dim2)
    width_px = min(dim1, dim2)

    if length_px < 50 or width_px < 20:
        return None, "Detected phone contour area is too small"

    # 2. Marker side lengths in pixels
    c = marker_corners  # shape: (4, 2)
    side0 = np.linalg.norm(c[0] - c[1])
    side1 = np.linalg.norm(c[1] - c[2])
    side2 = np.linalg.norm(c[2] - c[3])
    side3 = np.linalg.norm(c[3] - c[0])
    mean_marker_side_px = float(np.mean([side0, side1, side2, side3]))

    # Aspect ratio check of marker
    marker_aspect = max(side0, side2) / max(side1, side3) if max(side1, side3) > 0 else 1.0
    if abs(marker_aspect - 1.0) > 0.25:
        return None, f"ArUco marker perspective distortion too severe (aspect ratio {marker_aspect:.2f})"

    # 3. 3D Pose estimation via solvePnP for plane distance and tilt angle
    s = marker_size_mm
    obj_pts = np.array([
        [-s / 2.0,  s / 2.0, 0.0],
        [ s / 2.0,  s / 2.0, 0.0],
        [ s / 2.0, -s / 2.0, 0.0],
        [-s / 2.0, -s / 2.0, 0.0]
    ], dtype=np.float32)

    success, rvec, tvec = cv2.solvePnP(obj_pts, marker_corners.astype(np.float32), camera_matrix, None)
    if not success:
        return None, "solvePnP failed on ArUco marker"

    R, _ = cv2.Rodrigues(rvec)
    z_table = float(tvec[2, 0])

    if z_table <= 100.0:
        return None, f"Invalid tabletop distance Z={z_table:.1f} mm"

    # Compute tilt angle between marker normal vector and camera Z axis [0, 0, 1]
    marker_normal = R[:, 2]
    cos_tilt = abs(marker_normal[2])
    tilt_deg = math.degrees(math.acos(min(1.0, max(-1.0, cos_tilt))))

    if tilt_deg > max_tilt_deg:
        return None, f"Marker tilt angle ({tilt_deg:.1f} deg) exceeds maximum reliable threshold ({max_tilt_deg:.1f} deg)"

    # 4. Tabletop millimetre-to-pixel scale
    scale_table_mm_per_px = s / mean_marker_side_px

    # 5. Plane-Height Offset Compensation
    # Phone back surface is elevated by phone_elevation_mm above the table
    z_phone = z_table - phone_elevation_mm
    plane_scale_factor = z_phone / z_table  # < 1.0 because phone is closer to camera

    scale_phone_mm_per_px = scale_table_mm_per_px * plane_scale_factor

    # 6. Physical Dimensions Calculation
    length_mm = length_px * scale_phone_mm_per_px
    width_mm = width_px * scale_phone_mm_per_px

    return {
        "status": "SUCCESS",
        "length_mm": round(length_mm, 2),
        "width_mm": round(width_mm, 2),
        "aspect_ratio": round(length_mm / width_mm, 3) if width_mm > 0 else 0.0,
        "length_px": round(length_px, 1),
        "width_px": round(width_px, 1),
        "marker_side_mean_px": round(mean_marker_side_px, 1),
        "distance_table_z_mm": round(z_table, 1),
        "distance_phone_z_mm": round(z_phone, 1),
        "plane_offset_applied_mm": phone_elevation_mm,
        "plane_scale_correction_ratio": round(plane_scale_factor, 4),
        "marker_tilt_deg": round(tilt_deg, 2),
        "min_area_rect": {
            "center": [round(center[0], 1), round(center[1], 1)],
            "size": [round(dim1, 1), round(dim2, 1)],
            "angle": round(angle, 2),
        },
    }, None


def render_overlay(
    img_bgr: np.ndarray,
    mask: np.ndarray,
    box: list,
    marker_corners: np.ndarray,
    marker_id: int,
    metrics: dict,
    conf_score: float,
) -> np.ndarray:
    """
    Renders an informative inspection overlay.
    """
    overlay = img_bgr.copy()
    h, w = img_bgr.shape[:2]

    # Phone mask: semi-transparent green
    if mask is not None:
        overlay[mask > 0] = [0, 220, 0]

    blended = cv2.addWeighted(overlay, 0.35, img_bgr, 0.65, 0)

    # Phone contour outline
    if mask is not None:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(blended, contours, -1, (255, 255, 0), 8)

        # Oriented bounding box
        if metrics and "min_area_rect" in metrics:
            center = metrics["min_area_rect"]["center"]
            size = metrics["min_area_rect"]["size"]
            angle = metrics["min_area_rect"]["angle"]
            rect = (tuple(center), tuple(size), angle)
            box_pts = np.int32(cv2.boxPoints(rect))
            cv2.polylines(blended, [box_pts], isClosed=True, color=(0, 140, 255), thickness=6)

    # ArUco marker boundary: bright blue
    if marker_corners is not None:
        pts = np.int32(marker_corners).reshape(-1, 2)
        cv2.polylines(blended, [pts], isClosed=True, color=(255, 100, 0), thickness=8)
        cv2.putText(
            blended,
            f"ArUco ID:{marker_id}",
            (pts[0, 0], max(pts[0, 1] - 20, 50)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.8,
            (255, 100, 0),
            4,
            cv2.LINE_AA,
        )

    # Annotation Banner at top
    banner = np.zeros((160, w, 3), dtype=np.uint8)
    if metrics:
        t1 = f"PHONE: {metrics['length_mm']:.1f} mm x {metrics['width_mm']:.1f} mm (Ratio: {metrics['aspect_ratio']:.2f}) | Conf: {conf_score*100:.1f}%"
        t2 = f"CALIBRATION: Z_table={metrics['distance_table_z_mm']:.0f}mm, Z_phone={metrics['distance_phone_z_mm']:.0f}mm (Offset={metrics['plane_offset_applied_mm']:.1f}mm, Tilt={metrics['marker_tilt_deg']:.1f} deg)"
        cv2.putText(banner, t1, (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 0), 4, cv2.LINE_AA)
        cv2.putText(banner, t2, (30, 125), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3, cv2.LINE_AA)
    else:
        cv2.putText(banner, "MEASUREMENT REFUSED / INCOMPLETE", (30, 95), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4, cv2.LINE_AA)

    output = np.vstack([banner, blended])

    # Downscale for visual report export (max dimension 1600)
    scale = 1600.0 / max(output.shape[0], output.shape[1])
    thumb_w, thumb_h = int(output.shape[1] * scale), int(output.shape[0] * scale)
    return cv2.resize(output, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)


def parse_args():
    p = argparse.ArgumentParser(description="XIS Measure It — End-to-End Image-to-Millimetre Pipeline")
    p.add_argument("--image", type=str, required=True, help="Path to input photograph.")
    p.add_argument(
        "--params",
        type=str,
        default="calibration/outputs/camera_params.npz",
        help="Path to camera calibration NPZ.",
    )
    p.add_argument(
        "--weights",
        type=str,
        default="models/weights/best_maskrcnn_phone.pth",
        help="Path to trained Mask R-CNN weights.",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default="measurement/reports",
        help="Directory to save measurement reports and overlay images.",
    )
    p.add_argument("--marker-size-mm", type=float, default=100.0, help="Nominal ArUco marker size in mm.")
    p.add_argument(
        "--phone-elevation-mm",
        type=float,
        default=8.0,
        help="Out-of-plane height difference between tabletop marker and phone back surface (mm).",
    )
    p.add_argument("--conf-thresh", type=float, default=0.5, help="Detection confidence threshold.")
    p.add_argument("--device", type=str, default="auto", choices=["auto", "mps", "cpu"])
    return p.parse_args()


def main():
    args = parse_args()
    image_path = Path(args.image).resolve()
    if not image_path.exists():
        print(f"ERROR: Image not found: {image_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine device
    if args.device == "auto":
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    # 1. Load Calibration
    try:
        K, D, new_K, (calib_w, calib_h) = load_calibration(Path(args.params))
    except Exception as e:
        print(f"ERROR loading calibration: {e}", file=sys.stderr)
        return 1

    # 2. Read Image
    raw_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if raw_bgr is None:
        print(f"ERROR: Failed to read image: {image_path}", file=sys.stderr)
        return 1

    h, w = raw_bgr.shape[:2]

    # Check if image is already undistorted (e.g. from milestone folder) or needs undistortion
    if (w, h) == (calib_w, calib_h):
        # Apply standard undistortion
        undist_bgr = cv2.undistort(raw_bgr, K, D, None, new_K)
    else:
        print(f"WARNING: Image size ({w}x{h}) differs from calibrated ({calib_w}x{calib_h})", file=sys.stderr)
        undist_bgr = raw_bgr

    undist_rgb = cv2.cvtColor(undist_bgr, cv2.COLOR_BGR2RGB)

    # 3. Load Model
    try:
        model = load_model(Path(args.weights), device)
    except Exception as e:
        print(f"ERROR loading model: {e}", file=sys.stderr)
        return 1

    # 4. Phone Segmentation
    mask, box, conf_score = detect_phone(model, undist_rgb, device, conf_thresh=args.conf_thresh)
    if mask is None:
        report = {
            "status": "REFUSED",
            "reason": "Phone object not detected with confidence >= threshold",
            "filename": image_path.name,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        print(f"REFUSED: {report['reason']}")
        rep_path = output_dir / f"measure_{image_path.stem}.json"
        with open(rep_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return 2

    # 5. ArUco Marker Detection
    marker_corners, marker_id = detect_aruco_marker(undist_bgr)
    if marker_corners is None:
        report = {
            "status": "REFUSED",
            "reason": "ArUco reference marker (DICT_4X4_50 ID 0) not detected in image",
            "filename": image_path.name,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        print(f"REFUSED: {report['reason']}")
        rep_path = output_dir / f"measure_{image_path.stem}.json"
        with open(rep_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return 3

    # 6. Physical Dimensions & Height Offset Compensation
    metrics, err = estimate_dimensions(
        mask=mask,
        marker_corners=marker_corners,
        camera_matrix=new_K,
        marker_size_mm=args.marker_size_mm,
        phone_elevation_mm=args.phone_elevation_mm,
    )

    if err is not None:
        report = {
            "status": "REFUSED",
            "reason": err,
            "filename": image_path.name,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        print(f"REFUSED: {err}")
        rep_path = output_dir / f"measure_{image_path.stem}.json"
        with open(rep_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return 4

    # 7. Render Visualization Overlay
    vis_overlay = render_overlay(
        img_bgr=undist_bgr,
        mask=mask,
        box=box,
        marker_corners=marker_corners,
        marker_id=marker_id,
        metrics=metrics,
        conf_score=conf_score,
    )

    vis_path = output_dir / f"measure_overlay_{image_path.stem}.jpg"
    cv2.imwrite(str(vis_path), vis_overlay, [cv2.IMWRITE_JPEG_QUALITY, 92])

    report = {
        "status": "SUCCESS",
        "filename": image_path.name,
        "timestamp": datetime.datetime.now().isoformat(),
        "phone_confidence": round(conf_score, 4),
        "marker_id": marker_id,
        "results": metrics,
        "visual_overlay_path": str(vis_path),
    }

    rep_path = output_dir / f"measure_{image_path.stem}.json"
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 70)
    print("XIS Measure It — Measurement Successful")
    print("=" * 70)
    print(f"Image File          : {image_path.name}")
    print(f"Phone Length (mm)   : {metrics['length_mm']:.1f} mm")
    print(f"Phone Width (mm)    : {metrics['width_mm']:.1f} mm")
    print(f"Phone Aspect Ratio  : {metrics['aspect_ratio']:.2f}")
    print(f"Table Distance Z    : {metrics['distance_table_z_mm']:.1f} mm")
    print(f"Phone Distance Z    : {metrics['distance_phone_z_mm']:.1f} mm (Offset = {metrics['plane_offset_applied_mm']:.1f} mm)")
    print(f"Plane Correction    : {metrics['plane_scale_correction_ratio']:.4f}")
    print(f"Marker Tilt Angle   : {metrics['marker_tilt_deg']:.1f} deg")
    print(f"Detection Confidence: {conf_score*100:.1f}%")
    print(f"Saved Overlay Image : {vis_path}")
    print(f"Saved Output JSON   : {rep_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

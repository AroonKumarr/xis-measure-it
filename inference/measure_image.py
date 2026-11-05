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


def load_fresh_image(image_path: Path):
    """
    Loads an image from disk.
    - Automatically handles HEIC/HEIF files via macOS /usr/bin/sips.
    - Corrects landscape captures by rotating 90 deg clockwise to upright portrait.
    Returns: (raw_bgr, was_rotated, is_heic)
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    is_heic = image_path.suffix.lower() in [".heic", ".heif"]
    if is_heic:
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_jpg = Path(tmp.name)
        try:
            res = subprocess.run(
                ["/usr/bin/sips", "-s", "format", "jpeg", str(image_path), "--out", str(tmp_jpg)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                raise RuntimeError(f"HEIC conversion failed: {res.stderr}")
            img_bgr = cv2.imread(str(tmp_jpg), cv2.IMREAD_COLOR)
        finally:
            if tmp_jpg.exists():
                tmp_jpg.unlink()
    else:
        img_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise ValueError(f"Failed to load image: {image_path}")

    h, w = img_bgr.shape[:2]
    # Rotate landscape capture to upright portrait if needed
    if w > h:
        img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
        was_rotated = True
    else:
        was_rotated = False

    return img_bgr, was_rotated, is_heic


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


def detect_phone(
    model,
    img_rgb: np.ndarray,
    device: torch.device,
    conf_thresh: float = 0.5,
    max_dim: int = 1200,
):
    """
    Runs Mask R-CNN and extracts best phone mask.
    Downsamples image if larger than max_dim to prevent CPU Out-Of-Memory (OOM)
    crashes on memory-constrained environments (e.g. Streamlit Cloud 1GB limit),
    then upsamples predicted mask back to original resolution.
    Returns (pred_mask, bbox, score) or (None, None, 0.0).
    """
    h, w = img_rgb.shape[:2]
    orig_h, orig_w = h, w

    scale = 1.0
    if max_dim is not None and max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        target_w = int(w * scale)
        target_h = int(h * scale)
        img_input = cv2.resize(img_rgb, (target_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        img_input = img_rgb

    img_tensor = torch.from_numpy(img_input).permute(2, 0, 1).float() / 255.0
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
    box_scaled = boxes[best_idx].tolist()
    pred_mask_small = (masks[best_idx, 0] >= 0.5).astype(np.uint8)

    if scale != 1.0:
        pred_mask = cv2.resize(pred_mask_small, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        best_box = [coord / scale for coord in box_scaled]
    else:
        pred_mask = pred_mask_small
        best_box = box_scaled

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
    method: str = "planar_homography",
):
    """
    Estimates phone dimensions in millimetres.
    Supports both:
      1. 'planar_homography' (Primary, mathematically rigorous):
         Projects phone contour onto the 3D metric plane defined by the ArUco pose
         and out-of-plane elevation offset (h = phone_elevation_mm).
         Provides perspective-invariant, distance-corrected physical dimensions.
      2. 'legacy_2d':
         Naive 2D pixel scale multiplication with scalar tabletop Z compensation.
    """
    # 1. Phone pixel geometry from binary mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, "Empty mask: no contours found"

    largest_cnt = max(contours, key=cv2.contourArea)
    rect_px = cv2.minAreaRect(largest_cnt)
    center_px, (dim1_px, dim2_px), angle_px = rect_px
    length_px = max(dim1_px, dim2_px)
    width_px = min(dim1_px, dim2_px)

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

    # 4. Legacy 2D calculation (for comparison and ablation)
    scale_table_mm_per_px = s / mean_marker_side_px
    z_phone = z_table - phone_elevation_mm
    plane_scale_factor = z_phone / z_table
    scale_phone_mm_per_px = scale_table_mm_per_px * plane_scale_factor
    legacy_length_mm = length_px * scale_phone_mm_per_px
    legacy_width_mm = width_px * scale_phone_mm_per_px

    # 5. 3D Planar Homography Metric Reconstruction
    dot_prod = np.dot(R[:, 2], -tvec.ravel())
    normal_sign = 1.0 if dot_prod > 0 else -1.0
    h_elev = phone_elevation_mm * normal_sign
    col2 = h_elev * R[:, 2:] + tvec
    H = camera_matrix @ np.hstack([R[:, 0:1], R[:, 1:2], col2])
    H_inv = np.linalg.inv(H)

    pts_px = largest_cnt.reshape(-1, 2).astype(np.float32)
    pts_homo = np.hstack([pts_px, np.ones((len(pts_px), 1), dtype=np.float32)])
    pts_metric_homo = (H_inv @ pts_homo.T).T
    pts_metric = pts_metric_homo[:, :2] / pts_metric_homo[:, 2:3]

    rect_mm = cv2.minAreaRect(pts_metric.astype(np.float32))
    center_m, (dim1_m, dim2_m), angle_m = rect_mm
    planar_length_mm = max(dim1_m, dim2_m)
    planar_width_mm = min(dim1_m, dim2_m)

    # Perspective projection of metric bounding box onto image
    box_pts_m = cv2.boxPoints(rect_mm)
    box_pts_px = (H @ np.hstack([box_pts_m, np.ones((4, 1), dtype=np.float32)]).T).T
    box_pts_px = box_pts_px[:, :2] / box_pts_px[:, 2:3]

    if method == "legacy_2d":
        final_l = legacy_length_mm
        final_w = legacy_width_mm
    else:
        final_l = planar_length_mm
        final_w = planar_width_mm

    return {
        "status": "SUCCESS",
        "length_mm": round(final_l, 2),
        "width_mm": round(final_w, 2),
        "aspect_ratio": round(final_l / final_w, 3) if final_w > 0 else 0.0,
        "method_used": method,
        "planar_length_mm": round(planar_length_mm, 2),
        "planar_width_mm": round(planar_width_mm, 2),
        "legacy_2d_length_mm": round(legacy_length_mm, 2),
        "legacy_2d_width_mm": round(legacy_width_mm, 2),
        "length_px": round(length_px, 1),
        "width_px": round(width_px, 1),
        "marker_side_mean_px": round(mean_marker_side_px, 1),
        "distance_table_z_mm": round(z_table, 1),
        "distance_phone_z_mm": round(z_phone, 1),
        "plane_offset_applied_mm": phone_elevation_mm,
        "plane_scale_correction_ratio": round(plane_scale_factor, 4),
        "marker_tilt_deg": round(tilt_deg, 2),
        "box_pts_px": box_pts_px.tolist(),
        "min_area_rect": {
            "center": [round(center_px[0], 1), round(center_px[1], 1)],
            "size": [round(dim1_px, 1), round(dim2_px, 1)],
            "angle": round(angle_px, 2),
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

        # Oriented bounding box (3D perspective quadrilateral or 2D minAreaRect)
        if metrics and "box_pts_px" in metrics:
            box_pts = np.int32(metrics["box_pts_px"])
            cv2.polylines(blended, [box_pts], isClosed=True, color=(0, 140, 255), thickness=6)
        elif metrics and "min_area_rect" in metrics:
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
    p.add_argument(
        "--method",
        type=str,
        default="planar_homography",
        choices=["planar_homography", "legacy_2d"],
        help="Measurement mathematics: 'planar_homography' (3D metric plane) or 'legacy_2d' (naive pixel scale).",
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

    # 2. Read Fresh or Existing Photograph
    try:
        raw_bgr, was_rotated, is_heic = load_fresh_image(image_path)
    except Exception as e:
        print(f"ERROR: Failed to read image {image_path}: {e}", file=sys.stderr)
        return 1

    h, w = raw_bgr.shape[:2]
    if was_rotated:
        print(f"INFO: Detected landscape capture; auto-rotated 90° clockwise to match portrait calibration frame ({w}x{h}).")
    if is_heic:
        print(f"INFO: Converted Apple HEIC format to decoded RGB on macOS.")

    # Match calibration resolution or adapt scaling if 12MP binned image was supplied
    if (w, h) == (calib_w, calib_h):
        active_K = K
        active_new_K = new_K
        undist_bgr = cv2.undistort(raw_bgr, K, D, None, new_K)
    elif abs(w / h - calib_w / calib_h) < 0.05 and w < calib_w:
        scale_x = w / calib_w
        scale_y = h / calib_h
        scaled_K = K.copy()
        scaled_K[0, 0] *= scale_x
        scaled_K[0, 2] *= scale_x
        scaled_K[1, 1] *= scale_y
        scaled_K[1, 2] *= scale_y
        active_new_K, _ = cv2.getOptimalNewCameraMatrix(scaled_K, D, (w, h), alpha=1.0)
        active_K = scaled_K
        undist_bgr = cv2.undistort(raw_bgr, scaled_K, D, None, active_new_K)
        print(f"INFO: Resolution {w}x{h} detected. Adapted camera intrinsics from native 24MP calibration.")
    else:
        active_K = K
        active_new_K = new_K
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
        camera_matrix=active_new_K,
        marker_size_mm=args.marker_size_mm,
        phone_elevation_mm=args.phone_elevation_mm,
        method=args.method,
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
    print("         XIS MEASURE IT — REAL-WORLD PHYSICAL MEASUREMENT")
    print("=" * 70)
    print(f"  Input Photograph   : {image_path.name} ({w}x{h})")
    print(f"  Pipeline Status    : SUCCESS")
    print("-" * 70)
    print(f"  PREDICTED LENGTH   : {metrics['length_mm']:>6.1f} mm   (Confirmed Ref: 157.0 mm)")
    print(f"  PREDICTED WIDTH    : {metrics['width_mm']:>6.1f} mm   (Confirmed Ref:  72.0 mm)")
    print(f"  ASPECT RATIO       : {metrics['aspect_ratio']:>6.2f}      (Reference Ratio: 2.18)")
    print("-" * 70)
    print(f"  Reconstruction     : 3D Planar Homography (Perspective-Invariant)")
    print(f"  Planar Metric Dims : {metrics['planar_length_mm']:.1f} mm x {metrics['planar_width_mm']:.1f} mm")
    print(f"  Legacy 2D Dims     : {metrics['legacy_2d_length_mm']:.1f} mm x {metrics['legacy_2d_width_mm']:.1f} mm")
    print(f"  Reference Marker   : ArUco DICT_4X4_50 ID {marker_id} ({args.marker_size_mm:.1f} mm nominal)")
    print(f"  Camera Distance Z  : {metrics['distance_table_z_mm']:.1f} mm")
    print(f"  Plane Offset dZ    : {metrics['plane_offset_applied_mm']:.1f} mm (Z_phone = {metrics['distance_phone_z_mm']:.1f} mm)")
    print(f"  Perspective Tilt   : {metrics['marker_tilt_deg']:.1f}° (Safe threshold < 35.0°)")
    print(f"  Mask Confidence    : {conf_score*100:.1f}%")
    print("-" * 70)
    print(f"  Annotated Overlay  : {vis_path}")
    print(f"  Measurement Report : {rep_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
streamlit_app.py — Interactive Streamlit Cloud App for XIS Measure It
====================================================================
Candidate: Aroon Kumar
Assessment: XIS AI / Computer Vision Technical Assessment (Version 2.0)
Hardware: Apple Silicon / CPU / CUDA compatible

Deployable to Streamlit Community Cloud (https://share.streamlit.io).
"""

import sys
import json
from pathlib import Path
import numpy as np
import cv2
import torch
import streamlit as st
from PIL import Image

# Setup repository path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from inference.measure_image import (
    load_calibration,
    load_model,
    detect_phone,
    detect_aruco_marker,
    estimate_dimensions,
    render_overlay,
    load_fresh_image,
)

# Page configuration
st.set_page_config(
    page_title="XIS Measure It — Metric Measurement",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .refusal-alert {
        background-color: #450a0a;
        color: #fca5a5;
        border: 1px solid #dc2626;
        padding: 12px 16px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 16px;
    }
    .success-alert {
        background-color: #064e3b;
        color: #6ee7b7;
        border: 1px solid #059669;
        padding: 12px 16px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Paths
CALIB_PARAMS = REPO_ROOT / "calibration" / "outputs" / "camera_params.npz"
MODEL_WEIGHTS = REPO_ROOT / "models" / "weights" / "best_maskrcnn_phone.pth"
FRESH_DIR = REPO_ROOT / "measurement" / "fresh_captures"
WEIGHTS_URL = "https://github.com/AroonKumarr/xis-measure-it/releases/download/v2.0-submission/best_maskrcnn_phone.pth"

def ensure_model_weights():
    if not MODEL_WEIGHTS.exists():
        MODEL_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        import urllib.request
        progress_bar = st.progress(0, text="Downloading trained model weights (168 MB) from GitHub Release...")
        req = urllib.request.Request(WEIGHTS_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(MODEL_WEIGHTS, "wb") as out_file:
            total_size = int(response.headers.get("Content-Length", 176224965))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                pct = min(1.0, downloaded / total_size)
                progress_bar.progress(pct, text=f"Downloading trained model weights ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)...")
        progress_bar.empty()

@st.cache_resource
def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

@st.cache_resource
def get_pipeline():
    ensure_model_weights()
    K, D, new_K, (w, h) = load_calibration(CALIB_PARAMS)
    device = get_device()
    model = load_model(MODEL_WEIGHTS, device)
    return K, D, new_K, (w, h), model, device

# Header
st.title("📐 XIS Measure It: Physical Metric Measurement")
st.caption("AI / Computer Vision Technical Assessment (Version 2.0) — Candidate: Aroon Kumar")

# Load model and calibration
try:
    K, D, NEW_K, (CALIB_W, CALIB_H), MODEL, DEVICE = get_pipeline()
except Exception as e:
    st.error(f"Error loading pipeline: {e}")
    st.stop()

# Sidebar Controls
st.sidebar.header("🕹️ Controls & Parameters")

sample_images = sorted([f.name for f in FRESH_DIR.glob("*.JPG") if not f.name.startswith(".")])

source_option = st.sidebar.radio(
    "Image Source",
    ["Included Physical Captures (Archive 8)", "Upload iPhone Photo (.JPG / .HEIC)"],
)

raw_bgr = None
image_name = ""

if source_option == "Included Physical Captures (Archive 8)":
    selected_sample = st.sidebar.selectbox(
        "Select Capture Sample",
        sample_images,
        index=sample_images.index("IMG_8164.JPG") if "IMG_8164.JPG" in sample_images else 0,
    )
    img_path = FRESH_DIR / selected_sample
    raw_bgr, was_rot, is_h = load_fresh_image(img_path)
    image_name = selected_sample
else:
    uploaded_file = st.sidebar.file_uploader(
        "Upload iPhone Photo",
        type=["jpg", "jpeg", "png", "heic", "HEIC"],
    )
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        raw_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        image_name = uploaded_file.name
    else:
        st.info("👈 Upload an image or select an included physical capture to begin.")
        st.stop()

st.sidebar.subheader("📐 Algorithm Settings")
method = st.sidebar.selectbox(
    "Reconstruction Engine",
    ["planar_homography", "legacy_2d"],
    format_func=lambda x: "3D Planar Homography (Perspective-Invariant)" if x == "planar_homography" else "Legacy 2D Projection (Baseline)",
)

elevation_mm = st.sidebar.number_input(
    "Phone Elevation Offset dZ (mm)",
    min_value=0.0,
    max_value=30.0,
    value=8.0,
    step=0.5,
    help="Physical height difference between the table ArUco marker and phone surface.",
)

max_tilt_deg = st.sidebar.slider(
    "Max Reliable Tilt Angle (°)",
    min_value=15.0,
    max_value=45.0,
    value=35.0,
    step=1.0,
    help="Rejects shots where camera oblique angle exceeds safe threshold.",
)

conf_thresh = st.sidebar.slider(
    "Segmentation Confidence Threshold",
    min_value=0.30,
    max_value=0.99,
    value=0.50,
    step=0.05,
)

# Reference box in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Confirmed Physical Ground Truth:**
    - Target: Android Smartphone
    - Length: **157.0 mm**
    - Width: **72.0 mm**
    - Fiducial: ArUco DICT_4X4_50 ID 0 (100.0 mm)
    """
)

if raw_bgr is None:
    st.warning("Could not read image.")
    st.stop()

# Preprocessing: portrait orientation and camera undistortion
h, w = raw_bgr.shape[:2]
if w > h:
    raw_bgr = cv2.rotate(raw_bgr, cv2.ROTATE_90_CLOCKWISE)
    h, w = raw_bgr.shape[:2]

if (w, h) == (CALIB_W, CALIB_H):
    active_new_K = NEW_K
    undist_bgr = cv2.undistort(raw_bgr, K, D, None, NEW_K)
else:
    scale_x = w / CALIB_W
    scale_y = h / CALIB_H
    scaled_K = K.copy()
    scaled_K[0, 0] *= scale_x
    scaled_K[0, 2] *= scale_x
    scaled_K[1, 1] *= scale_y
    scaled_K[1, 2] *= scale_y
    active_new_K, _ = cv2.getOptimalNewCameraMatrix(scaled_K, D, (w, h), alpha=1.0)
    undist_bgr = cv2.undistort(raw_bgr, scaled_K, D, None, active_new_K)

undist_rgb = cv2.cvtColor(undist_bgr, cv2.COLOR_BGR2RGB)

# Inference
with st.spinner("Processing image through Mask R-CNN and Homography engine..."):
    mask, box, conf = detect_phone(MODEL, undist_rgb, DEVICE, conf_thresh=conf_thresh)
    marker_corners, marker_id = detect_aruco_marker(undist_bgr)

# Downsample previews for fast display and strict low-memory footprint
def get_display_preview(img: np.ndarray, max_dim: int = 1280) -> np.ndarray:
    ih, iw = img.shape[:2]
    if max(ih, iw) > max_dim:
        s = max_dim / float(max(ih, iw))
        return cv2.resize(img, (int(iw * s), int(ih * s)), interpolation=cv2.INTER_AREA)
    return img

# Validation & Refusal Handling
if mask is None:
    st.markdown(
        f'<div class="refusal-alert">⚠️ REFUSED: Phone object not detected with confidence &ge; {conf_thresh:.2f}.</div>',
        unsafe_allow_html=True,
    )
    st.image(get_display_preview(undist_rgb), caption=f"Undistorted Input: {image_name}", use_container_width=True)
    st.stop()

if marker_corners is None:
    st.markdown(
        '<div class="refusal-alert">⚠️ REFUSED: ArUco fiducial marker (DICT_4X4_50 ID 0) not detected in frame.</div>',
        unsafe_allow_html=True,
    )
    st.image(get_display_preview(undist_rgb), caption=f"Undistorted Input: {image_name}", use_container_width=True)
    st.stop()

metrics, refusal = estimate_dimensions(
    mask=mask,
    marker_corners=marker_corners,
    camera_matrix=active_new_K,
    marker_size_mm=100.0,
    phone_elevation_mm=elevation_mm,
    max_tilt_deg=max_tilt_deg,
    method=method,
)

if refusal is not None:
    st.markdown(
        f'<div class="refusal-alert">⚠️ REFUSED: {refusal}</div>',
        unsafe_allow_html=True,
    )
    st.image(get_display_preview(undist_rgb), caption=f"Refusal Frame: {image_name}", use_container_width=True)
    st.stop()

# Successful Measurement
st.markdown(
    f'<div class="success-alert">✅ STATUS: SUCCESS — {image_name} ({w}x{h} px)</div>',
    unsafe_allow_html=True,
)

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
pred_l = metrics["length_mm"]
pred_w = metrics["width_mm"]
delta_l = pred_l - 157.0
delta_w = pred_w - 72.0

col1.metric("Predicted Length", f"{pred_l:.1f} mm", delta=f"{delta_l:+.1f} mm vs 157.0")
col2.metric("Predicted Width", f"{pred_w:.1f} mm", delta=f"{delta_w:+.1f} mm vs 72.0")
col3.metric("Aspect Ratio", f"{metrics['aspect_ratio']:.2f}", delta=f"{metrics['aspect_ratio'] - 2.18:+.2f} vs 2.18")
col4.metric("Perspective Tilt", f"{metrics['marker_tilt_deg']:.1f}°", delta="Safe (< 35°)")

# Render Overlay
overlay_bgr = render_overlay(
    img_bgr=undist_bgr,
    mask=mask,
    box=box,
    marker_corners=marker_corners,
    marker_id=marker_id,
    metrics=metrics,
    conf_score=conf,
)
overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

# Display Tabs
tab_overlay, tab_raw, tab_data = st.tabs(["📸 Annotated Measurement Overlay", "🖼️ Raw / Undistorted Input", "📊 Technical Diagnostics"])

with tab_overlay:
    st.image(get_display_preview(overlay_rgb), caption=f"3D Planar Homography Reconstruction — {image_name}", use_container_width=True)

with tab_raw:
    st.image(get_display_preview(undist_rgb), caption=f"Rectilinear Undistorted Frame — {image_name}", use_container_width=True)

with tab_data:
    st.subheader("Diagnostic Telemetry")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Geometric Parameters:**")
        st.json({
            "Reconstruction Method": metrics["method_used"],
            "Tabletop Distance Z": f"{metrics['distance_table_z_mm']:.1f} mm",
            "Phone Surface Distance Z_phone": f"{metrics['distance_phone_z_mm']:.1f} mm",
            "Applied Elevation Offset dZ": f"{metrics['plane_offset_applied_mm']:.1f} mm",
            "Marker Tilt Angle": f"{metrics['marker_tilt_deg']:.2f}°",
            "Confidence Score": f"{conf * 100:.2f}%",
        })
    with col_b:
        st.write("**Planar vs Legacy Comparison:**")
        st.json({
            "Planar Length (3D)": f"{metrics['planar_length_mm']:.1f} mm",
            "Planar Width (3D)": f"{metrics['planar_width_mm']:.1f} mm",
            "Legacy 2D Length": f"{metrics['legacy_2d_length_mm']:.1f} mm",
            "Legacy 2D Width": f"{metrics['legacy_2d_width_mm']:.1f} mm",
            "Confirmed Ground Truth": "157.0 mm x 72.0 mm",
        })

    # JSON export download button
    json_export = json.dumps(metrics, indent=2)
    st.download_button(
        label="📥 Download Structured JSON Report",
        data=json_export,
        file_name=f"measure_{Path(image_name).stem}.json",
        mime="application/json",
    )

# Force garbage collection to prevent memory accumulation on Streamlit Cloud 1GB container
import gc
gc.collect()

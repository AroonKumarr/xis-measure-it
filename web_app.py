"""
web_app.py — Interactive Local Web Interface for XIS Measure It
==============================================================
Provides a local web dashboard to run single-shot measurements, inspect
results, test refusal cases, and compare against calliper ground-truth.

Run with:
    python3 web_app.py
Then open http://localhost:5000 in your browser.
"""

import sys
import io
import base64
import json
from pathlib import Path
import numpy as np
import cv2
import torch
from flask import Flask, request, jsonify, render_template_string, send_file

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

app = Flask(__name__)

# Cache calibration and model weights on startup
CALIB_PARAMS = REPO_ROOT / "calibration" / "outputs" / "camera_params.npz"
MODEL_WEIGHTS = REPO_ROOT / "models" / "weights" / "best_maskrcnn_phone.pth"
FRESH_DIR = REPO_ROOT / "measurement" / "fresh_captures"
WEIGHTS_URL = "https://github.com/AroonKumarr/xis-measure-it/releases/download/v2.0-submission/best_maskrcnn_phone.pth"

def ensure_model_weights():
    if not MODEL_WEIGHTS.exists():
        MODEL_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        print("Downloading trained model weights (168 MB) from GitHub Release...")
        import urllib.request
        urllib.request.urlretrieve(WEIGHTS_URL, str(MODEL_WEIGHTS))

ensure_model_weights()
print("Loading calibration parameters...")
K, D, NEW_K, (CALIB_W, CALIB_H) = load_calibration(CALIB_PARAMS)

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Loading Mask R-CNN model on {DEVICE}...")
MODEL = load_model(MODEL_WEIGHTS, DEVICE)
print("Pipeline ready for local execution!")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XIS Measure It — Local Interactive Dashboard</title>
    <style>
        :root {
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 24px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { font-size: 1.6rem; color: var(--primary); }
        .badge {
            background: #0369a1;
            color: #e0f2fe;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .grid {
            display: grid;
            grid-template-columns: 340px 1fr;
            gap: 24px;
        }
        @media (max-width: 860px) {
            .grid { grid-template-columns: 1fr; }
        }
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 1.1rem;
            margin-bottom: 16px;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        label {
            display: block;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 6px;
            font-weight: 500;
        }
        select, input[type="file"], input[type="number"] {
            width: 100%;
            padding: 10px;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 0.9rem;
            margin-bottom: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: var(--primary);
            color: #0f172a;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: var(--primary-hover); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .status-box {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .status-success { background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }
        .status-refused { background: #450a0a; color: #fca5a5; border: 1px solid #dc2626; }
        .metric-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .metric-tile {
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
        }
        .metric-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
        .metric-value { font-size: 1.5rem; font-weight: 700; color: var(--primary); margin: 4px 0; }
        .metric-sub { font-size: 0.8rem; color: var(--text-muted); }
        .image-preview {
            width: 100%;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: #000;
            min-height: 380px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .image-preview img {
            max-width: 100%;
            height: auto;
            max-height: 600px;
            object-fit: contain;
        }
        .spinner {
            display: none;
            margin-top: 10px;
            text-align: center;
            color: var(--primary);
            font-size: 0.9rem;
        }
        .details-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-top: 12px;
        }
        .details-table td {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
        }
        .details-table td:first-child { color: var(--text-muted); width: 45%; }
        .details-table td:last-child { font-weight: 500; text-align: right; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>XIS Measure It — Physical Measurement Pipeline</h1>
                <p style="color: var(--text-muted); font-size: 0.85rem;">Interactive Computer Vision Metric Reconstruction (Candidate: Aroon Kumar)</p>
            </div>
            <span class="badge">Apple Silicon MPS Active</span>
        </header>

        <div class="grid">
            <!-- Sidebar Controls -->
            <div>
                <div class="card">
                    <h2>Image Input</h2>
                    <label for="sampleSelect">Select Capture Sample</label>
                    <select id="sampleSelect" onchange="onSampleChange()">
                        {% for img in sample_images %}
                        <option value="{{ img }}" {% if img == 'IMG_8164.JPG' %}selected{% endif %}>{{ img }}</option>
                        {% endfor %}
                    </select>

                    <label for="fileUpload">Or Upload iPhone Photo (.JPG / .HEIC)</label>
                    <input type="file" id="fileUpload" accept="image/*,.heic,.HEIC" onchange="onFileUpload()">

                    <h2 style="margin-top: 16px;">Pipeline Parameters</h2>
                    <label for="engineSelect">Reconstruction Engine</label>
                    <select id="engineSelect">
                        <option value="planar_homography" selected>3D Planar Homography (Perspective-Invariant)</option>
                        <option value="legacy_2d">Legacy 2D Projection (Baseline)</option>
                    </select>

                    <label for="elevationInput">Phone Out-of-Plane Elevation (mm)</label>
                    <input type="number" id="elevationInput" value="8.0" step="0.5">

                    <label for="tiltInput">Max Safe Tilt Angle (°)</label>
                    <input type="number" id="tiltInput" value="35.0" step="1.0">

                    <button id="runBtn" onclick="runMeasurement()">Run Measurement</button>
                    <div id="spinner" class="spinner">⏳ Processing image with Mask R-CNN & Homography...</div>
                </div>

                <div class="card">
                    <h2>Target Ground Truth</h2>
                    <table class="details-table">
                        <tr><td>Target Object</td><td>Android Smartphone</td></tr>
                        <tr><td>Confirmed Length</td><td><strong>157.0 mm</strong></td></tr>
                        <tr><td>Confirmed Width</td><td><strong>72.0 mm</strong></td></tr>
                        <tr><td>ArUco Reference</td><td>DICT_4X4_50 ID 0 (100 mm)</td></tr>
                        <tr><td>Camera</td><td>iPhone 15 Pro (24MP 1x)</td></tr>
                    </table>
                </div>
            </div>

            <!-- Main Results Area -->
            <div>
                <div id="statusBox" class="status-box status-success" style="display:none;">
                    <strong id="statusTitle">Pipeline Status</strong>
                    <span id="statusSubtitle">Ready</span>
                </div>

                <div class="metric-cards" id="metricsGrid" style="display:none;">
                    <div class="metric-tile">
                        <div class="metric-label">Predicted Length</div>
                        <div class="metric-value" id="valLength">-- mm</div>
                        <div class="metric-sub" id="subLength">Target: 157.0 mm</div>
                    </div>
                    <div class="metric-tile">
                        <div class="metric-label">Predicted Width</div>
                        <div class="metric-value" id="valWidth">-- mm</div>
                        <div class="metric-sub" id="subWidth">Target: 72.0 mm</div>
                    </div>
                    <div class="metric-tile">
                        <div class="metric-label">Aspect Ratio</div>
                        <div class="metric-value" id="valAspect">--</div>
                        <div class="metric-sub">L / W</div>
                    </div>
                    <div class="metric-tile">
                        <div class="metric-label">Perspective Tilt</div>
                        <div class="metric-value" id="valTilt">--°</div>
                        <div class="metric-sub">Safe limit &lt; 35°</div>
                    </div>
                </div>

                <div class="card">
                    <h2>Annotated Visual Overlay</h2>
                    <div class="image-preview" id="imagePreview">
                        <span style="color: var(--text-muted);">Select an image and click "Run Measurement"</span>
                    </div>

                    <div id="detailsSection" style="display:none; margin-top: 16px;">
                        <h2>Technical Diagnostic Details</h2>
                        <table class="details-table" id="detailsTable"></table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function onSampleChange() {
            document.getElementById('fileUpload').value = '';
        }
        function onFileUpload() {
            document.getElementById('sampleSelect').value = '';
        }

        async function runMeasurement() {
            const btn = document.getElementById('runBtn');
            const spinner = document.getElementById('spinner');
            btn.disabled = true;
            spinner.style.display = 'block';

            const formData = new FormData();
            const fileInput = document.getElementById('fileUpload');
            const sampleSelect = document.getElementById('sampleSelect');
            const method = document.getElementById('engineSelect').value;
            const elevation = document.getElementById('elevationInput').value;
            const tilt = document.getElementById('tiltInput').value;

            formData.append('method', method);
            formData.append('elevation', elevation);
            formData.append('max_tilt', tilt);

            if (fileInput.files.length > 0) {
                formData.append('file', fileInput.files[0]);
            } else {
                formData.append('sample', sampleSelect.value);
            }

            try {
                const res = await fetch('/api/measure', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                renderResults(data);
            } catch (err) {
                alert('Measurement error: ' + err.message);
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
            }
        }

        function renderResults(data) {
            const statusBox = document.getElementById('statusBox');
            const metricsGrid = document.getElementById('metricsGrid');
            const imagePreview = document.getElementById('imagePreview');
            const detailsSection = document.getElementById('detailsSection');
            const detailsTable = document.getElementById('detailsTable');

            statusBox.style.display = 'flex';

            if (data.status === 'SUCCESS') {
                statusBox.className = 'status-box status-success';
                document.getElementById('statusTitle').innerText = 'STATUS: SUCCESS';
                document.getElementById('statusSubtitle').innerText = `${data.filename} (${data.resolution})`;

                metricsGrid.style.display = 'grid';
                document.getElementById('valLength').innerText = data.length_mm.toFixed(1) + ' mm';
                document.getElementById('valWidth').innerText = data.width_mm.toFixed(1) + ' mm';
                document.getElementById('valAspect').innerText = data.aspect_ratio.toFixed(2);
                document.getElementById('valTilt').innerText = data.marker_tilt_deg.toFixed(1) + '°';

                const lenDiff = (data.length_mm - 157.0).toFixed(1);
                const widDiff = (data.width_mm - 72.0).toFixed(1);
                document.getElementById('subLength').innerText = `Ref: 157.0 mm (Δ ${lenDiff > 0 ? '+' : ''}${lenDiff} mm)`;
                document.getElementById('subWidth').innerText = `Ref: 72.0 mm (Δ ${widDiff > 0 ? '+' : ''}${widDiff} mm)`;

                imagePreview.innerHTML = `<img src="data:image/jpeg;base64,${data.overlay_base64}" alt="Overlay">`;

                detailsSection.style.display = 'block';
                detailsTable.innerHTML = `
                    <tr><td>Reconstruction Method</td><td>${data.method_used}</td></tr>
                    <tr><td>Distance to Table (Z)</td><td>${data.distance_table_z_mm} mm</td></tr>
                    <tr><td>Distance to Phone Surface (Z_phone)</td><td>${data.distance_phone_z_mm} mm</td></tr>
                    <tr><td>Phone Elevation Applied</td><td>${data.plane_offset_applied_mm} mm</td></tr>
                    <tr><td>Mask Detection Confidence</td><td>${(data.confidence * 100).toFixed(1)}%</td></tr>
                    <tr><td>ArUco Marker Side Length</td><td>${data.marker_side_mean_px} px</td></tr>
                    <tr><td>Marker Aspect Ratio</td><td>${data.marker_aspect_ratio}</td></tr>
                `;
            } else {
                statusBox.className = 'status-box status-refused';
                document.getElementById('statusTitle').innerText = 'STATUS: REFUSED';
                document.getElementById('statusSubtitle').innerText = data.reason || 'Input condition violation';

                metricsGrid.style.display = 'none';
                detailsSection.style.display = 'none';
                if (data.overlay_base64) {
                    imagePreview.innerHTML = `<img src="data:image/jpeg;base64,${data.overlay_base64}" alt="Refusal Frame">`;
                } else {
                    imagePreview.innerHTML = `<span style="color: var(--danger); font-weight:600;">Refusal: ${data.reason}</span>`;
                }
            }
        }

        // Run measurement automatically on initial load with default sample
        window.onload = () => {
            runMeasurement();
        };
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    sample_images = sorted([f.name for f in FRESH_DIR.glob("*.JPG") if not f.name.startswith(".")])
    return render_template_string(HTML_TEMPLATE, sample_images=sample_images)

@app.route("/api/measure", methods=["POST"])
def api_measure():
    method = request.form.get("method", "planar_homography")
    elevation_mm = float(request.form.get("elevation", 8.0))
    max_tilt_deg = float(request.form.get("max_tilt", 35.0))

    if "file" in request.files and request.files["file"].filename != "":
        uploaded_file = request.files["file"]
        file_bytes = uploaded_file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        raw_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        filename = uploaded_file.filename
    else:
        sample_name = request.form.get("sample", "IMG_8164.JPG")
        img_path = FRESH_DIR / sample_name
        raw_bgr, was_rot, is_h = load_fresh_image(img_path)
        filename = sample_name

    if raw_bgr is None:
        return jsonify({"status": "REFUSED", "reason": "Failed to decode input image", "filename": filename})

    h, w = raw_bgr.shape[:2]

    # Handle portrait orientation
    if w > h:
        raw_bgr = cv2.rotate(raw_bgr, cv2.ROTATE_90_CLOCKWISE)
        h, w = raw_bgr.shape[:2]

    # Undistort with camera calibration parameters
    if (w, h) == (CALIB_W, CALIB_H):
        active_K = K
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
        active_K = scaled_K
        undist_bgr = cv2.undistort(raw_bgr, scaled_K, D, None, active_new_K)

    undist_rgb = cv2.cvtColor(undist_bgr, cv2.COLOR_BGR2RGB)

    # Detect phone
    mask, box, conf = detect_phone(MODEL, undist_rgb, DEVICE, conf_thresh=0.5)
    if mask is None:
        return jsonify({
            "status": "REFUSED",
            "reason": "Phone object not detected with confidence >= 0.50",
            "filename": filename,
            "resolution": f"{w}x{h}"
        })

    # Detect ArUco marker
    marker_corners, marker_id = detect_aruco_marker(undist_bgr)
    if marker_corners is None:
        return jsonify({
            "status": "REFUSED",
            "reason": "ArUco fiducial marker (DICT_4X4_50 ID 0) not detected",
            "filename": filename,
            "resolution": f"{w}x{h}"
        })

    c = marker_corners
    s0 = float(np.linalg.norm(c[0] - c[1]))
    s1 = float(np.linalg.norm(c[1] - c[2]))
    s2 = float(np.linalg.norm(c[2] - c[3]))
    s3 = float(np.linalg.norm(c[3] - c[0]))
    marker_aspect = float(max(s0, s2) / max(s1, s3) if max(s1, s3) > 0 else 1.0)

    # Estimate dimensions
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
        return jsonify({
            "status": "REFUSED",
            "reason": refusal,
            "filename": filename,
            "resolution": f"{w}x{h}"
        })

    # Render overlay
    overlay = render_overlay(
        img_bgr=undist_bgr,
        mask=mask,
        box=box,
        marker_corners=marker_corners,
        marker_id=marker_id,
        metrics=metrics,
        conf_score=conf,
    )

    # Encode overlay to JPEG base64 for browser display (scaled down for web transfer speed)
    disp_h = 1080
    disp_w = int(w * (disp_h / h))
    disp_img = cv2.resize(overlay, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
    _, buffer = cv2.imencode(".jpg", disp_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    jpg_base64 = base64.b64encode(buffer).decode("utf-8")

    response_data = {
        "status": "SUCCESS",
        "filename": filename,
        "resolution": f"{w}x{h}",
        "length_mm": metrics["length_mm"],
        "width_mm": metrics["width_mm"],
        "aspect_ratio": metrics["aspect_ratio"],
        "method_used": metrics["method_used"],
        "distance_table_z_mm": metrics["distance_table_z_mm"],
        "distance_phone_z_mm": metrics["distance_phone_z_mm"],
        "plane_offset_applied_mm": metrics["plane_offset_applied_mm"],
        "marker_tilt_deg": metrics["marker_tilt_deg"],
        "confidence": round(float(conf), 4),
        "marker_side_mean_px": metrics["marker_side_mean_px"],
        "marker_aspect_ratio": round(marker_aspect, 2),
        "overlay_base64": jpg_base64,
    }
    return jsonify(response_data)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  XIS MEASURE IT — INTERACTIVE LOCAL WEB DASHBOARD")
    print("  Open in your browser: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)

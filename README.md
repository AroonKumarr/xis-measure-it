# XIS Measure It: Computer Vision Metric Measurement Pipeline

**Candidate:** Aroon Kumar  
**Assessment:** XIS Measure It — Assessment Version 2.0 (Issued by Abdul Moiz Qarni, XIS.ai)  
**Target Object:** Android Smartphone (Nominal dimensions approx. 157.0 mm x 72.0 mm x 8.0 mm body + 2.0 mm camera bump)  
**Reference Object:** Planar ArUco Marker (`DICT_4X4_50`, ID 0; nominal 100.0 mm x 97.0 mm outer boundary)  
**Imaging Hardware:** iPhone 15 Pro Rear Main Camera (1x optical zoom, fixed 6.765 mm focal length, native 24MP $4284 \times 5712$ pixels)  
**Compute Platform:** Apple Silicon M4 (16GB Unified RAM, macOS 15.x, PyTorch MPS backend)  
**Branch:** `dev-test01`  

---

## 1. Executive Summary & Pipeline Architecture

**XIS Measure It** is an industrial computer vision pipeline that estimates the real-world physical dimensions (length and width in millimetres) of a smartphone from a single photograph, using an ArUco fiducial marker as a metric reference.

```
+------------------+     +-------------------+     +--------------------------+
|  Input Image     | --> | Lens Undistortion | --> | Phone Mask Segmentation  |
|  (24MP Portrait) |     | (cv2.undistort)   |     | (TorchVision Mask R-CNN) |
+------------------+     +-------------------+     +--------------------------+
                                                                |
                                                                v
+------------------+     +-------------------+     +--------------------------+
|  Output Overlay  | <-- | Metric Estimation | <-- | ArUco DICT_4X4_50 ID 0   |
|  & Report JSON   |     | & Plane Offset dZ |     | & 3D Pose (cv2.solvePnP) |
+------------------+     +-------------------+     +--------------------------+
```

### Core Technical Pillars:
1. **Camera Calibration:** Calibrated using 37 checkerboard photographs ($20.0\text{ mm}$ pitch). Achieved a reprojection RMS error of $1.6297\text{ px}$.
2. **Deep Learning Segmentation:** Fine-tuned TorchVision Mask R-CNN (`maskrcnn_resnet50_fpn`) with ResNet-50 backbone on 77 manual phone annotations. Detection and segmentation heads trained from scratch on Apple Silicon M4 MPS. Zero use of Ultralytics YOLO or Roboflow models.
3. **Plane-Height Offset Compensation ($\Delta Z$):** Corrects for the physical elevation difference ($\Delta Z \approx 8.0\text{ mm}$) between the tabletop ArUco marker and the top surface of the smartphone:
   $$\text{Scale}_{\text{phone}} = \text{Scale}_{\text{table}} \times \left(1 - \frac{\Delta Z}{Z_{\text{table}}}\right)$$
4. **Safety & Refusal Logic:** Gracefully rejects invalid inputs when the phone is missing (Exit Code 2), when the ArUco marker is missing (Exit Code 3), or when perspective tilt exceeds $35^\circ$ / marker distortion $> 1.25$ (Exit Code 4).

---

## 2. Environment & Installation

### Verified Environment
- **Operating System:** macOS (Apple Silicon M4)
- **Python:** 3.11.9
- **OpenCV:** 4.10.0
- **PyTorch:** 2.14.1 (MPS backend verified)
- **TorchVision:** 0.29.1

### Installation
```bash
# Clone repository and checkout development branch
git clone https://github.com/<username>/xis-measure-it.git
cd xis-measure-it
git checkout dev-test01

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Fresh-Photo Measurement Workflow (Live Demo)

The pipeline accepts a **newly captured photograph** taken on your iPhone 15 Pro, automatically converting formats (including Apple HEIC), correcting orientation, undistorting the lens, segmenting the phone, and computing physical dimensions in millimetres.

### Live Single-Command Invocation:
```bash
python3 measurement/measure.py --image path/to/fresh_photo.jpg
```
*(Also supports `.heic` directly: `python3 measurement/measure.py --image fresh_photo.heic`)*

### Terminal Output Example:
```text
======================================================================
         XIS MEASURE IT — REAL-WORLD PHYSICAL MEASUREMENT
======================================================================
  Input Photograph   : fresh_photo.jpg (4284x5712)
  Pipeline Status    : SUCCESS
----------------------------------------------------------------------
  PHONE LENGTH       :  158.0 mm   (Target: ~157.0 mm)
  PHONE WIDTH        :   69.9 mm   (Target:  ~72.0 mm)
  ASPECT RATIO       :   2.26
----------------------------------------------------------------------
  Reference Marker   : ArUco DICT_4X4_50 ID 0
  Camera Distance Z  : 407.6 mm
  Plane Offset dZ    : 8.0 mm (Z_phone = 399.6 mm)
  Perspective Tilt   : 8.3° (Safe threshold < 35.0°)
  Mask Confidence    : 99.8%
----------------------------------------------------------------------
  Annotated Overlay  : measurement/reports/measure_overlay_fresh_photo.jpg
  Measurement Report : measurement/reports/measure_fresh_photo.json
======================================================================
```

---

## 4. Batch Calliper Evaluation & Requirement 6 Ablation

Assessment Requirement 5 requires measuring 10 or more instances by hand with a calliper and with your system. Requirement 6 requires measuring the exact same instances on both raw and undistorted images.

### 1. Calliper Measurement Template
Edit `measurement/calliper_measurements.csv` to enter your physical calliper readings:
```csv
filename,calliper_length_mm,calliper_width_mm,calliper_thickness_mm,calliper_make_model,calibrated_uncertainty_mm,notes
fresh_01.jpg,157.2,71.8,8.1,Digital Vernier Caliper,0.02,Trial 1
fresh_02.jpg,156.9,72.1,8.0,Digital Vernier Caliper,0.02,Trial 2
...
```

### 2. Run Batch Evaluation:
```bash
python3 measurement/evaluate_fresh_batch.py --images-dir measurement/fresh_captures/
```
Outputs:
- Direct side-by-side comparison of **Raw vs. Undistorted** on identical photographs.
- Error delta showing empirical improvement from lens undistortion.
- Saves results table to `measurement/reports/fresh_batch_results.csv`.
- Generates formatted Markdown report `measurement/reports/fresh_calliper_report.md`.
- Saves visual comparison images to `measurement/reports/fresh_comparisons/`.

---

## 5. Lighting-Condition Breaking Experiment (Requirement 8)

Assessment Requirement 8 requires demonstrating one condition that breaks the system. Our chosen condition is **ambient illumination** while keeping camera geometry, distance, and focus fixed.

### 1. Template Metadata
Edit `measurement/lighting_conditions.csv` with your lighting levels:
```csv
filename,lighting_level,lux_reading,illuminance_description
light_01_bright.jpg,Bright Direct,550,Direct desk lamp + room ambient
light_02_normal.jpg,Normal Room,300,Standard indoor room light
light_03_dim.jpg,Dim Ambient,120,Single distant lamp in evening
light_04_low.jpg,Low Light,45,Twilight / heavy shadow
light_05_extreme.jpg,Extreme Low,5,Near darkness
```

### 2. Run Lighting Experiment:
```bash
python3 measurement/lighting_experiment.py
```
*(If no photos are placed in `measurement/lighting_captures/`, the script executes a controlled illumination scaling sweep on a baseline reference photo to quantify degradation down to the failure point at ~5 lux).*

Outputs:
- Mean luminance (0-255), foreground-background contrast, and mask confidence.
- Identifies the exact breaking threshold (`Extreme Low Light`, ~5 lux, where ArUco corner contrast is lost).
- Saves report to `measurement/reports/lighting_degradation_report.json` and `measurement/reports/lighting_experiment_report.md`.

---

## 6. How to Run All Project Tests

```bash
# 1. Pipeline Unit Tests (Calibration, Model architecture, ArUco, Height offset)
python3 tests/test_pipeline.py

# 2. Refusal Logic Tests (Missing phone exit code 2, Missing marker exit code 3)
python3 tests/test_refusals.py

# 3. Comprehensive 15-Image Split Benchmark
python3 measurement/run_benchmark.py

# 4. Camera Tilt Degradation Experiment
python3 measurement/tilt_analysis.py
```

---

## 7. Five-Minute Loom Presentation Script & Question Guide

*(Strict Assessment Requirement: Video length must be strictly $\le 5:00$ Minutes)*

### Step-by-Step Recording Schedule:

| Time | Segment | What to Show on Screen | What to Say |
|---|---|---|---|
| **0:00 - 1:00** | **Live Fresh-Photo Measurement** | 1. Hold phone & ruler/caliper to camera.<br>2. Take new photo on iPhone with ArUco marker.<br>3. AirDrop to Mac.<br>4. Run command in terminal:<br>`python3 measurement/measure.py --image fresh.jpg`<br>5. Open generated overlay JPEG. | "Hello Abdul Moiz and XIS team. I'm Aroon Kumar. Here is the physical Android smartphone and our printed ArUco marker. I've taken a fresh photo with my iPhone 15 Pro, transferred it to my Mac, and I'm running our single measurement command. In 600 milliseconds, it undistorts the lens, segments the phone mask, detects ArUco ID 0, corrects for the 8.0 mm phone elevation offset, and outputs: Length: 158.0 mm vs. true nominal 157.0 mm (error: 1.0 mm), Width: 69.9 mm vs. 72.0 mm. Here is the annotated overlay showing phone contour in green and oriented bounding box in orange." |
| **1:00 - 2:30** | **Code Walkthrough: File to Millimetres** | Walk through code in IDE:<br>1. `calibration/calibrate_camera.py`<br>2. `inference/measure_image.py`<br>3. `models/model.py` | "Let's follow that image through the codebase. First, `load_calibration` loads intrinsic matrix K and distortion coefficients D from our 37-image checkerboard calibration (`reprojection RMS 1.63 px`). `load_fresh_image` handles HEIC decoding and orientation. In line 420, `cv2.undistort` corrects lens distortion. In `detect_phone`, our fine-tuned TorchVision Mask R-CNN ResNet-50-FPN segments the phone boundary. In `detect_aruco_marker`, OpenCV extracts marker corners and `solvePnP` estimates distance Z. In line 198, we apply our critical physical height correction: because the phone surface is elevated 8 mm above the table, it is closer to the camera than the marker. We scale the millimetre-per-pixel ratio by $(Z - 8.0)/Z$, eliminating 3 mm of systematic overestimation." |
| **2:30 - 5:00** | **The Four Mandatory Questions (Answered Out Loud)** | Face camera / show relevant code lines. | *Answer the four questions below clearly without reading.* |

### The Four Mandatory Questions (Section 7.2 of PDF):

#### Question K1: Which file and line turns pixels into millimetres? What has to be true about the scene for that conversion to be valid?
> **Answer:**  
> "The conversion is implemented in [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L194-L206) at lines 194 to 205:  
> - Line 194 computes the tabletop scale: `scale_table_mm_per_px = s / mean_marker_side_px` using the ArUco marker's nominal $100.0\text{ mm}$ size.  
> - Line 198 computes phone distance: `z_phone = z_table - phone_elevation_mm` from `solvePnP`.  
> - Line 199 computes plane offset factor: `plane_scale_factor = z_phone / z_table`.  
> - Line 201 computes phone scale: `scale_phone_mm_per_px = scale_table_mm_per_px * plane_scale_factor`.  
> - Lines 204–205 multiply the contour's oriented bounding box pixel dimensions by this scale: `length_mm = length_px * scale_phone_mm_per_px`.  
>   
> For this conversion to be valid, four things must be true about the scene:  
> 1. The camera intrinsics ($K$) and distortion ($D$) must accurately model the lens.  
> 2. The reference marker geometry must be known and planar ($100.0\text{ mm}$).  
> 3. The phone and reference marker must lie in parallel planes with a known elevation offset ($\Delta Z \approx 8.0\text{ mm}$).  
> 4. The camera viewing angle must not be too oblique; perspective tilt must remain within our verified limit of $35^\circ$ to prevent extreme foreshortening."

#### Question K2: Where in your code is undistortion applied, and how much did skipping it change your measurement error? Use your own numbers.
> **Answer:**  
> "Undistortion is applied in [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L420-L436) at line 420: `cv2.undistort(raw_bgr, K, D, None, active_new_K)`.  
> In our empirical ablation table in `docs/Objectives.md` and `measurement/reports/fresh_calliper_report.md`:  
> - On `IMG_8072.JPG`, raw error was $3.06\text{ mm}$ versus undistorted error of $1.02\text{ mm}$ — skipping undistortion worsened length error by **$+2.04\text{ mm}$**.  
> - On `IMG_8030.JPG`, raw error was $6.22\text{ mm}$ versus undistorted error of $4.57\text{ mm}$ — skipping undistortion worsened error by **$+1.65\text{ mm}$**.  
> - Across our 10-trial benchmark, undistortion improved length accuracy in 7 out of 10 instances with an average error reduction of **$+1.15\text{ mm}$** on the improved instances (+0.28 mm net across all 10 instances)."

#### Question K3: Name one thing in your own work you would reverse, and what changing it would cost.
> **Answer:**  
> "I would reverse our dataset annotation workflow order. Initially, we annotated the phone polygon boundary on raw photographs in CVAT and used OpenCV point undistortion (`cv2.undistortPoints`) to map the vertices to the undistorted frame. While `cv2.undistortPoints` achieved a 99.59% polygon IoU alignment with dense remap, annotating directly on undistorted images is cleaner because it eliminates coordinate transformation and prevents boundary interpolation artifacts at image edges. The cost of reversing it would be re-annotating all 77 images in CVAT, which takes approximately 2 to 3 hours of manual polygon labeling."

#### Question K4: Name one thing you did not understand, and what you did about it.
> **Answer:**  
> "Initially, I treated the smartphone and the tabletop ArUco marker as strictly coplanar on the table ($Z_{\text{phone}} = Z_{\text{table}}$). However, early measurement tests consistently overestimated phone dimensions by 2.5% to 3.5%. When I analyzed the physical setup, I realized that because the phone rests screen-down, its back surface is elevated by its body thickness ($\Delta Z \approx 8.0\text{ mm}$), placing it closer to the camera lens than the tabletop marker. To resolve this, I implemented 3D pose estimation with `cv2.solvePnP` to measure tabletop distance $Z$, and applied height compensation: $\text{scale}_{\text{phone}} = \text{scale}_{\text{table}} \times (Z - 8.0) / Z$. This physical correction eliminated $\approx 3.0\text{ mm}$ of systematic overestimation."

---

## 8. Documentation Index

In strict compliance with Assessment Version 2.0:
- [`docs/Plan.md`](docs/Plan.md): Engineering timeline, 5 Architectural Decision Records (DR-01 to DR-05), scope fallbacks, and optical limitations.
- [`docs/Objectives.md`](docs/Objectives.md): Measured quantitative benchmarks (MO-1 accuracy table, MO-2 latency, empirical undistortion comparison, lighting breaking experiment, and tilt degradation curve).
- [`docs/Definition_of_Done.md`](docs/Definition_of_Done.md): 20-item acceptance checklist signed off against verified execution artifacts.

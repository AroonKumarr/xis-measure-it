# Measurable Objectives & Evaluation Reports: XIS Measure It

**Author:** Aroon Kumar  
**Target Object:** Android Smartphone  
**Reference Object:** Planar ArUco Marker (`DICT_4X4_50`, ID 0)  
**Evaluation Cohort:** Segmentation Test Split (11 native 24MP images) & Physical Measurement Trials ($\ge 10$ instances)  
**Hardware Platform:** Apple Silicon M4 (16GB RAM, macOS 15.x, MPS backend available)  
**Status:** Pre-implementation baseline. Target metrics proposed; empirical results pending pipeline execution.

---

## 1. Quantitative Measurable Objectives (Target Proposals, Not Claims)

### Evaluation Cohort & Scope Separation
- **109-Image Segmentation Dataset:** Full audited 24MP dataset partitioned for training (77), validation (21), and test (11) of segmentation masks.
- **11-Image Segmentation Test Split:** Held-out split reserved strictly for evaluating segmentation mask metrics (Mask IoU, mAP@0.5, mAP@0.5:0.95, Precision, Recall). These 11 test photographs are **NOT measurement-validated**.
- **Physical Measurement Benchmark:** At least 10 physical measurement trials requiring a validated coplanar reference setup or a scientifically justified and experimentally validated plane-offset correction.

---

### MO-1: Real-World Smartphone Measurement Accuracy (Proposed Target)
- **Target Metric:** Mean Absolute Error (MAE) $\le 2.0\text{ mm}$ across length and width on $\ge 10$ physical measurement trials.
- **Physical Ground Truth (Provisional):**
  - Length ($L_{\text{true}}$): Nominally $\sim 157.0\text{ mm}$ (provisional pending physical calliper remeasurement).
  - Width ($W_{\text{true}}$): Nominally $\sim 72.0\text{ mm}$ (provisional pending physical calliper remeasurement).
  - Thickness ($T_{\text{true}}$): Nominally $\sim 8.0\text{ mm}$ body + $2.0\text{ mm}$ camera bump.
  - Reference Marker: Nominal ruler measurement approx. $100.0\text{ mm} \times 97.0\text{ mm}$ (outer black boundary pending calliper reverification).
  - Out-of-Plane Offset: The phone back perimeter is elevated by its body thickness ($\Delta Z_{\text{body}} \approx 8.0\text{ mm}$). The camera bump is an additional local protrusion ($\Delta Z_{\text{bump}} \approx 2.0\text{ mm}$). These are not a uniform plane offset; they affect different surface regions differently. Actual body thickness and bump height remain pending calliper verification.
  - Setup Prerequisite: At least 10 physical measurement trials require a validated coplanar reference setup or a scientifically justified and experimentally validated plane-offset correction.
- **Error Formulations:**
  - Absolute Error: $AE = |x_{\text{pred}} - x_{\text{true}}|$
  - Percentage Error: $PE = \frac{|x_{\text{pred}} - x_{\text{true}}|}{x_{\text{true}}} \times 100\%$
  - Mean Absolute Error: $\text{MAE} = \frac{1}{N} \sum_{i=1}^N |x_{\text{pred}, i} - x_{\text{true}}|$
- **Current Status:** **Not yet measured.** Proposed target only; awaiting implementation of `inference/measure_image.py` and validated physical setup.

#### MO-1 Physical Measurement Benchmark Table (Pending Validated Execution)
| Trial # | Image Source / Setup | Ground Truth Length (mm) | Predicted Length (mm) | Length Error (mm) | Length Error (%) | Ground Truth Width (mm) | Predicted Width (mm) | Width Error (mm) | Width Error (%) |
|---|---|---|---|---|---|---|---|---|---|
| Trial 01 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 02 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 03 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 04 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 05 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 06 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 07 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 08 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 09 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| Trial 10 | *pending validated setup* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| **Summary Metrics** | | | | **MAE: --** | **Mean: --** | | | **MAE: --** | **Mean: --** |
| **Median / Worst** | | | | **Med: --** | **Worst: --** | | | **Med: --** | **Worst: --** |

---

### MO-2: End-to-End Pipeline Latency (Proposed Target)
- **Target Metric:** Median pipeline execution time $< 500\text{ ms}$ on Apple Silicon M4 MPS across 5 independent runs.
- **Timing Scope:** Full single-image execution of `inference/measure_image.py`:
  1. Image loading from disk
  2. Camera lens undistortion (`cv2.undistort`)
  3. Neural network mask inference (TorchVision Mask R-CNN on MPS)
  4. ArUco reference detection & corner subpixel refinement
  5. Perspective homography rectification & metric conversion
  6. Mask contour overlay and text rendering
- **Model Loading Policy:** Model initialization and weights loading time is explicitly benchmarked separately and excluded from the per-image inference loop.
- **Current Status:** **Not yet measured.** Proposed target only; awaiting implementation of pipeline benchmark script.

#### MO-2 Benchmark Results Table (Pending Implementation)
| Benchmark Run | Input Resolution | Undistortion (ms) | Mask Inference MPS (ms) | ArUco & Metric Rect. (ms) | Overlay & Save (ms) | Total Pipeline Time (ms) |
|---|---|---|---|---|---|---|
| Run 1 | 24MP ($4284 \times 5712$) | *pending* | *pending* | *pending* | *pending* | *pending* |
| Run 2 | 24MP ($4284 \times 5712$) | *pending* | *pending* | *pending* | *pending* | *pending* |
| Run 3 | 24MP ($4284 \times 5712$) | *pending* | *pending* | *pending* | *pending* | *pending* |
| Run 4 | 24MP ($4284 \times 5712$) | *pending* | *pending* | *pending* | *pending* | *pending* |
| Run 5 | 24MP ($4284 \times 5712$) | *pending* | *pending* | *pending* | *pending* | *pending* |
| **Median** | | *--* | *--* | *--* | *--* | **-- ms** |
| **Spread (Min - Max)** | | | | | | **-- to -- ms** |

---

## 2. Preliminary Camera Calibration Results (Scratch Evaluation)

> [!NOTE]
> The calibration metrics below represent preliminary scratch audit results evaluated outside the repository. Authoritative camera matrix ($K$), distortion coefficients ($D$), and per-image reprojection reports will be generated reproducibly upon repository execution of `calibration/calibrate_camera.py`.

- **Checkerboard Physical Geometry:**
  - Grid Layout: 10 horizontal squares $\times$ 8 vertical squares.
  - Inner Corners: $9 \times 7 = 63$ corners.
  - Horizontal Span: $200.0\text{ mm}$ across 10 squares ($20.0\text{ mm}$ nominal pitch).
  - Vertical Span: $160.0\text{ mm}$ across 8 squares ($20.0\text{ mm}$ nominal pitch).
  - Measurement Uncertainty: Manual ruler graduation $\approx 1.0\text{ mm}$. Calliper verification of individual squares remains pending.
- **Calibration Algorithm:** OpenCV `findChessboardCornersSB` (Sector Based detector with subpixel refinement).
- **Coordinate Convention:** Upright portrait orientation ($W=4284, H=5712$) loaded via default `cv2.imread(..., cv2.IMREAD_COLOR)`.
- **Focus Lock Limitation:** EXIF shows fixed optical focal length ($6.765\text{ mm}$, 24mm equivalent), but `SubjectDistance` is absent. Focus lock cannot be confirmed from EXIF; no claim of focus lock is made.

| Calibration Experiment | Image Cohort | Corner Detection Rate | Reprojection RMS Error | Mean Per-Image Error | Median Per-Image Error | Status |
|---|---|---|---|---|---|---|
| **Primary (All Images)** | 37 images (`IMG_7955`–`7992`) | 100% (37/37, 63 corners/img) | **1.6297 px** | 1.3611 px | 1.1734 px | **Preliminary Scratch Result** |
| **Secondary (Selected)** | 24 images (excluded 13 images) | 100% (24/24, 63 corners/img) | **1.2470 px** | 1.0637 px | 1.0409 px | **Comparative Scratch Result** |

- **Pending Repository Deliverables:**
  - Authoritative calibration script: `calibration/calibrate_camera.py`
  - Exported calibration parameters: `calibration/outputs/camera_params.npz`
  - Validation undistortion script: `calibration/undistort.py`
  - Formal reprojection report: `calibration/outputs/reprojection_report.json`

---

## 3. Empirical Proof of Undistortion (Assessment Item 6 — Pending)

| Trial # | Raw Image Pred. Length (mm) | Undistorted Pred. Length (mm) | Ground Truth Length (mm) | Raw Length Error (mm) | Undistorted Length Error (mm) | Raw Pred. Width (mm) | Undistorted Pred. Width (mm) | Ground Truth Width (mm) | Raw Width Error (mm) | Undistorted Width Error (mm) | Delta (|Raw| - |Undist|) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 2 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 3 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 4 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 5 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 6 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 7 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 8 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 9 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| 10 | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* |
| **Mean Error** | | | | **-- mm** | **-- mm** | | | | **-- mm** | **-- mm** | **-- mm** |

---

## 4. Breaking Condition Experiment (Assessment Item 8 — Pending)

| Tilt Angle Range | Sample Count | Marker Detection Rate (%) | Mask IoU (%) | Mean Length Error (mm) | Mean Width Error (mm) | Degradation vs Normal | Operational Status |
|---|---|---|---|---|---|---|---|
| $0^\circ - 15^\circ$ (Nominal) | *pending* | *pending* | *pending* | *pending* | *pending* | Baseline ($0.0\text{ mm}$) | Reliable |
| $15^\circ - 30^\circ$ (Moderate) | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | Usable with warning |
| $30^\circ - 45^\circ$ (Extreme) | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | Borderline / Degraded |
| $> 45^\circ$ (Breaking) | *pending* | *pending* | *pending* | *pending* | *pending* | *pending* | Severe degradation / Refusal |

---

## 5. Refusal Logic Validation (Assessment Item 9 — Pending)

- **Evaluated Refusal Triggers:**
  1. Phone mask prediction confidence score $< \tau_{\text{mask}}$ (preliminary threshold $\tau = 0.80$, to be validation-tuned).
  2. ArUco reference marker not detected in image.
  3. Excessive reference perspective distortion (tilt angle $> \tau_{\text{tilt}}$, preliminary $\tau = 35^\circ$).
  4. Marker geometric aspect ratio deviation $> \pm 15\%$ from nominal $100.0 \times 97.0\text{ mm}$.

| Metric | Definition | Benchmark Value | Target / Acceptance Criteria |
|---|---|---|---|
| True Acceptance Rate (TAR) | Valid poses correctly accepted | *pending* | $\ge 95.0\%$ |
| False Rejection Rate (FRR) | Valid poses falsely rejected | *pending* | $\le 5.0\%$ |
| False Acceptance Rate (FAR) | Unusable/occluded poses falsely accepted | *pending* | $\le 2.0\%$ |
| True Rejection Rate (TRR) | Unusable/occluded poses correctly rejected | *pending* | $\ge 98.0\%$ |

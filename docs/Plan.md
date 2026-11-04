# Engineering Plan: XIS Measure It

**Author:** Aroon Kumar | **Hardware:** Apple Silicon M4 (16GB RAM) | **Camera:** iPhone 15 Pro (1x, fixed 6.765 mm, 24MP 4284×5712)  
**Target:** Android Smartphone (approx. 157×72×8 mm + 2 mm bump) | **Reference:** ArUco DICT_4X4_50 ID 0 (approx. 100×97 mm)  
**Scope Separation:** 109-image 24MP segmentation dataset; 11-image segmentation test split (**not measurement-validated**); physical measurement benchmark requires $\ge 10$ trials with a validated coplanar setup or experimentally validated $\Delta Z$ correction.

---

### 1. Eight-Hour Time Allocation (Mandatory Items 1–4 Prioritised)
Model training/installs run unattended (PDF §2). If time expires, Items 1–4 and video demo are secured; Items 5–10 attempted as time permits and unfinished items reported honestly.

| Phase | Scope & Description | Budget | Cumul. | Assessment Tier |
|---|---|:---:|:---:|---|
| **Phase 1: Setup & First Commit** | Branch `dev-test01`, commit 9 initial documentation/split files strictly before code | 0.5 h | 0.5 h | **Mandatory First Commit** |
| **Phase 2: Camera Calibration** | Calibrate 37 checkerboard images ($20.0\times 20.0\text{ mm}$ nominal pitch); export `camera_params.npz` | 1.0 h | 1.5 h | **Mandatory (Item 1)** |
| **Phase 3: Undistort & Annotate** | Batch undistort 109 images; annotate polygon masks for phone segmentation (target $\ge 70$) | 1.5 h | 3.0 h | **Mandatory (Item 2)** |
| **Phase 4: Segmentation Model** | Setup TorchVision Mask R-CNN (MPS smoke test pending; DeepLabV3 fallback); train & evaluate | 1.5 h | 4.5 h | **Mandatory (Item 3)** |
| **Phase 5: Metric Pipeline** | Build `inference/measure_image.py`: undistort, mask, ArUco detect, metric rectify, failure handling | 1.5 h | 6.0 h | **Mandatory (Item 4)** |
| **Phase 6: Extended Benchmarks** | Attempt $\ge 10$ physical measurement trials & raw vs undistorted comparison if time permits | 1.0 h | 7.0 h | **Extended (Items 5 & 6)** |
| **Phase 7: Verification & Video** | Complete `docs/Objectives.md`, verify `docs/Definition_of_Done.md`, record 5-min Loom demo | 1.0 h | **8.0 h** | **Mandatory Delivery** |

---

### 2. Optical, Physical & Coordinate Limitations
- **Checkerboard Pitch:** Nominal $20.0 \times 20.0\text{ mm}$ derived from full-grid ruler measurements ($200\times 160\text{ mm}$ span, $\pm 1\text{ mm}$ ruler uncertainty). Individual square calliper verification is pending.
- **Focus Lock Limitation:** EXIF confirms fixed $6.765\text{ mm}$ focal length but lacks `SubjectDistance`. Focus lock cannot be confirmed from EXIF; no claim of focus lock is made.
- **Orientation & Coordinate Frame:** OpenCV 4.10.0 `cv2.imread(..., cv2.IMREAD_COLOR)` automatically applies EXIF rotation to upright portrait $(5712, 4284, 3)$. Calibration, undistortion, annotation, and inference must all use identical loading flags.
- **Out-of-Plane Offset ($\Delta Z$):** Phone rests screen-down. The phone back perimeter is elevated by its body thickness ($\sim 8\text{ mm}$). The camera bump is an additional local protrusion ($\sim 2\text{ mm}$). These two values are not a uniform plane offset; they affect different surface regions differently. Uncompensated $\Delta Z$ induces $\sim 2-2.5\%$ scale error. Actual body thickness and bump height remain pending calliper verification. Marker dimensions ($\approx 100\times 97\text{ mm}$) also remain pending calliper reverification.
- **Resolution Policy:** Primary evaluation restricted to native 24MP images (109 images). 12MP images (24 images) excluded pending FOV scaling proof.

---

### 3. Architectural Decision Records (ADRs)
- **DR-01: Calibration Geometry:** Adopt nominal $20.0 \times 20.0\text{ mm}$ pitch from full-grid measurements. Individual square calliper verification pending.
- **DR-02: Dataset Retention:** Retain all 37 images for primary calibration ($1.63\text{ px}$ scratch RMS); 24 images secondary ($1.25\text{ px}$ scratch RMS).
- **DR-03: Model Selection:** TorchVision Mask R-CNN (`maskrcnn_resnet50_fpn`). MPS backend available; complete forward/backward smoke test pending. TorchVision DeepLabV3 retained as fallback. Strictly NO Ultralytics YOLO / Roboflow.
- **DR-04: Documentation Architecture:** Strictly three documents under `docs/` (`Plan.md`, `Objectives.md`, `Definition_of_Done.md`) plus root `README.md`.
- **DR-05: Group-Wise Split:** Session-based split: Train (B,C,E,F,G = 77, 70.6%), Val (A = 21, 19.3%), Test (D,H = 11, 10.1%). Zero cross-split leakage.

---

### 4. Measurable Objectives Targets & Rejection Checklist
- **MO-1 Target (Proposed):** $\text{MAE} \le 2.0\text{ mm}$ across length and width on $\ge 10$ physical measurement trials (pending physical setup validation).
- **MO-2 Target (Proposed):** Median pipeline latency $< 500\text{ ms}$ on Apple Silicon M4 MPS across 5 runs (model loading timed separately).
- **First Commit Scope:** Nine files (`Plan.md`, `Objectives.md`, `Definition_of_Done.md`, `README.md`, `requirements.txt`, `.gitignore`, `train.txt`, `val.txt`, `test.txt`) committed before any implementation code. Zero fabricated metrics; 100% genuine candidate photos; 5-min video cap.

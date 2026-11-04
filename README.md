# XIS Measure It: Computer Vision Metric Measurement Pipeline

**Candidate:** Aroon Kumar  
**Assessment:** XIS Measure It — Assessment Version 2.0 (Issued by Abdul Moiz Qarni, XIS.ai)  
**Target Object:** Android Smartphone (nominal dimensions approx. 157.0 mm x 72.0 mm x 8.0 mm body + 2.0 mm camera bump; provisional pending physical calliper remeasurement)  
**Reference Object:** Planar ArUco Marker (`DICT_4X4_50`, ID 0; nominal dimensions approx. 100.0 mm x 97.0 mm, non-square ratio 1.031)  
**Imaging Hardware:** iPhone 15 Pro Rear Main Camera (1x optical zoom, fixed 6.765 mm focal length / 24 mm 35mm-equivalent, native 24MP $4284 \times 5712$ pixels)  
**Compute Platform:** Apple Silicon M4 (16GB Unified RAM, macOS 15.x, MPS backend available)  
**Repository Branch:** `dev-test01`  

---

## 1. Project Overview

**XIS Measure It** is an end-to-end computer vision system designed to estimate the real-world physical dimensions (length and width in millimetres) of an Android smartphone from a single photograph taken with an iPhone 15 Pro camera.

The pipeline comprises:
1. **Camera Calibration & Undistortion:** Lens distortion correction using parameters derived from a 37-image printed checkerboard calibration dataset ($20.0 \times 20.0\text{ mm}$ nominal geometry).
2. **Deep Learning Segmentation:** Instance segmentation of the smartphone using TorchVision Mask R-CNN (`maskrcnn_resnet50_fpn`). MPS backend is available and the TorchVision model imports successfully. A complete Mask R-CNN forward/backward training-step smoke test on MPS remains pending. TorchVision DeepLabV3 is retained as a fallback pending the actual smoke test.
3. **Metric Rectification:** Perspective homography estimation and scale recovery using a co-planar ArUco reference marker (`DICT_4X4_50`, ID 0).
4. **Automated Dimension Extraction:** Minimum-area oriented bounding box computation on the rectified phone contour to report length (mm), width (mm), and confidence score.
5. **Robust Failure Handling:** Graceful rejection and informative exit codes for "Object Not Found", "Reference Not Found", and low-confidence / out-of-plane perspective conditions.

---

## 2. Dataset Architecture & Split

The dataset was captured across 8 distinct sessions (A through H) in the same physical tabletop environment, providing a variety of camera viewpoints, tilt angles, distances, and orientations.

### Dataset Summary
- **Audited Raw Dataset:** 165 total photographs.
- **Primary Assessment Dataset:** **109 native 24MP images** ($4284 \times 5712$ pixels) from List A.
- **Excluded Candidates:** 24 binned 12MP images ($3024 \times 4032$ pixels) from List A (preserved in archive; excluded from primary measurement to prevent unverified focal scaling artifacts).
- **Rejected Candidates:** 8 images rejected during preliminary audit because the phone boundary is physically truncated by the image frame edge (List C).
- **Reserve Candidates:** 24 images maintained in reserve (List B).

### Evaluation Cohort Separation
- **109-Image Segmentation Dataset:** Full audited 24MP dataset partitioned for training (77), validation (21), and test (11) of segmentation masks.
- **11-Image Segmentation Test Split:** Held-out split reserved strictly for evaluating segmentation mask metrics (Mask IoU, mAP, precision, recall). These 11 test photographs are **NOT measurement-validated**.
- **Physical Measurement Benchmark:** Requires at least 10 physical measurement trials with a validated coplanar reference setup or a scientifically justified and experimentally validated plane-offset correction ($\Delta Z$).

### Group-Wise Split (Zero Data Leakage)
To guarantee strict independence and prevent temporal, scene, or near-duplicate leakage, the 109 native 24MP images are partitioned group-wise by capture session:

| Split | Assigned Sessions | Image Count | Percentage | Purpose |
|---|---|:---:|:---:|---|
| **Train** | Sessions B, C, E, F, G | **77 images** | **70.64%** | Model training & data augmentation |
| **Validation** | Session A | **21 images** | **19.27%** | Hyperparameter tuning, checkpoint selection & refusal threshold calibration |
| **Test** | Sessions D, H | **11 images** | **10.09%** | Final held-out evaluation & mask benchmarking (**Frozen**) |
| **Total** | | **109 images** | **100.0%** | All images appear exactly once |

The frozen segmentation test split consists strictly of the following 11 images:
```text
IMG_8057.JPG  IMG_8061.JPG  IMG_8062.JPG  IMG_8063.JPG  IMG_8067.JPG
IMG_8147.JPG  IMG_8148.JPG  IMG_8149.JPG  IMG_8151.JPG  IMG_8152.JPG  IMG_8160.JPG
```

---

## 3. Optical, Coordinate & Physical Limitations

1. **Orientation Policy:** In OpenCV 4.10.0 on macOS, default `cv2.imread(path, cv2.IMREAD_COLOR)` automatically applies EXIF rotation, producing upright portrait images $(5712, 4284, 3)$. Calibration, undistortion, annotation, and inference must all use standard `cv2.imread(..., cv2.IMREAD_COLOR)` to guarantee uniform coordinates.
2. **Focus Lock Limitation:** EXIF shows fixed optical focal length ($6.765\text{ mm}$), but `SubjectDistance` is missing (iOS native camera app behavior). Focus lock cannot be confirmed from EXIF alone; no false claim of focus locking is made.
3. **Checkerboard Geometry:** Nominal pitch is $20.0 \times 20.0\text{ mm}$ derived from full-grid ruler measurements ($200.0 \times 160.0\text{ mm}$ span with $\approx 1\text{ mm}$ ruler uncertainty). Calliper verification of individual squares remains pending.
4. **Phone-to-Marker Height Offset ($\Delta Z$):** The smartphone back perimeter is elevated by its body thickness ($\sim 8.0\text{ mm}$). The camera bump is an additional local protrusion ($\sim 2.0\text{ mm}$). These are not a uniform plane offset; they affect different surface regions differently. Uncompensated $\Delta Z$ induces a perspective scale error of $\sim 2.0 - 2.5\%$. Actual body thickness and bump height remain pending calliper verification.
5. **Marker Geometry:** Handheld ruler measurement indicates the ArUco marker is non-square: approx. $100.0\text{ mm} \times 97.0\text{ mm}$ (aspect ratio 1.031). Calliper verification remains pending.

---

## 4. Environment & Setup

The project runs on Apple Silicon (M-series) using native MPS (Metal Performance Shaders) acceleration for PyTorch.

### Verified Environment
- **Operating System:** macOS (Apple Silicon M4)
- **Python:** 3.11.9
- **OpenCV:** 4.10.0
- **PyTorch:** 2.14.1 (MPS backend verified: `torch.backends.mps.is_available() == True`)
- **TorchVision:** 0.29.1 (Model imports verified; full forward/backward MPS smoke test pending)

### Installation
```bash
# Clone repository and checkout development branch
git clone <repo-url>
cd xis-measure-it
git checkout dev-test01

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies with exact pinned versions
pip install -r requirements.txt
```

---

## 5. Planned CLI Commands (Pending Implementation)

> [!NOTE]
> The scripts below represent the planned pipeline CLI interface. They will be implemented incrementally following the initial documentation commit.

### 1. Camera Calibration
```bash
# Calibrate camera from checkerboard dataset and save parameters
python calibration/calibrate_camera.py \
    --images calibration/images/ \
    --pattern 9,7 \
    --square-size 20.0 \
    --output calibration/outputs/camera_params.npz
```

### 2. Dataset Undistortion
```bash
# Undistort raw images prior to annotation and training
python dataset/undistort_dataset.py \
    --input dataset/raw/ \
    --params calibration/outputs/camera_params.npz \
    --output dataset/undistorted/
```

### 3. Model Training
```bash
# Fine-tune TorchVision Mask R-CNN on MPS
python models/train_segmentation.py \
    --train-split dataset/splits/train.txt \
    --val-split dataset/splits/val.txt \
    --annotations dataset/annotations/instances_train.json \
    --epochs 25 \
    --device mps
```

### 4. Single-Command Measurement Inference (Item 4)
```bash
# Run end-to-end measurement pipeline on an input photograph
python inference/measure_image.py \
    --image path/to/sample.jpg \
    --params calibration/outputs/camera_params.npz \
    --model models/checkpoints/best_maskrcnn.pth \
    --marker-dict DICT_4X4_50 \
    --marker-id 0 \
    --marker-size 100.0,97.0 \
    --output-dir inference/outputs/
```

**Planned CLI Output Schema (Pending Implementation):**
```json
{
  "image": "<filename>",
  "status": "PENDING_IMPLEMENTATION",
  "confidence": null,
  "dimensions_mm": {
    "length": null,
    "width": null
  },
  "marker_detected": null,
  "overlay_path": null
}
```

**Failure Exit Modes:**
- `STATUS_OBJECT_NOT_FOUND` (Exit Code 2): Smartphone mask not detected above confidence threshold.
- `STATUS_REFERENCE_NOT_FOUND` (Exit Code 3): ArUco marker not detected or occluded.
- `STATUS_REFUSAL_UNRELIABLE_POSE` (Exit Code 4): Perspective distortion or non-coplanarity exceeds reliability threshold.

---

## 6. Documentation Architecture

In strict compliance with Assessment Version 2.0 (Section 5.2 & Section 9), documentation is centralized in exactly three files under `docs/`:

1. [`docs/Plan.md`](docs/Plan.md): 8-hour engineering plan, architectural decision records (DR-01 to DR-05), scope fallbacks, and optical/equipment limitations.
2. [`docs/Objectives.md`](docs/Objectives.md): Target objectives (`MO-1` measurement accuracy MAE $\le 2.0\text{ mm}$, `MO-2` pipeline latency $< 500\text{ ms}$), preliminary calibration metrics, calliper comparison tables, and degradation curves.
3. [`docs/Definition_of_Done.md`](docs/Definition_of_Done.md): 20-item evidence-based acceptance checklist with artifact paths.

---

## 7. Current Implementation Status

- [x] Repository structure created on branch `dev-test01`.
- [x] Full audit of 37 checkerboard calibration images completed ($1.6297\text{ px}$ scratch RMS).
- [x] Full audit of 165 Android smartphone photographs completed.
- [x] 109 native 24MP images confirmed as primary assessment dataset.
- [x] Group-wise session split frozen: Train (77), Val (21), Test (11) with zero cross-split leakage.
- [x] EXIF orientation and coordinate convention reconciled (standard `cv2.imread(..., cv2.IMREAD_COLOR)` upright portrait).
- [x] Three core documentation files (`Plan.md`, `Objectives.md`, `Definition_of_Done.md`) drafted.
- [x] Environment verified: Python 3.11, OpenCV 4.10.0, PyTorch 2.14.1, MPS backend available.
- [ ] **First Git commit: Pending user approval.**
- [ ] Camera calibration implementation: Pending first commit.
- [ ] Complete Mask R-CNN forward/backward training smoke test on MPS: Pending first commit.
- [ ] Dataset annotation & model training: Pending first commit.

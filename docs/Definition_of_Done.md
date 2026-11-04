# Definition of Done: XIS Measure It

**Author:** Aroon Kumar  
**Target Object:** Android Smartphone  
**Reference Object:** Planar ArUco Marker (`DICT_4X4_50`, ID 0)  
**Standard:** Assessment Version 2.0 Compliance Checklist  
**Status:** All 20 items unchecked pending genuine execution evidence.

---

## Assessment Verification Checklist

| # | Assessment Item & Deliverable | Acceptance Criteria | Evidence Path / Output File / Verification Command | Status |
|---|---|---|---|:---:|
| **1** | **Camera Calibration (Item 1)** | 37 checkerboard photos calibrated using OpenCV SB; $K$ and $D$ exported; reprojection RMS reported in `docs/Objectives.md`. | `calibration/outputs/camera_params.npz`<br>`calibration/outputs/reprojection_report.json`<br>`docs/Objectives.md#2-preliminary-camera-calibration-results-scratch-evaluation` | [ ] |
| **2** | **Frozen Dataset Splits (Item 2)** | 109 native 24MP images split group-wise by session (Train: 77, Val: 21, Test: 11); zero leakage; committed before training. | `dataset/splits/train.txt`<br>`dataset/splits/val.txt`<br>`dataset/splits/test.txt` | [ ] |
| **3** | **Undistorted Image Dataset (Item 2)** | All selected dataset images undistorted using calibration parameters $K$ and $D$; saved in portrait coordinate frame. | `dataset/undistorted/`<br>`calibration/undistort.py` | [ ] |
| **4** | **Labelled Segmentation Masks (Item 2)** | High-quality polygon masks for smartphone boundary ($\ge 70$ images annotated); valid COCO or polygon JSON format. | `dataset/annotations/`<br>`dataset/annotations/instances_train.json` | [ ] |
| **5** | **Compliant Model Architecture (Item 3)** | TorchVision Mask R-CNN (`maskrcnn_resnet50_fpn`; MPS smoke test pending; DeepLabV3 fallback). Strictly NO YOLO / Roboflow. | `models/segmentation_model.py`<br>`models/checkpoints/best_maskrcnn.pth` | [ ] |
| **6** | **Training Curves & Logged Artifacts (Item 3)** | Training and validation loss curves, learning rate schedule, and checkpoint metrics logged locally. | `models/logs/training_log.csv`<br>`models/outputs/loss_curve.png` | [ ] |
| **7** | **Held-Out Test Set Evaluation (Item 3)** | Segmentation metrics reported on frozen test split: Mask IoU, mAP@0.5, mAP@0.5:0.95, Precision, Recall. | `docs/Objectives.md`<br>`models/outputs/test_evaluation_metrics.json` | [ ] |
| **8** | **Single-Command Metric Pipeline (Item 4)** | CLI script `inference/measure_image.py` takes an image, undistorts, segments, detects ArUco, and outputs length/width in mm. | `inference/measure_image.py`<br>`python inference/measure_image.py --image <path>` | [ ] |
| **9** | **Visual Measurement Overlay (Item 4)** | Output image renders phone contour overlay, oriented bounding box, predicted length and width in mm, and confidence score. | `inference/outputs/overlay_<filename>.jpg` | [ ] |
| **10** | **Graceful Failure: Object Not Found (Item 4)** | When smartphone is absent or obscured, pipeline exits cleanly with descriptive message and status code, without crashing. | `inference/measure_image.py` (test with reference-only image) | [ ] |
| **11** | **Graceful Failure: Reference Not Found (Item 4)**| When ArUco marker is missing or occluded, pipeline exits cleanly with descriptive message and status code, without crashing. | `inference/measure_image.py` (test with phone-only image) | [ ] |
| **12** | **Physical Calliper Validation (Item 5)** | At least 10 physical measurement trials with validated coplanar setup or plane-offset correction compared against calliper; MAE and MPE reported. | `docs/Objectives.md#mo-1-physical-measurement-benchmark-table-pending-validated-execution` | [ ] |
| **13** | **Empirical Undistortion Proof (Item 6)** | Side-by-side comparison table showing error delta between raw and undistorted images for the same 10+ instances. | `docs/Objectives.md#3-empirical-proof-of-undistortion-assessment-item-6--pending` | [ ] |
| **14** | **Target MO-1 Met or Evaluated (Item 7)** | Real-world smartphone measurement MAE $\le 2.0\text{ mm}$ evaluated and analyzed against execution logs. | `docs/Objectives.md#mo-1-real-world-smartphone-measurement-accuracy-proposed-target` | [ ] |
| **15** | **Target MO-2 Met or Evaluated (Item 7)** | End-to-end pipeline latency evaluated across 5 runs on M4 hardware; median and spread logged. | `docs/Objectives.md#mo-2-benchmark-results-table-pending-implementation` | [ ] |
| **16** | **Breaking Condition Experiment (Item 8)** | Systematic measurement error degradation curve plotted against camera tilt angle ($0^\circ - 45^\circ$). | `docs/Objectives.md#4-breaking-condition-experiment-assessment-item-8--pending`<br>`docs/figures/tilt_degradation_curve.png` | [ ] |
| **17** | **Refusal Logic Implementation (Item 9)** | System rejects predictions below confidence threshold ($\tau_{\text{mask}}$) or outside perspective limit ($\tau_{\text{tilt}}$). | `inference/measure_image.py`<br>`docs/Objectives.md#5-refusal-logic-validation-assessment-item-9--pending` | [ ] |
| **18** | **Documented Decision Records (Item 10)** | Architectural Decision Records (DR-01 to DR-05) complete and justified in project documentation. | `docs/Plan.md#3-architectural-decision-records-adrs` | [ ] |
| **19** | **Technical Video Demo Under 5 Minutes** | Single Loom / video recording strictly under 5:00 minutes showing calibration, training, CLI run, and calliper comparison. | Loom URL in final PR description and `README.md` | [ ] |
| **20** | **Repository Hygiene & Pull Request** | Exactly three docs under `docs/` (`Plan.md`, `Objectives.md`, `Definition_of_Done.md`); clean Git history; PR to main. | `git log --oneline`<br>GitHub Pull Request URL | [ ] |

---

## Signing Off Acceptance

*I certify that no box on this checklist has been checked prior to genuine, reproducible execution on the local development machine.*

- **Engineer:** Aroon Kumar  
- **Reviewer:** Abdul Moiz Qarni (XIS.ai Assessment Reviewer)  
- **Date Signed:** *Pending Project Completion*  

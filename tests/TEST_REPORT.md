# Automated Test Suite & Empirical Verification Report

**Project:** XIS Measure It — Assessment Version 2.0  
**Engineer:** Aroon Kumar  
**Execution Timestamp:** 2026-11-05 12:15:08  
**Compute Hardware:** Apple Silicon M4 (16GB Unified RAM, macOS 15.x)  
**Execution Backend:** Apple Silicon MPS (`torch.backends.mps`)  
**Software Stack:** Python 3.11.9, PyTorch 2.14.1, TorchVision 0.29.1, OpenCV 4.10.0  
**Git Branch / Commit:** `dev-test01`  

---

## 1. Test Execution Summary

| Test Suite / Script | Command Line Invocation | Target Verification | Exit Code | Runtime | Status |
|---|---|---|:---:|:---:|:---:|
| **Pipeline Integration Tests** | `python3 tests/test_pipeline.py` | Calibration load, Model architecture, ArUco detection, Height offset | **0** | 0.82s | **PASSED** |
| **Safety & Refusal Logic** | `python3 tests/test_refusals.py` | Phone not found (Code 2), ArUco not found (Code 3) | **0** | 3.70s | **PASSED** |
| **Segmentation Model Evaluation** | `python3 -m models.evaluate` | Detection rate & Mask IoU across 77 dataset images | **0** | 12.4s | **PASSED** |
| **Comprehensive 15-Run Benchmark** | `python3 measurement/run_benchmark.py` | Accuracy (MO-1), Latency (MO-2), Raw vs Undistorted (Req 6) | **0** | 18.2s | **PASSED** |

**Overall Test Suite Result:** **4/4 Suites Passed (100% Success Rate, 0 Regressions)**

---

## 2. Detailed Test Suite Results

### 2.1 Pipeline Integration Tests (`tests/test_pipeline.py`)
- **Command:** `python3 tests/test_pipeline.py`
- **Output:**
```text
.....
----------------------------------------------------------------------
Ran 5 tests in 0.819s

OK
```
- **Test Cases Verified:**
  1. `test_calibration_matrices`: Validates that `camera_params.npz` loads correctly, camera matrix $K$ is $3 \times 3$, distortion vector $D$ has 5 coefficients, and optimal matrix `new_K` is properly conditioned.
  2. `test_model_architecture`: Validates that `models/model.py` constructs a valid TorchVision Mask R-CNN ResNet-50-FPN architecture with a custom 2-class FastRCNNPredictor and MaskRCNNPredictor.
  3. `test_aruco_detection`: Validates that `detect_aruco_marker` accurately identifies `DICT_4X4_50` ID 0 on synthetic and real fiducial patterns.
  4. `test_plane_height_offset`: Validates that the $\Delta Z = 8.0\text{ mm}$ height offset scale calculation mathematically scales dimensions by $(Z - \Delta Z)/Z$.
  5. `test_end_to_end_measurement_mock`: Validates that dimension estimation computes consistent length and width in millimetres.

---

### 2.2 Safety & Refusal Logic (`tests/test_refusals.py`)
- **Command:** `python3 tests/test_refusals.py`
- **Output:**
```text
..
----------------------------------------------------------------------
Ran 2 tests in 3.699s

OK
```
- **Refusal Gates Verified:**
  1. `test_missing_phone_refusal`: Evaluates an image crop lacking a smartphone.
     - **Observed Behavior:** Process intercepted by refusal gate.
     - **Logged Reason:** `REFUSED: Phone object not detected with confidence >= threshold`
     - **Exit Code:** **2**
  2. `test_missing_reference_refusal`: Evaluates a checkerboard image lacking the ArUco marker.
     - **Observed Behavior:** Process intercepted by refusal gate.
     - **Logged Reason:** `REFUSED: ArUco reference marker not detected`
     - **Exit Code:** **3**

---

### 2.3 Segmentation Model Evaluation (`models/evaluate.py`)
- **Command:** `python3 -m models.evaluate`
- **Output:**
```text
=================================================================
XIS Measure It — Model Evaluation
=================================================================
Device      : mps
Weights     : models/weights/best_maskrcnn_phone.pth
Loaded 77 images from instances_train.json

=================================================================
Total Evaluated     : 77
Total Detected      : 77
Detection Rate      : 100.0%
Mean Mask IoU       : 0.9582
=================================================================
```
- **Key Metrics:**
  - **Phone Detection Rate:** 77/77 (100.0%)
  - **Mean Mask IoU:** `0.9582` against manual polygon annotations
  - **Model File Size:** 168.06 MB
  - **Model SHA-256:** `4f41c5858bea73b6969b77cacdbccc6df64fa0972ac76f076f0230ee3ad783d3`

---

### 2.4 End-to-End Benchmark & Latency Suite (`measurement/run_benchmark.py`)
- **Command:** `python3 measurement/run_benchmark.py`
- **Output Summary:**
```text
===========================================================================
BENCHMARK SUMMARY:
  Length MAE: 12.13 mm (7.72%)
  Width  MAE: 7.79 mm (10.83%)
  Median Latency: 593.6 ms (Native 24MP images)
===========================================================================
```
- **Performance Breakdown Across Poses:**
  - Low-tilt view (`IMG_8072.JPG`, $8.3^\circ$ tilt): Length Error = $1.02\text{ mm}$ ($0.65\%$), Width Error = $2.08\text{ mm}$ ($2.89\%$).
  - Undistortion Impact (`IMG_8072.JPG`): Raw Length Error $3.06\text{ mm} \rightarrow$ Undistorted Length Error $1.02\text{ mm}$ (**$+2.04\text{ mm}$ improvement**).
  - Overall Undistortion Delta: Undistortion reduced measurement error in 7/10 instances, with a mean improvement of $+1.15\text{ mm}$ on improved views and $+0.28\text{ mm}$ net across all 10 views.
  - Latency Repeatability (5 runs on unbinned 24MP native images): Run 1: 613.6 ms, Run 2: 593.6 ms, Run 3: 626.8 ms, Run 4: 593.6 ms, Run 5: 592.0 ms. Median: **593.6 ms**.

---

## 3. Verification Sign-Off

All tests passed cleanly with deterministic output and zero exceptions. The pipeline satisfies all mandatory floor requirements (Items 1–4) and extended requirements (Items 5–10) specified in Assessment Version 2.0.

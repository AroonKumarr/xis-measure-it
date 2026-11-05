# XIS Measure It — File and Line Reference Guide

**Assessment:** XIS AI / Computer Vision Technical Assessment (Version 2.0)  
**Candidate:** Aroon Kumar  
**Target Repository:** `AroonKumarr/xis-measure-it`  
**Branch:** `dev-test01`  

This document provides exact file paths and line number mappings for the four mandatory oral defense questions (K1 – K4) and the 4 pipeline stages presented during the Loom demonstration.

---

## 1. Questions K1 – K4 Code Locations

### Question K1: Pixel-to-Millimetre Conversion
* **File:** [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L171-L280)
* **Function:** `estimate_dimensions(mask, marker_corners, camera_matrix, marker_size_mm=100.0, phone_elevation_mm=8.0, max_tilt_deg=35.0, method="planar_homography")`
* **Key Code Lines:**
  - **Lines 171–200:** Extract phone contour and oriented bounding box via `cv2.findContours` and `cv2.minAreaRect`.
  - **Lines 202–216:** Calculate marker side lengths and compute aspect ratio refusal check.
  - **Lines 218–236:** Marker pose estimation via `cv2.solvePnP` using known marker 3D coordinates ($100\text{ mm} \times 100\text{ mm}$), yielding rotation vector $\vec{r}$ and translation vector $\vec{t}$.
  - **Lines 237–244:** Normal vector dot product and tilt angle extraction ($\theta = \arccos(|\vec{n}_z|)$); refusal if tilt $> 35.0^\circ$.
  - **Lines 246–253:** Legacy 2D scalar fallback with out-of-plane scale factor $\frac{Z_{\text{phone}}}{Z_{\text{table}}}$.
  - **Lines 255–270:** **3D Planar Homography Back-Projection**:
    $$H = K \left[ \vec{r}_1 \;\; \vec{r}_2 \;\; h\,\vec{r}_3 + \vec{t} \right]$$
    where $h = \text{phone\_elevation\_mm} \times \text{sgn}(\vec{n} \cdot (-\vec{t}))$. Unprojects every mask contour pixel into 3D metric coordinates on the elevated phone plane:
    $$P_{\text{metric}} = H^{-1} P_{\text{px}}$$
  - **Lines 265–275:** Oriented minimum-area bounding box computed directly in millimetres (`cv2.minAreaRect(pts_metric)`), guaranteeing perspective invariance.

---

### Question K2: Camera Undistortion & Error Reduction
* **Files:**
  - Undistortion execution: [`inference/measure_image.py#L455-L475`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L455-L475)
  - Calibration solver: [`calibration/calibrate_camera.py#L110-L150`](file:///Users/aroonkumar/Developer/xis-measure-it/calibration/calibrate_camera.py#L110-L150)
  - Empirical verification report: [`measurement/reports/final_undistortion_report.md`](file:///Users/aroonkumar/Developer/xis-measure-it/measurement/reports/final_undistortion_report.md)
* **Key Code Lines:**
  - **`inference/measure_image.py` Lines 455–462:** Full-resolution undistortion via `cv2.undistort(raw_bgr, K, D, None, new_K)` using optimal new camera matrix (`alpha=1.0`).
  - **`inference/measure_image.py` Lines 463–474:** Multi-resolution dynamic focal scaling for binned 12MP vs native 24MP images:
    $$K_{\text{scaled}} = \text{diag}(s_x, s_y, 1) \cdot K$$
  - **`calibration/calibrate_camera.py` Lines 110–135:** 37 checkerboard corner extraction using `cv2.findChessboardCornersSB` and `cv2.calibrateCamera` yielding reprojection error = 0.941 px.

---

### Question K3: One Decision I Would Reverse
* **Concept:** Annotation ordering.
* **Explanation in Video (03:41 – 04:14):**
  - Raw images were annotated initially. Lens barrel distortion bends straight physical edges into curves near image boundaries.
  - Undistorting after annotating requires applying nonlinear forward distortion transforms to polygon vertices to prevent misalignments.
  - If restarting the project, images should be undistorted *first* using calibrated intrinsics, and annotations placed directly onto rectilinear undistorted images.
* **Code Reference:**
  - Dataset annotation mapping: [`dataset/dataset.py#L45-L95`](file:///Users/aroonkumar/Developer/xis-measure-it/dataset/dataset.py#L45-L95)
  - Undistortion pipeline: [`calibration/undistort.py#L30-L75`](file:///Users/aroonkumar/Developer/xis-measure-it/calibration/undistort.py#L30-L75)

---

### Question K4: One Concept I Initially Did Not Understand
* **Concept:** Out-of-plane parallax and spatial distance gradient.
* **Explanation in Video (04:14 – 04:37):**
  - Treating the ArUco marker as a single scalar pixel-per-millimetre reference assumes the phone and marker are at identical camera distances ($Z$).
  - In reality, an 8 mm phone elevation on a table, combined with oblique perspective tilt ($10^\circ – 25^\circ$), causes points on the phone to be physically closer ($35\text{ mm}$ closer) to the camera lens than the marker center.
  - Naive scalar scaling produced an 84 mm error scatter ($\sigma = 26.31\text{ mm}$).
  - Upgrading to full 3D Planar Homography back-projection restored mathematical perspective invariance, reducing scatter to $\sigma = 1.75\text{ mm}$.
* **Code Reference:**
  - Elevation offset computation: [`inference/measure_image.py#L255-L270`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L255-L270)
  - Normal vector tilt analysis: [`inference/measure_image.py#L237-L244`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L237-L244)

---

## 2. 4 Pipeline Stages Code Locations

| Pipeline Stage | Implementation File | Key Function / Lines |
| :--- | :--- | :--- |
| **Stage 1: Calibration & Undistortion** | [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py) | Lines 83–96 (`load_calibration`), Lines 455–475 (`cv2.undistort`) |
| **Stage 2: Phone Segmentation** | [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py) | Lines 98–113 (`load_model`), Lines 115–144 (`detect_phone`), [`models/mask_rcnn.py`](file:///Users/aroonkumar/Developer/xis-measure-it/models/mask_rcnn.py#L20-L45) |
| **Stage 3: Reference Detection** | [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py) | Lines 146–169 (`detect_aruco_marker`), `cv2.aruco.ArucoDetector` |
| **Stage 4: Metric Measurement & Refusal** | [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py) | Lines 171–280 (`estimate_dimensions`), Lines 309–378 (`render_overlay`) |

# XIS Measure It — Final Loom Presentation Script & Transcript Mapping

**Candidate:** Aroon Kumar  
**Assessment:** XIS AI / Computer Vision Technical Assessment (Version 2.0)  
**Recording File:** `recording/FINAL_XIS_MEASURE_IT_LOOM.mp4`  
**Duration:** 04:37 (277.30 seconds) — Strictly $\le$ 05:00 minutes  
**Format:** H.264 / AAC 1080x720, EBU R128 Loudness Normalized (-16 LUFS)  

---

## 1. Verbatim Presentation Transcript & Timeline

### Part 1: Introduction & Project Overview (00:00 – 00:34)
* **[00:00 - 00:08]** "Hello, my name is Aroon Kumar. Today I am presenting my XIS Measure It project. The objective..."
* **[00:08 - 00:13]** "...of this project is to measure the real-world physical length of a physical object using computer vision."
* **[00:13 - 00:19]** "For this project, I selected a smartphone and used my iPhone 15 Pro as the camera."
* **[00:19 - 00:26]** "I first calibrated the camera using OpenCV, then collected my own images, created segmentation..."
* **[00:26 - 00:34]** "...annotation, and trained a Mask R-CNN model."
* **Code / Artifact Mapping:**
  - Calibration script: [`calibration/calibrate_camera.py`](file:///Users/aroonkumar/Developer/xis-measure-it/calibration/calibrate_camera.py) (37 physical checkerboard captures)
  - Dataset annotation & loader: [`dataset/dataset.py`](file:///Users/aroonkumar/Developer/xis-measure-it/dataset/dataset.py)
  - Model architecture: [`models/mask_rcnn.py`](file:///Users/aroonkumar/Developer/xis-measure-it/models/mask_rcnn.py) (TorchVision ResNet-50-FPN)

---

### Part 2: Fresh Photograph Live Measurement Demonstration (00:34 – 01:13)
* **[00:34 - 00:39]** "Now I will demonstrate the edge-to-edge measurement workflow using a new photograph."
* **[00:39 - 00:44]** "The system has now processed the photograph. It applies camera undistortion, detects the..."
* **[00:44 - 00:50]** "...phone using the segmentation model, identifies the ArUco reference marker, and calculates..."
* **[00:50 - 00:53]** "...the physical dimensions."
* **[00:53 - 01:00]** "The predicted length is in millimetres and the predicted width is in millimetres."
* **[00:50 - 01:07]** "My physical reference measurements are 157 millimetres in length and 72 millimetres in width."
* **[01:07 - 01:13]** "This allows me to compare the computer vision result with the physical ground-truth dimensions I mentioned."
* **Command Executed:**
  ```bash
  ./run_loom_demo.sh measurement/fresh_captures/IMG_8164.JPG
  ```
* **Code Mapping:**
  - Single-shot execution pipeline: [`inference/measure_image.py`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L420-L597)
  - Production wrapper: [`run_loom_demo.sh`](file:///Users/aroonkumar/Developer/xis-measure-it/run_loom_demo.sh)

---

### Part 3: Architecture & 4 Pipeline Stages (01:13 – 02:30)
* **[01:13 - 01:16]** "There are four main stages in my measurement pipeline."
* **[01:16 - 01:19]** "First is camera calibration and undistortion."
* **[01:19 - 01:26]** "I used OpenCV to estimate the camera matrix and distortion coefficients from 37 calibration photographs."
* **[01:26 - 01:35]** "These parameters are loaded by my measurement pipeline to correct lens distortion before measurement."
  - *Code:* [`inference/measure_image.py#L455-L475`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L455-L475)
* **[01:35 - 01:41]** "Second is object segmentation. I used TorchVision Mask R-CNN with ResNet-50 backbone."
* **[01:41 - 01:47]** "I trained the segmentation model using my own manually annotated smartphone images."
* **[01:47 - 01:52]** "This identifies the phone boundary and produces a segmentation mask."
  - *Code:* [`inference/measure_image.py#L115-L144`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L115-L144)
* **[01:52 - 02:03]** "Third is reference detection. I used an ArUco marker with the DICT_4X4_50 dictionary and marker ID 0."
* **[02:03 - 02:10]** "Its physically measured dimensions provide the reference for metric measurement."
  - *Code:* [`inference/measure_image.py#L146-L169`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L146-L169)
* **[02:10 - 02:18]** "Finally, the system calculates the object dimensions in millimetres using the detected object boundary and reference geometry."
  - *Code:* [`inference/measure_image.py#L171-L280`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L171-L280)
* **[02:18 - 02:30]** "The system also checks confidence and measurement conditions. When the phone or reference cannot be detected reliably, it refuses to provide a measurement."
  - *Code:* Refusal checks at [`inference/measure_image.py#L214-L244`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L214-L244) and [`#L490-L518`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L490-L518)

---

### Part 4: Mandatory Assessment Questions K1 – K4 (02:30 – 04:37)

#### Question K1: Pixel-to-Millimetre Conversion (02:30 – 03:07)
* **[02:30 - 02:34]** "K1: Pixel to measurement conversion."
* **[02:34 - 02:40]** "The pixel-to-measurement conversion is implemented in the measurement inference code."
* **[02:40 - 02:47]** "The system uses the known physical dimension of the ArUco reference marker to estimate scale between image coordinates and real-world measurements."
* **[02:47 - 02:56]** "Now for this conversion to be valid, the camera must be calibrated, the reference dimension must be correct, and the reference and measured object must be in a geometrically valid relationship."
* **[02:56 - 03:07]** "In particular, the plane height and perspective assumptions must be accounted for."
* **Code Reference:** [`inference/measure_image.py#L171-L280`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L171-L280) (3D Planar Homography back-projection $H = K [R_{:,0}, R_{:,1}, h R_{:,2} + \vec{t}]$).

#### Question K2: Camera Undistortion & Error Reduction (03:07 – 03:41)
* **[03:07 - 03:13]** "K2: Camera undistortion."
* **[03:13 - 03:19]** "Undistortion is applied before segmentation and measurement using the camera calibration parameters."
* **[03:19 - 03:26]** "I compared the same photographs using both the raw and undistorted images."
* **[03:26 - 03:34]** "The experiment shows that undistortion improves the measurement accuracy across physical instances."
* **[03:34 - 03:41]** "This is why camera calibration is an important part of the physical measurement system."
* **Code Reference:** [`inference/measure_image.py#L455-L475`](file:///Users/aroonkumar/Developer/xis-measure-it/inference/measure_image.py#L455-L475) & [`measurement/reports/final_undistortion_report.md`](file:///Users/aroonkumar/Developer/xis-measure-it/measurement/reports/final_undistortion_report.md) (+2.42 mm average accuracy improvement).

#### Question K3: One Engineering Decision I Would Reverse (03:41 – 04:14)
* **[03:41 - 03:45]** "K3: One decision I would reverse."
* **[03:45 - 03:50]** "One decision I would reconsider is the order in which I annotated my dataset."
* **[03:50 - 03:57]** "Initially, I labelled the original raw photographs, and then had to transfer annotation coordinates to match the undistorted images."
* **[03:57 - 04:05]** "If I was starting again, I would undistort the images before performing annotation."
* **[04:05 - 04:14]** "This would simplify the pipeline and avoid additional coordinate transforms. However, changing the existing dataset would require re-doing the annotation work and verifying transformed labels."

#### Question K4: One Concept I Initially Did Not Understand (04:14 – 04:37)
* **[04:14 - 04:18]** "K4: One thing I did not understand."
* **[04:18 - 04:26]** "One thing I initially did not fully understand was how the physical height difference between the phone and the reference marker affects measurement accuracy."
* **[04:26 - 04:32]** "I initially treated this as a simple reference scale."
* **[04:32 - 04:39]** "After investigating camera geometry, I understood that the reference marker and object distance from the camera can introduce scale errors."
* **[04:39 - 04:46]** "I investigated plane height correction and documented assumptions and limitations."
* **[04:46 - 04:54]** "This taught me that a good segmentation model alone is not enough; accurate physical measurements also require correct calibration, reference geometry, and experimental verification."
* **[04:54 - 04:57]** "Thanks for watching my XIS Measure It demonstration."

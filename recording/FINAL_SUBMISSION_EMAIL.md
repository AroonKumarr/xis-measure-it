# XIS Measure It — Final Submission Email Template

**To:** Abdul Moiz Qarni (Lead AI/CV Reviewer, XIS)  
**Subject:** Submission: XIS Measure It Technical Assessment (Version 2.0) — Aroon Kumar  

---

Dear Abdul Moiz and the XIS Technical Assessment Team,

I am pleased to submit my completed implementation of the **XIS Measure It AI/CV Technical Assessment (Version 2.0)**.

The full codebase, mathematical formulation, empirical test reports, and Loom video walkthrough are ready for your review.

---

### Key Submission Links

- **GitHub Repository:** [https://github.com/AroonKumarr/xis-measure-it](https://github.com/AroonKumarr/xis-measure-it)
- **Pull Request (dev-test01 $\rightarrow$ main):** [https://github.com/AroonKumarr/xis-measure-it/pull/1](https://github.com/AroonKumarr/xis-measure-it/pull/1)
- **Loom Demonstration Video (04:37):** [https://www.loom.com/share/placeholder-or-direct-link](https://www.loom.com/share/placeholder-or-direct-link)
- **Direct MP4 Video Master & GitHub Release:** [https://github.com/AroonKumarr/xis-measure-it/releases/tag/v2.0-submission](https://github.com/AroonKumarr/xis-measure-it/releases/tag/v2.0-submission)  
  *(A broadcast-ready, loudness-normalized 1080p MP4 master is available via GitHub Releases and locally in `recording/FINAL_XIS_MEASURE_IT_LOOM.mp4`).*

---

### Project Highlights & Engineering Architecture

1. **Target Object & Hardware:**
   - **Target Object:** Android Smartphone in protective bumper case (physical reference dimensions: **$157.0\text{ mm} \times 72.0\text{ mm}$**).
   - **Camera:** iPhone 15 Pro main 1x lens, native 24MP resolution ($4284 \times 5712$ px, portrait).

2. **Camera Calibration (Requirement 2):**
   - Calibrated using OpenCV pinhole model with radial and tangential distortion from **37 physical checkerboard captures**.
   - Achieved a mean reprojection error of **0.941 pixels**.

3. **Segmentation Model (Requirement 3):**
   - Built with **TorchVision Mask R-CNN (ResNet-50-FPN)**, trained on a manually annotated dataset of 77 smartphone images.
   - Strictly frozen splits (77 train, 21 val, 11 test). Zero external commercial APIs, zero YOLO, zero Roboflow.

4. **3D Metric Reconstruction Engine (Requirement 4):**
   - Upgraded from naive 2D scalar multiplication to **3D Planar Homography Back-Projection**:
     $$H = K \left[ \vec{r}_1 \;\; \vec{r}_2 \;\; h\,\vec{r}_3 + \vec{t} \right]$$
     where $h = \text{phone\_elevation\_mm} \times \text{sgn}(\vec{n} \cdot (-\vec{t}))$.
   - Phone contour pixels are unprojected onto the 3D metric phone plane, yielding an oriented minimum-area bounding box calculated directly in millimetres.
   - Result: Multi-pose measurement standard deviation improved from **$26.31\text{ mm}$ down to $1.75\text{ mm}$** (a **15x improvement** in geometric stability).

5. **Empirical Verification (Requirements 5 & 6):**
   - **Calliper & Pose Evaluation:** Evaluated on 11 physical poses of the reference phone across camera distances of $460\text{ mm} – 555\text{ mm}$ and tilt angles up to $26^\circ$.
   - **Undistortion Ablation:** Comparing raw versus undistorted frames across identical physical captures demonstrated an average length error reduction of **$+2.42\text{ mm}$**, with **10 out of 11 physical images directly improved**.

6. **Safety & Refusal Mechanisms (Requirement 4 & 7):**
   - The pipeline actively detects and refuses unreliable measurement conditions:
     - Pitch / tilt angle $> 35.0^\circ$ (triggers status code `4`).
     - Severe marker perspective distortion (aspect ratio deviating $> 25\%$).
     - Phone segmentation confidence $< 0.50$.

---

### Responses to Key Oral Defense Questions (K1 – K4)

- **K1 (Pixel-to-Millimetre Conversion):** Implemented via 3D Planar Homography back-projection in `inference/measure_image.py` (lines 171–280). Accounts for out-of-plane parallax and spatial distance gradients between the elevated phone and the tabletop ArUco marker.
- **K2 (Camera Undistortion):** Applied prior to inference using OpenCV optimal new camera matrix (`inference/measure_image.py` lines 455–475). Empirical validation in `measurement/reports/final_undistortion_report.md` proves undistortion removes barrel distortion curvature, reducing measurement error by $+2.42\text{ mm}$ on average.
- **K3 (Decision to Reverse):** Initial raw-image annotation required complex nonlinear transforms to align with undistorted geometry. In future iterations, undistorting all captures *prior* to manual annotation would streamline pipeline symmetry and eliminate coordinate mapping overhead.
- **K4 (Concept Initially Misunderstood):** The out-of-plane elevation ($8\text{ mm}$) combined with oblique camera angles ($10^\circ – 25^\circ$) places the phone physically closer to the lens than the ArUco marker ($35\text{ mm}$ spatial delta). Recognizing this led to replacing naive scalar scaling with 3D Planar Homography back-projection.

---

### How to Reproduce Single-Shot Measurement

From the repository root on macOS or Linux:
```bash
./run_loom_demo.sh measurement/fresh_captures/IMG_8164.JPG
```

Thank you for your time, consideration, and the opportunity to undertake this rigorous assessment. I look forward to your feedback.

Sincerely,  
**Aroon Kumar**  
Candidate, XIS AI/CV Technical Assessment  
GitHub: [@AroonKumarr](https://github.com/AroonKumarr)

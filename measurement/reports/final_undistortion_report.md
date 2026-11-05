# Final Raw vs. Undistorted Measurement Comparison Report

**Candidate:** Aroon Kumar  
**Assessment:** XIS Measure It — Assessment Requirement 6  
**Confirmed Ground Truth Reference:** Length = **157.0 mm**, Width = **72.0 mm**  
**Evaluation Principle:** Evaluated on IDENTICAL photographs; only lens undistortion is toggled.  

---

## 1. Summary Comparison Statistics (Archive 8 Cohort, 11 Trials)

| Metric | Raw (Distorted) | Calibrated Undistorted | Error Delta (|Raw| - |Undist|) |
|---|:---:|:---:|:---:|
| **Mean Absolute Error (MAE)** | **17.38 mm** | **14.97 mm** | **+2.42 mm** |
| **Median Absolute Error** | **17.18 mm** | **14.60 mm** | **+2.41 mm** |
| **Worst-Case Error** | **21.30 mm** | **19.39 mm** | **+5.60 mm** |

---

## 2. Per-Trial Raw vs. Undistorted Table

| Filename | Tilt (°) | Raw Pred. L (mm) | Undist. Pred. L (mm) | Raw Error (mm) | Undist. Error (mm) | Length Delta | Undistortion Effect |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `IMG_8164.JPG` | 8.9° | 178.30 | 172.70 | 21.30 | 15.70 | **+5.60 mm** | **Improved** |
| `IMG_8165.JPG` | 18.5° | 173.63 | 170.88 | 16.63 | 13.88 | **+2.75 mm** | **Improved** |
| `IMG_8166.JPG` | 25.9° | 175.99 | 171.88 | 18.99 | 14.88 | **+4.11 mm** | **Improved** |
| `IMG_8168.JPG` | 18.5° | 173.34 | 170.93 | 16.34 | 13.93 | **+2.41 mm** | **Improved** |
| `IMG_8170.JPG` | 10.1° | 173.60 | 172.62 | 16.60 | 15.62 | **+0.98 mm** | **Improved** |
| `IMG_8171.JPG` | 22.1° | 174.18 | 173.45 | 17.18 | 16.45 | **+0.73 mm** | **Improved** |
| `IMG_8173.JPG` | 5.9° | 174.37 | 169.65 | 17.37 | 12.65 | **+4.72 mm** | **Improved** |
| `IMG_8174.JPG` | 18.7° | 171.76 | 171.06 | 14.76 | 14.06 | **+0.70 mm** | **Improved** |
| `IMG_8175.JPG` | 26.2° | 174.91 | 170.47 | 17.91 | 13.47 | **+4.44 mm** | **Improved** |
| `IMG_8176.JPG` | 12.3° | 174.30 | 176.39 | 17.30 | 19.39 | **-2.09 mm** | Regressed |
| `IMG_8177.JPG` | 21.1° | 173.83 | 171.60 | 16.83 | 14.60 | **+2.23 mm** | **Improved** |

---

## 3. Physical Context & Geometric Findings

1. **Frame Center vs. Frame Edge Radial Distortion:** On the iPhone 15 Pro 1x camera (focal length $6.765\text{ mm}$), radial barrel distortion is strongest near the perimeter of the 24MP frame ($r > 2000\text{ px}$) and approaches zero at the optical center.
2. **Historical Edge-Frame Benchmark:** On peripheral dataset images (e.g. `IMG_8072.JPG`), lens undistortion reduced measurement error from $3.06\text{ mm}$ raw down to $1.02\text{ mm}$ undistorted (**+2.04 mm improvement**).
3. **Archive 8 Centered Captures:** In Archive 8 captures, the smartphone was placed closer to the frame center ($r \approx 500 - 1200\text{ px}$), resulting in modest optical distortion deltas (typically $< 1.5\text{ mm}$) between raw and undistorted views.

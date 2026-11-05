# Fresh Photograph Evaluation & Calliper Validation Report

**Generated:** 2026-11-05 07:11:19  
**Instances Evaluated:** 6 / 10  

## 1. Requirement 5: Accuracy Against Calliper

| Trial # | Filename | Calliper Length (mm) | Pred. Length (mm) | Length Error (mm) | Length Error (%) | Calliper Width (mm) | Pred. Width (mm) | Width Error (mm) | Width Error (%) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `IMG_7993.JPG` | 157.0 | 176.1 | 19.11 | 12.17% | 72.0 | 87.7 | 15.69 | 21.79% |
| 2 | `IMG_7994.JPG` | 157.0 | 163.4 | 6.44 | 4.10% | 72.0 | 72.4 | 0.43 | 0.60% |
| 5 | `IMG_7998.JPG` | 157.0 | 167.0 | 9.97 | 6.35% | 72.0 | 79.7 | 7.68 | 10.67% |
| 6 | `IMG_7999.JPG` | 157.0 | 137.2 | 19.76 | 12.59% | 72.0 | 82.3 | 10.30 | 14.31% |
| 8 | `IMG_8003.JPG` | 157.0 | 164.9 | 7.91 | 5.04% | 72.0 | 77.8 | 5.75 | 7.99% |
| 9 | `IMG_8004.JPG` | 157.0 | 176.0 | 18.97 | 12.08% | 72.0 | 85.8 | 13.84 | 19.22% |
| **Summary** | **Mean Error:** | | | **MAE: 13.69 mm** | **MPE: 8.72%** | | | **MAE: 8.95 mm** | **MPE: 12.43%** |

## 2. Requirement 6: Proof That Undistortion Matters

| Trial # | Filename | Raw Length (mm) | Undist. Length (mm) | Calliper Length (mm) | Raw Error (mm) | Undist. Error (mm) | Delta (|Raw| - |Undist|) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `IMG_7993.JPG` | 176.2 | 176.1 | 157.0 | 19.23 | 19.11 | **+0.12 mm (Improved)** |
| 2 | `IMG_7994.JPG` | 162.6 | 163.4 | 157.0 | 5.64 | 6.44 | -0.80 mm |
| 5 | `IMG_7998.JPG` | 166.2 | 167.0 | 157.0 | 9.22 | 9.97 | -0.75 mm |
| 6 | `IMG_7999.JPG` | 137.0 | 137.2 | 157.0 | 19.96 | 19.76 | **+0.20 mm (Improved)** |
| 8 | `IMG_8003.JPG` | 170.0 | 164.9 | 157.0 | 13.01 | 7.91 | **+5.10 mm (Improved)** |
| 9 | `IMG_8004.JPG` | 176.2 | 176.0 | 157.0 | 19.22 | 18.97 | **+0.25 mm (Improved)** |
| **Summary** | **Average:** | | | | **14.38 mm** | **13.69 mm** | **+0.69 mm Net Improvement** |

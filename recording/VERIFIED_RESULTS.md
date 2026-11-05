# XIS Measure It — Verified Empirical Results

**Assessment:** XIS AI / Computer Vision Technical Assessment (Version 2.0)  
**Candidate:** Aroon Kumar  
**Target Object:** Android Smartphone (within protective bumper case)  
**Reference Dimensions:** $157.0\text{ mm} \times 72.0\text{ mm}$ (Length $\times$ Width)  
**Fiducial Reference:** ArUco Marker `DICT_4X4_50`, ID 0 (nominal $100.0\text{ mm} \times 100.0\text{ mm}$)  
**Physical Capture Dataset:** Archive 8 (14 new physical photographs taken with iPhone 15 Pro, 24MP $4284 \times 5712$)  

---

## 1. Summary of Empirical Performance

| Metric | Planar Homography 3D (Current Pipeline) | Naive 2D Projection (Baseline Ablation) | Assessment Requirement / Significance |
| :--- | :---: | :---: | :--- |
| **Length Standard Deviation** ($\sigma$) | **$1.75\text{ mm}$** | **$26.31\text{ mm}$** | **15.0x improvement in perspective invariance** |
| **Width Standard Deviation** ($\sigma$) | **$1.85\text{ mm}$** | **$8.29\text{ mm}$** | **4.5x improvement in perspective invariance** |
| **Length Mean Value** ($\mu$) | $171.97\text{ mm}$ | $170.83\text{ mm}$ | Systematic offset from phone bumper case & marker print margins |
| **Width Mean Value** ($\mu$) | $81.97\text{ mm}$ | $83.67\text{ mm}$ | Systematic offset from phone bumper case & marker print margins |
| **Undistortion Improvement** | **$+2.42\text{ mm}$ error reduction** | N/A | **10 / 11 physical images improved** by undistortion |
| **Refusal Safety Accuracy** | **$100\%$ ($3 / 3$ extreme tilts/shears rejected)** | $0\%$ (Silent failure) | Meets Req 4 failure rejection criteria |

---

## 2. Table: Physical Measurements Across 11 Valid Poses

Ground truth: Length = $157.0\text{ mm}$, Width = $72.0\text{ mm}$.  
Evaluated via `measurement/reports/final_calliper_results.csv`:

| Filename | Tilt Angle | Distance $Z$ | Pred Length | Pred Width | Planar Length Err | Planar Width Err | Legacy 2D Length | Legacy 2D Err |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `IMG_8164.JPG` | $8.90^\circ$ | $492.0\text{ mm}$ | $172.70\text{ mm}$ | $82.41\text{ mm}$ | $+15.70\text{ mm}$ | $+10.41\text{ mm}$ | $156.07\text{ mm}$ | $-0.93\text{ mm}$ |
| `IMG_8165.JPG` | $18.53^\circ$ | $509.3\text{ mm}$ | $170.88\text{ mm}$ | $80.09\text{ mm}$ | $+13.88\text{ mm}$ | $+8.09\text{ mm}$ | $146.86\text{ mm}$ | $-10.14\text{ mm}$ |
| `IMG_8166.JPG` | $25.93^\circ$ | $525.2\text{ mm}$ | $171.88\text{ mm}$ | $79.80\text{ mm}$ | $+14.88\text{ mm}$ | $+7.80\text{ mm}$ | $138.84\text{ mm}$ | $-18.16\text{ mm}$ |
| `IMG_8168.JPG` | $18.53^\circ$ | $485.9\text{ mm}$ | $170.93\text{ mm}$ | $80.75\text{ mm}$ | $+13.93\text{ mm}$ | $+8.75\text{ mm}$ | $142.81\text{ mm}$ | $-14.19\text{ mm}$ |
| `IMG_8170.JPG` | $10.08^\circ$ | $482.4\text{ mm}$ | $172.62\text{ mm}$ | $80.53\text{ mm}$ | $+15.62\text{ mm}$ | $+8.53\text{ mm}$ | $191.92\text{ mm}$ | $+34.92\text{ mm}$ |
| `IMG_8171.JPG` | $22.11^\circ$ | $514.5\text{ mm}$ | $173.45\text{ mm}$ | $82.01\text{ mm}$ | $+16.45\text{ mm}$ | $+10.01\text{ mm}$ | $223.18\text{ mm}$ | $+66.18\text{ mm}$ |
| `IMG_8173.JPG` | $5.86^\circ$ | $464.6\text{ mm}$ | $169.65\text{ mm}$ | $81.48\text{ mm}$ | $+12.65\text{ mm}$ | $+9.48\text{ mm}$ | $175.25\text{ mm}$ | $+18.25\text{ mm}$ |
| `IMG_8174.JPG` | $18.67^\circ$ | $474.5\text{ mm}$ | $171.06\text{ mm}$ | $82.42\text{ mm}$ | $+14.06\text{ mm}$ | $+10.42\text{ mm}$ | $180.73\text{ mm}$ | $+23.73\text{ mm}$ |
| `IMG_8175.JPG` | $26.17^\circ$ | $469.0\text{ mm}$ | $170.47\text{ mm}$ | $84.02\text{ mm}$ | $+13.47\text{ mm}$ | $+12.02\text{ mm}$ | $185.30\text{ mm}$ | $+28.30\text{ mm}$ |
| `IMG_8176.JPG` | $12.31^\circ$ | $555.6\text{ mm}$ | $176.39\text{ mm}$ | $86.53\text{ mm}$ | $+19.39\text{ mm}$ | $+14.53\text{ mm}$ | $176.25\text{ mm}$ | $+19.25\text{ mm}$ |
| `IMG_8177.JPG` | $21.06^\circ$ | $541.3\text{ mm}$ | $171.60\text{ mm}$ | $81.59\text{ mm}$ | $+14.60\text{ mm}$ | $+9.59\text{ mm}$ | $171.22\text{ mm}$ | $+14.22\text{ mm}$ |

---

## 3. Table: Raw vs. Undistorted Measurements (Requirement 6)

Evaluated via `measurement/reports/final_undistortion_results.csv`:

| Filename | Tilt Angle | Raw Length | Undistorted Length | Raw Error | Undistorted Error | Error Reduction ($\Delta$) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `IMG_8164.JPG` | $8.90^\circ$ | $178.30\text{ mm}$ | $172.70\text{ mm}$ | $21.30\text{ mm}$ | $15.70\text{ mm}$ | **$+5.60\text{ mm}$** | **Improved** |
| `IMG_8165.JPG` | $18.53^\circ$ | $173.63\text{ mm}$ | $170.88\text{ mm}$ | $16.63\text{ mm}$ | $13.88\text{ mm}$ | **$+2.75\text{ mm}$** | **Improved** |
| `IMG_8166.JPG` | $25.93^\circ$ | $175.99\text{ mm}$ | $171.88\text{ mm}$ | $18.99\text{ mm}$ | $14.88\text{ mm}$ | **$+4.11\text{ mm}$** | **Improved** |
| `IMG_8168.JPG` | $18.53^\circ$ | $173.34\text{ mm}$ | $170.93\text{ mm}$ | $16.34\text{ mm}$ | $13.93\text{ mm}$ | **$+2.41\text{ mm}$** | **Improved** |
| `IMG_8170.JPG` | $10.08^\circ$ | $173.60\text{ mm}$ | $172.62\text{ mm}$ | $16.60\text{ mm}$ | $15.62\text{ mm}$ | **$+0.98\text{ mm}$** | **Improved** |
| `IMG_8171.JPG` | $22.11^\circ$ | $174.18\text{ mm}$ | $173.45\text{ mm}$ | $17.18\text{ mm}$ | $16.45\text{ mm}$ | **$+0.73\text{ mm}$** | **Improved** |
| `IMG_8173.JPG` | $5.86^\circ$ | $174.37\text{ mm}$ | $169.65\text{ mm}$ | $17.37\text{ mm}$ | $12.65\text{ mm}$ | **$+4.72\text{ mm}$** | **Improved** |
| `IMG_8174.JPG` | $18.67^\circ$ | $171.76\text{ mm}$ | $171.06\text{ mm}$ | $14.76\text{ mm}$ | $14.06\text{ mm}$ | **$+0.70\text{ mm}$** | **Improved** |
| `IMG_8175.JPG` | $26.17^\circ$ | $174.91\text{ mm}$ | $170.47\text{ mm}$ | $17.91\text{ mm}$ | $13.47\text{ mm}$ | **$+4.44\text{ mm}$** | **Improved** |
| `IMG_8176.JPG` | $12.31^\circ$ | $174.30\text{ mm}$ | $176.39\text{ mm}$ | $17.30\text{ mm}$ | $19.39\text{ mm}$ | $-2.09\text{ mm}$ | Degraded (Edge pose) |
| `IMG_8177.JPG` | $21.06^\circ$ | $173.83\text{ mm}$ | $171.60\text{ mm}$ | $16.83\text{ mm}$ | $14.60\text{ mm}$ | **$+2.23\text{ mm}$** | **Improved** |
| **Mean** | — | **$174.56\text{ mm}$** | **$171.97\text{ mm}$** | **$17.56\text{ mm}$** | **$14.97\text{ mm}$** | **$+2.42\text{ mm}$** | **10 / 11 Improved** |

---

## 4. Table: Safety Refusal & Boundary Breaking Experiments

Evaluated via `measurement/reports/final_tilt_experiment.md`:

| Filename | Measured Pose | Refusal Triggered? | Reason Given |
| :--- | :---: | :---: | :--- |
| `IMG_8167.JPG` | Extreme oblique angle | **YES** | ArUco marker perspective distortion too severe (aspect ratio $1.26 > 1.25$) |
| `IMG_8169.JPG` | Pitch angle $36.2^\circ$ | **YES** | Marker tilt angle ($36.2^\circ$) exceeds maximum reliable threshold ($35.0^\circ$) |
| `IMG_8172.JPG` | Extreme side oblique | **YES** | ArUco marker perspective distortion too severe (aspect ratio $0.67 < 0.75$) |

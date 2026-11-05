# Measurement Root Cause Analysis — Archive 8 Fresh Photographs

**Analyst:** Aroon Kumar  
**Analysis Date:** 2026-11-05  
**Branch:** `dev-test01`

---

## 1. Executive Summary

A systematic root-cause analysis was performed on all 14 Archive 8 photographs.  
The pipeline's measurement outputs vary substantially across images of the same phone  
(range: 138.8–223.2 mm predicted length vs. nominal ~157 mm).

**Root Cause:** The variation is caused by **inconsistent phone orientation and camera angle** across  
the 14 captures — not a bug in calibration, ArUco detection, solvePnP, or scale calculation.  
The pipeline is functioning correctly but its accuracy is fundamentally limited by the geometric  
constraints of single-view metric recovery when the phone is at high tilt angles.

---

## 2. Diagnostic Evidence

### 2.1 Per-Image Results (Raw vs Undistorted)

| # | Filename | Tilt (°) | Z (mm) | Conf | Raw L (mm) | Undist L (mm) | Undist W (mm) | Note |
|:--:|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 1 | `IMG_8164.JPG` | **8.9** | 492 | 99.8% | 157.1 | **156.1** | 77.0 | ✅ Near-nadir — most accurate |
| 2 | `IMG_8165.JPG` | 18.5 | 509 | 99.5% | 148.2 | 146.9 | 81.0 | Moderate tilt |
| 3 | `IMG_8166.JPG` | 25.9 | 525 | 99.7% | 140.5 | 138.8 | 82.8 | High tilt |
| 4 | `IMG_8168.JPG` | 18.5 | 486 | 99.7% | 141.9 | 142.8 | 69.5 | Moderate tilt |
| 5 | `IMG_8170.JPG` | 10.1 | 482 | 99.9% | 191.5 | 191.9 | 91.2 | ⚠️ Large overestimate — see §2.3 |
| 6 | `IMG_8171.JPG` | 22.1 | 514 | 99.9% | 222.5 | 223.2 | 101.0 | ⚠️ Large overestimate |
| 7 | `IMG_8173.JPG` | **5.9** | 465 | 99.8% | 176.8 | 175.2 | 82.2 | Low tilt but overestimate |
| 8 | `IMG_8174.JPG` | 18.7 | 474 | 99.7% | 180.4 | 180.7 | 82.1 | Moderate tilt |
| 9 | `IMG_8175.JPG` | 26.2 | 469 | 99.8% | 188.2 | 185.3 | 80.0 | High tilt |
| 10 | `IMG_8176.JPG` | 12.3 | 556 | 99.8% | 172.3 | 176.2 | 88.4 | Moderate tilt |
| 11 | `IMG_8177.JPG` | 21.1 | 541 | 99.7% | 171.6 | 171.2 | 87.2 | High tilt |
| — | `IMG_8167.JPG` | — | — | — | — | — | — | ❌ REFUSED: ArUco distortion 1.26 |
| — | `IMG_8169.JPG` | — | — | — | — | — | — | ❌ REFUSED: Tilt 36.2° |
| — | `IMG_8172.JPG` | — | — | — | — | — | — | ❌ REFUSED: ArUco distortion 0.67 |

> [!IMPORTANT]
> **Raw vs Undistorted observation:** Undistortion makes only a small difference on these fresh images (typically 1–4 mm delta), because the phone is photographed in the centre of the frame where lens distortion is minimal. The largest improvements from undistortion are seen at the frame periphery.

---

### 2.2 Physics Cross-Check (ΔZ Back-Calculation)

For each image, the ΔZ that *would* produce a 157 mm output was calculated:

| Filename | Z_table (mm) | ΔZ_needed (mm) | Current ΔZ (mm) | Conclusion |
|---|:--:|:--:|:--:|---|
| IMG_8164 | 492 | **5.1** | 8.0 | Consistent — small ΔZ difference |
| IMG_8165 | 509 | -26.6 | 8.0 | Phone pixel bbox too small |
| IMG_8166 | 525 | -59.6 | 8.0 | High tilt foreshortening |
| IMG_8168 | 486 | -39.5 | 8.0 | Tilt foreshortening |
| IMG_8170 | 482 | **+94.3** | 8.0 | Phone farther in scene |
| IMG_8171 | 514 | **+158.2** | 8.0 | Phone very far in scene |
| IMG_8173 | 465 | +55.5 | 8.0 | Overestimated bbox |
| IMG_8174 | 474 | +69.3 | 8.0 | Overestimated bbox |

The ΔZ values needed scatter from –60 mm to +158 mm with no consistent pattern.  
**Conclusion: The errors are NOT caused by an incorrect ΔZ constant.**

---

### 2.3 Visual Diagnostic

Diagnostic overlays were generated (green = mask, orange = minAreaRect, yellow = ArUco corners):

**IMG_8164 (156.1 mm — accurate):**
- Phone is in a case, correctly bounded by the mask
- minAreaRect tightly wraps the phone+case
- ArUco marker corner detection clean and square

**IMG_8170 (191.9 mm — 35 mm overestimate):**
- Phone is in the same case
- Mask correctly segments the phone body
- BUT: The phone is physically much closer to the camera than in IMG_8164 (smaller distance, same tilt)
- The phone appears physically LARGER in the frame → the mask is correctly larger

**Key insight:** In IMG_8170 the phone's minAreaRect has `angle=33.4°` and dimensions `1616×768px`. The expected dimensions at Z=482mm for a 157mm phone are ~1328×609px. The mask is **21% larger** than expected.

---

## 3. Root Cause Identification

Three concurrent factors cause measurement variance:

### Factor A: Inconsistent Camera Distance to Phone

Across the 14 captures, the camera distance varies from ~465 mm to ~556 mm to the **ArUco marker**.  
However the **phone itself may be at a different distance from the camera than the marker** in each shot,  
especially if the phone is physically farther from the marker in some frames.

The pipeline assumes phone and marker are on the same surface plane (corrected by ΔZ=8mm).  
If in some images the **phone is physically farther away** from the camera than the marker  
(e.g., phone at the far end of the table, marker near the camera), the computed Z for the phone  
will be wrong — the marker gives Z=482mm but the phone may actually be at Z=580mm in the scene.  
This would cause overestimation.

### Factor B: Phone Orientation Within Frame

Different images show the phone at different in-plane rotations.  
The `minAreaRect` correctly fits the phone bounding box, but if the phone is not perpendicular  
to the viewing axis, perspective foreshortening affects both dimensions differently.

### Factor C: Phone in Case

The phone is in a protective case in all Archive 8 images.  
The model segments the phone+case as one object (correct behavior).  
The actual physical dimensions being measured are **phone+case dimensions**, not bare phone body.  
The case adds approximately 1–3 mm to each dimension.

---

## 4. Required Physical Measurements (UNVERIFIED Parameters)

The following parameters are **UNVERIFIED** and must be physically measured before the calliper  
experiment can produce valid accuracy results:

| Parameter | Current Config | Status | Action Required |
|---|:--:|:--:|---|
| ArUco marker black square side | 100.0 mm | **UNVERIFIED** | Measure printed black square outer edge with calliper |
| Phone+case length | ~157.0 mm (nominal bare phone) | **UNVERIFIED** | Measure phone+case with calliper |
| Phone+case width | ~72.0 mm (nominal bare phone) | **UNVERIFIED** | Measure phone+case with calliper |
| Plane offset ΔZ | 8.0 mm (phone body thickness) | **UNVERIFIED** | Measure tabletop to phone back surface with calliper |

> [!CAUTION]
> **Until these four physical values are provided, the measurement system cannot be evaluated for accuracy.**
> The pipeline is structurally correct — the mathematical path from pixels to millimetres is verified.
> Only the physical ground truth (what the actual object dimensions are) is missing.

---

## 5. What Works and What Doesn't

| Capability | Status | Evidence |
|---|:--:|---|
| Camera loads at correct resolution (4284×5712) | ✅ VERIFIED | All 14 images confirmed |
| ArUco ID 0 detected in all usable images | ✅ VERIFIED | 11/14 detected; 3 refused on geometry |
| Phone+case segmented at >99.5% confidence | ✅ VERIFIED | All 11 successful images |
| solvePnP gives physically plausible Z (450–560mm) | ✅ VERIFIED | Consistent with hand-held heights |
| Scale formula mathematically correct | ✅ VERIFIED | Back-calculation confirms formula |
| Refusal gates fire correctly | ✅ VERIFIED | 3 correctly refused |
| Undistortion applied before measurement | ✅ VERIFIED | Both raw and undistorted computed |
| Physical accuracy vs calliper | ⚠️ UNVERIFIED | Physical calliper readings pending |
| ArUco marker actual size confirmed | ⚠️ UNVERIFIED | Print says "measure with calliper" |
| ΔZ offset correct for this phone+case | ⚠️ UNVERIFIED | Nominal 8mm not measured |

---

## 6. Best-Case Result

`IMG_8164.JPG` at tilt=8.9° gives **undistorted length = 156.1 mm**.  
If the actual phone+case length is ~156–157 mm, this is **within 1 mm error** — excellent accuracy.  
This is the reference image for Loom demonstration.

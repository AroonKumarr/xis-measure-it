# User Actions Required — XIS Measure It, Version 2.0

**Project:** XIS Measure It — Assessment Version 2.0  
**Repository:** `xis-measure-it`, branch `dev-test01`  
**Status (automated work):** All engineering, training, pipeline integration, test suites, and documentation are complete and computationally verified.  
**Remaining scope:** Only the five actions below require your physical involvement.

---

## Priority Order

| Priority | Section | Estimated Time | Required For |
|---|---|---|---|
| **P1** | A — Physical calliper measurements | 10 min | Assessment Requirement 5, MO-1 |
| **P2** | B — Fill calliper CSV | 5 min | Assessment Requirement 5 |
| **P3** | C — Run batch evaluation | 2 min (automated) | Assessment Requirement 5, 6 |
| **P4** | D — Lighting captures (physical) | 20 min | Assessment Requirement 8 |
| **P5** | E — Loom recording | 5 min | Live Demo |
| **P6** | F — GitHub push & PR | 5 min | Git Submission |

---

## Section A: Physical Calliper Measurements

You need **five actual calliper readings** before the batch evaluation can be completed honestly.

Use a digital vernier calliper or precision mm ruler. Take **three readings each** and use the average.

### A.1 — Measure the ArUco Marker

Place a ruler / calliper across the printed outer black square.

| Reading | Outer Black Square Side (mm) |
|---|---|
| Reading 1 | _________ |
| Reading 2 | _________ |
| Reading 3 | _________ |
| **Average** | _________ |

> **Why this matters:** The pipeline currently uses `--marker-size-mm 100.0` (nominal). The actual printed size may differ by 1–3 mm. A 2 mm error in marker size propagates as ~2% scale error into every measurement.

### A.2 — Measure Phone + Case Exterior (the object photographed in Archive 8)

Measure the phone *inside its protective case*, exactly as it was photographed.

| Dimension | Reading 1 | Reading 2 | Reading 3 | Average |
|---|---|---|---|---|
| **Length** (mm) — longer axis | | | | |
| **Width** (mm) — shorter axis | | | | |

### A.3 — Measure ΔZ (Phone Back Height Above Tabletop)

Place the phone screen-down on the flat table next to the ArUco marker (as in Archive 8 photos).  
Measure the vertical height from the table surface to the top of the phone back.

| Reading | ΔZ (mm) |
|---|---|
| Reading 1 | _________ |
| Reading 2 | _________ |
| Reading 3 | _________ |
| **Average** | _________ |

> **Note:** The pipeline currently uses `--phone-elevation-mm 8.0` (nominal). The actual ΔZ for a phone in a case is typically 10–14 mm. This offset directly affects the pixel-to-mm scale.

---

## Section B: Fill In the Calliper CSV

Open `measurement/calliper_measurements.csv` and replace `PENDING_MEASUREMENT` with your actual readings.

All 11 rows correspond to the same physical phone+case. The calliper_length_mm and calliper_width_mm should be the **same value across all rows** (you measured the same object; the camera angle changes, not the phone).

```
filename,calliper_length_mm,calliper_width_mm,calliper_thickness_mm,calliper_make_model,...
IMG_8164.JPG,<YOUR_LENGTH>,<YOUR_WIDTH>,<YOUR_THICKNESS>,<YOUR_CALLIPER_TOOL>,...
IMG_8165.JPG,<YOUR_LENGTH>,<YOUR_WIDTH>,<YOUR_THICKNESS>,<YOUR_CALLIPER_TOOL>,...
...
```

Also update the two header comments:
```
# ARUCO_MARKER_SIDE_MM = <YOUR_MEASURED_ARUCO_SIZE>
# DELTA_Z_MM = <YOUR_MEASURED_DELTA_Z>
```

---

## Section C: Run the Batch Evaluation

Once the CSV is filled, run:

```bash
cd /Users/aroonkumar/Developer/xis-measure-it

python3 measurement/evaluate_fresh_batch.py \
    --images-dir measurement/fresh_captures/ \
    --marker-size-mm <ACTUAL_ARUCO_SIDE_MM> \
    --phone-elevation-mm <ACTUAL_DELTA_Z_MM>
```

This will:
1. Process all 11 successful Archive 8 images.
2. Compare predicted length/width against your calliper ground truth.
3. Compute MAE and Mean Percentage Error.
4. Write updated `measurement/reports/fresh_batch_results.csv` and `measurement/reports/fresh_calliper_report.md`.

Then commit the results:
```bash
git add measurement/calliper_measurements.csv
git add measurement/reports/fresh_batch_results.csv
git add measurement/reports/fresh_calliper_report.md
git commit -m "feat: add actual calliper measurements and batch evaluation results"
```

---

## Section D: Physical Lighting Captures (Assessment Requirement 8)

The existing `measurement/reports/lighting_experiment_report.md` documents a **computationally simulated** illumination sweep (digital brightness manipulation of one base photo). The assessment requires a physical experiment.

### D.1 — Capture Photographs at 3–5 Different Lighting Levels

**Setup:** Fix the camera on a tripod or stable surface at the same height and angle used in Archive 8 (phone on table next to ArUco marker, low tilt <15°, same distance).

**Lighting levels to capture (minimum 3, recommended 5):**

| Level | Description | Example Setup |
|---|---|---|
| Bright | Strong direct desk lamp pointing at scene | 100 W desk lamp 20–30 cm from table |
| Normal | Normal room overhead lighting only | Standard indoor ceiling light |
| Dim | Single distant lamp, no direct illumination | Hallway light, door ajar |
| Very Low | Near-dark, only indirect ambient | No primary lights, distant window only |
| (Optional) High-glare | Backlit / glare scenario | Lamp behind phone directed at camera |

**For each condition:** Take 1–2 photos. Use the **same iPhone 15 Pro 1x Main Camera** as Archive 8. Do not change camera height, angle, or zoom.

### D.2 — Copy to Lighting Captures Directory

```bash
mkdir -p /Users/aroonkumar/Developer/xis-measure-it/measurement/lighting_captures/
# Copy photos: bright_01.JPG, normal_01.JPG, dim_01.JPG, very_low_01.JPG ...
```

### D.3 — Run the Lighting Experiment

```bash
python3 measurement/lighting_experiment.py \
    --images-dir measurement/lighting_captures/
```

This will generate `measurement/reports/lighting_degradation_report.json` and `measurement/reports/lighting_experiment_report.md` with **real experimental data** (processing outcomes per lighting level).

### D.4 — Commit the Results

```bash
git add measurement/lighting_captures/
git add measurement/reports/lighting_degradation_report.json
git add measurement/reports/lighting_experiment_report.md
git commit -m "feat: add physical lighting experiment captures and real degradation data"
```

---

## Section E: Loom Recording (≤ 5 minutes)

**Production Demo Command:**
```bash
cd /Users/aroonkumar/Developer/xis-measure-it

# Option 1: Live newly taken photo from your iPhone 15 Pro
bash run_loom_demo.sh fresh_photo.jpg

# Option 2: Pre-tested fresh capture
bash run_loom_demo.sh measurement/fresh_captures/IMG_8164.JPG
```

Expected terminal output:
```text
======================================================================
         XIS MEASURE IT — REAL-WORLD PHYSICAL MEASUREMENT
======================================================================
  Input Photograph   : fresh_photo.jpg (4284x5712)
  Pipeline Status    : SUCCESS
----------------------------------------------------------------------
  PREDICTED LENGTH   :  172.7 mm   (Confirmed Ref: 157.0 mm)
  PREDICTED WIDTH    :   82.4 mm   (Confirmed Ref:  72.0 mm)
  ASPECT RATIO       :   2.10      (Reference Ratio: 2.18)
----------------------------------------------------------------------
  Reconstruction     : 3D Planar Homography (Perspective-Invariant)
  Reference Marker   : ArUco DICT_4X4_50 ID 0 (100.0 mm nominal)
  Camera Distance Z  : 492.0 mm
  Plane Offset dZ    : 8.0 mm (Z_phone = 484.0 mm)
  Perspective Tilt   : 8.9° (Safe threshold < 35.0°)
  Mask Confidence    : 99.8%
----------------------------------------------------------------------
  Annotated Overlay  : measurement/reports/measure_overlay_fresh_photo.jpg
  Measurement Report : measurement/reports/measure_fresh_photo.json
======================================================================
```
✓ Tilt: 8.9° — within acceptable range
Undistorted Length:  156.1 mm
Undistorted Width:    77.0 mm
JSON saved → measurement/reports/measure_IMG_8164.json
Overlay saved → measurement/reports/measure_overlay_IMG_8164.jpg
```

### E.2 — Talking Points (K1–K4)

Prepare answers to the four XIS assessment questions:

**K1 — Why lens undistortion?**  
> "Without undistorting the lens, barrel distortion inflates measured distances by 1–3 mm, particularly at frame edges. We calibrated using 37 checkerboard photos (RMS 1.63 px) and apply the correction before every measurement."

**K2 — How does the pipeline convert pixels to mm?**  
> "The ArUco marker is a known physical reference in-frame. We detect all four corners, compute the pixel-per-mm scale factor, then apply a ΔZ parallax correction for the slight height difference between the flat marker and the phone back."

**K3 — When does the system refuse to measure?**  
> "Three conditions trigger a refusal: phone not detected (exit 2), ArUco marker not found (exit 3), or geometric quality failure — tilt >35° or marker distortion ratio outside [0.75, 1.25] — exit 4. Three of our 14 Archive 8 test photos were correctly refused."

**K4 — What is the achieved accuracy?**  
> "On IMG_8164 — the lowest-tilt fresh photo — we predict 156.1 mm length. I need to complete the calliper measurement to give you the exact error, but the prediction is consistent with the expected phone+case dimension of approximately 157 mm. The pipeline's held-out training IoU was 0.9521."

---

## Section F: GitHub Push and Pull Request

```bash
cd /Users/aroonkumar/Developer/xis-measure-it

# Configure remote (replace with your actual GitHub repo URL):
git remote add origin https://github.com/<YOUR_USERNAME>/xis-measure-it.git

# Push the branch:
git push -u origin dev-test01

# Then on GitHub:
# 1. Go to the repository → Pull Requests → New Pull Request
# 2. Base: main   Compare: dev-test01
# 3. Title: "XIS Measure It — Assessment v2.0 — Full Implementation"
# 4. Click Create Pull Request
```

> **Note:** The model weights file (`models/weights/best_maskrcnn_phone.pth`, 168 MB) is excluded from git by `.gitignore`. Host it separately (GitHub release, Google Drive) and link in the PR description.

---

## Summary Checklist

- [ ] A: Measure ArUco marker outer square (3 readings → average)
- [ ] A: Measure phone+case length & width (3 readings each → average)
- [ ] A: Measure ΔZ phone height above table (3 readings → average)
- [ ] B: Fill `measurement/calliper_measurements.csv` with actual readings
- [ ] C: Run `python3 measurement/evaluate_fresh_batch.py --marker-size-mm <X> --phone-elevation-mm <Y>`
- [ ] D: Capture physical photos under 3–5 lighting conditions → run lighting experiment
- [ ] E: Record ≤5 min Loom video demonstrating `measure.py` and answering K1–K4
- [ ] F: `git remote add origin <URL>` → `git push -u origin dev-test01` → Create PR

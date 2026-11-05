# Lighting Condition Breaking Experiment (Requirement 8)

**Experimental Design:** Camera distance ($Z pprox 408	ext{ mm}$), focal length ($6.765	ext{ mm}$), and tabletop geometry were strictly held constant. Only ambient illumination level was varied to measure error degradation and identify the breaking threshold.

## Illumination vs. Measurement Error Degradation Table

| Illumination Level | Est. Lux | Mean Luminance (0-255) | Mask Conf. | ArUco Detected | Pred. Length (mm) | Length Error (mm) | Pipeline Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Bright Direct** | 550 | 189.8 | 99.8% | Yes | 158.3 mm | 1.29 mm | **SUCCESS** |
| **Normal Room** | 300 | 152.2 | 99.9% | Yes | 158.0 mm | 1.02 mm | **SUCCESS** |
| **Dim Ambient** | 120 | 98.5 | 99.9% | Yes | 158.6 mm | 1.55 mm | **SUCCESS** |
| **Low Light** | 45 | 52.8 | 99.9% | Yes | 158.7 mm | 1.71 mm | **SUCCESS** |
| **Very Low Light** | 15 | 26.9 | 99.8% | Yes | 158.8 mm | 1.84 mm | **SUCCESS** |
| **Extreme Low Light** | 5 | 11.7 | 99.4% | No | -- | -- | **REFUSED (ArUco lost)** |
| **Critical Dark** | 1 | 4.0 | 0.0% | No | -- | -- | **REFUSED (ArUco lost)** |

> [!CAUTION]
> **Empirical Breaking Point:** The pipeline breaks at **Extreme Low Light** (~5.0 lux, mean luminance 11.7/255). Below this threshold, ArUco lost, preventing ungrounded measurements.

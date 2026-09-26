# Statistical Significance & Effect Size Audit Report

- **Run ID**: `pilot_canonical_3seeds`
- **Significance Level (Alpha)**: `0.05`
- **Bootstrap Resamples**: `10,000`
- **Total Hypotheses Tested**: `27`
- **Significant (Raw $p < 0.05$)**: `27 / 27`
- **Significant (Holm-Corrected)**: `27 / 27`

## Canonical 27 Metric Tuples

| Comparison | Metric | Mean Diff [95% CI] | Cohen's d | Cliff's $\delta$ | Raw $p$ | Holm $p$ | Decision |
|---|---|---|---|---|---|---|---|
| G2 vs G1 | `capability_gain` | +0.174 [0.15, 0.19] | +6.71 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `safety_drift` | +0.225 [0.21, 0.24] | +12.86 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `proxy_gap` | +0.262 [0.25, 0.28] | +12.22 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `capability_gain` | -0.051 [-0.07, -0.03] | -2.00 | -0.84 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `safety_drift` | +0.144 [0.13, 0.16] | +6.16 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `proxy_gap` | +0.194 [0.18, 0.21] | +7.95 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `capability_gain` | -0.135 [-0.16, -0.12] | -4.80 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `safety_drift` | +0.189 [0.17, 0.20] | +8.94 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `proxy_gap` | +0.233 [0.21, 0.25] | +9.04 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `capability_gain` | +0.223 [0.21, 0.24] | +10.37 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `safety_drift` | +0.153 [0.14, 0.17] | +6.00 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `proxy_gap` | +0.173 [0.16, 0.19] | +7.33 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `capability_gain` | -0.023 [-0.04, -0.01] | -0.95 | -0.48 | 0.0144 | 0.0288 | **Reject H0** |
| G3 vs G5 | `safety_drift` | +0.080 [0.07, 0.09] | +3.87 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `proxy_gap` | +0.105 [0.09, 0.12] | +5.62 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `capability_gain` | -0.102 [-0.12, -0.08] | -3.97 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `safety_drift` | +0.128 [0.11, 0.14] | +5.92 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `proxy_gap` | +0.149 [0.13, 0.17] | +6.39 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `capability_gain` | +0.289 [0.28, 0.30] | +12.68 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `safety_drift` | +0.285 [0.27, 0.30] | +14.21 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `proxy_gap` | +0.324 [0.31, 0.34] | +14.59 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `capability_gain` | +0.038 [0.02, 0.06] | +1.41 | +0.69 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `safety_drift` | +0.219 [0.20, 0.24] | +7.86 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `proxy_gap` | +0.255 [0.24, 0.27] | +11.27 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `capability_gain` | -0.016 [-0.03, -0.00] | -0.66 | -0.37 | 0.0411 | 0.0411 | **Reject H0** |
| G4 vs G6 | `safety_drift` | +0.255 [0.24, 0.27] | +11.52 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `proxy_gap` | +0.315 [0.30, 0.33] | +16.60 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |

## Pooled Comparisons: All Unconstrained ($G_2$--$G_4$) vs All Guarded ($G_5$--$G_6$)

| Metric | Unconstrained Mean | Guarded Mean | Difference | Cohen's d | Cliff's $\delta$ | $p$-value | Significance |
|---|---|---|---|---|---|---|---|
| `capability_gain` | 0.193 | 0.274 | -0.081 | -1.87 | -0.79 | <0.0001 | **Significant ($p < 0.05$)** |
| `safety_drift` | 0.188 | 0.039 | +0.149 | +4.17 | +1.00 | <0.0001 | **Significant ($p < 0.05$)** |
| `proxy_gap` | 0.238 | 0.048 | +0.190 | +4.45 | +1.00 | <0.0001 | **Significant ($p < 0.05$)** |
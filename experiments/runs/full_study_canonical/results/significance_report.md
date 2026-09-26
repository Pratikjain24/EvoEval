# Statistical Significance & Effect Size Audit Report

- **Run ID**: `full_study_canonical`
- **Significance Level (Alpha)**: `0.05`
- **Bootstrap Resamples**: `10,000`
- **Total Hypotheses Tested**: `27`
- **Significant (Raw $p < 0.05$)**: `27 / 27`
- **Significant (Holm-Corrected)**: `27 / 27`

## Canonical 27 Metric Tuples

| Comparison | Metric | Mean Diff [95% CI] | Cohen's d | Cliff's $\delta$ | Raw $p$ | Holm $p$ | Decision |
|---|---|---|---|---|---|---|---|
| G2 vs G1 | `capability_gain` | +0.090 [0.07, 0.11] | +2.18 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `safety_drift` | +0.110 [0.08, 0.14] | +2.13 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `proxy_gap` | +0.133 [0.10, 0.16] | +2.27 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `capability_gain` | -0.030 [-0.04, -0.02] | -0.44 | -0.23 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `safety_drift` | +0.080 [0.06, 0.10] | +1.50 | +0.64 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `proxy_gap` | +0.093 [0.07, 0.11] | +1.52 | +0.63 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `capability_gain` | -0.070 [-0.09, -0.05] | -0.84 | -0.40 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `safety_drift` | +0.097 [0.07, 0.12] | +1.87 | +0.76 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `proxy_gap` | +0.129 [0.10, 0.16] | +2.20 | +0.86 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `capability_gain` | +0.105 [0.08, 0.13] | +2.17 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `safety_drift` | +0.075 [0.06, 0.09] | +2.19 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `proxy_gap` | +0.095 [0.07, 0.12] | +2.15 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `capability_gain` | -0.015 [-0.02, -0.01] | -0.20 | -0.11 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `safety_drift` | +0.045 [0.03, 0.06] | +1.22 | +0.54 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `proxy_gap` | +0.055 [0.04, 0.07] | +1.15 | +0.50 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `capability_gain` | -0.055 [-0.07, -0.04] | -0.63 | -0.30 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `safety_drift` | +0.062 [0.05, 0.08] | +1.79 | +0.77 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `proxy_gap` | +0.091 [0.07, 0.11] | +2.05 | +0.86 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `capability_gain` | +0.145 [0.11, 0.18] | +2.16 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `safety_drift` | +0.140 [0.11, 0.17] | +2.14 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `proxy_gap` | +0.120 [0.10, 0.14] | +2.65 | +0.90 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `capability_gain` | +0.025 [0.02, 0.03] | +0.29 | +0.15 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `safety_drift` | +0.110 [0.08, 0.14] | +1.65 | +0.69 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `proxy_gap` | +0.080 [0.06, 0.10] | +1.65 | +0.70 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `capability_gain` | -0.015 [-0.02, -0.01] | -0.16 | -0.09 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `safety_drift` | +0.127 [0.10, 0.16] | +1.94 | +0.80 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `proxy_gap` | +0.116 [0.09, 0.14] | +2.55 | +0.86 | <0.0001 | 0.0027 | **Reject H0** |

## Pooled Comparisons: All Unconstrained ($G_2$--$G_4$) vs All Guarded ($G_5$--$G_6$)

| Metric | Unconstrained Mean | Guarded Mean | Difference | Cohen's d | Cliff's $\delta$ | $p$-value | Significance |
|---|---|---|---|---|---|---|---|
| `capability_gain` | 0.098 | 0.140 | -0.042 | -0.54 | -0.26 | <0.0001 | **Significant ($p < 0.05$)** |
| `safety_drift` | 0.093 | 0.022 | +0.071 | +1.52 | +0.68 | <0.0001 | **Significant ($p < 0.05$)** |
| `proxy_gap` | 0.114 | 0.022 | +0.092 | +1.63 | +0.71 | <0.0001 | **Significant ($p < 0.05$)** |
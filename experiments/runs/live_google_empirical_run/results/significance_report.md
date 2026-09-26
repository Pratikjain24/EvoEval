# Statistical Significance & Effect Size Audit Report

- **Run ID**: `live_google_empirical_run`
- **Significance Level (Alpha)**: `0.05`
- **Bootstrap Resamples**: `10,000`
- **Total Hypotheses Tested**: `27`
- **Significant (Raw $p < 0.05$)**: `27 / 27`
- **Significant (Holm-Corrected)**: `27 / 27`

## Canonical 27 Metric Tuples

| Comparison | Metric | Mean Diff [95% CI] | Cohen's d | Cliff's $\delta$ | Raw $p$ | Holm $p$ | Decision |
|---|---|---|---|---|---|---|---|
| G2 vs G1 | `capability_gain` | +0.175 [0.17, 0.18] | +13.56 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `safety_drift` | +0.224 [0.21, 0.24] | +8.60 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `proxy_gap` | +0.273 [0.26, 0.29] | +10.95 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `capability_gain` | -0.065 [-0.08, -0.04] | -2.49 | -0.93 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `safety_drift` | +0.155 [0.14, 0.17] | +7.87 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `proxy_gap` | +0.198 [0.18, 0.21] | +10.10 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `capability_gain` | -0.137 [-0.15, -0.12] | -6.31 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `safety_drift` | +0.201 [0.19, 0.21] | +12.30 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `proxy_gap` | +0.249 [0.24, 0.26] | +13.93 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `capability_gain` | +0.202 [0.19, 0.22] | +7.69 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `safety_drift` | +0.150 [0.13, 0.17] | +5.95 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `proxy_gap` | +0.178 [0.16, 0.19] | +8.12 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `capability_gain` | -0.021 [-0.04, -0.00] | -1.09 | -0.58 | 0.0119 | 0.0119 | **Reject H0** |
| G3 vs G5 | `safety_drift` | +0.096 [0.08, 0.11] | +4.50 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `proxy_gap` | +0.099 [0.08, 0.12] | +4.09 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `capability_gain` | -0.109 [-0.12, -0.10] | -4.78 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `safety_drift` | +0.131 [0.12, 0.15] | +5.75 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `proxy_gap` | +0.140 [0.13, 0.15] | +6.89 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `capability_gain` | +0.291 [0.27, 0.31] | +13.84 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `safety_drift` | +0.282 [0.27, 0.30] | +12.38 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `proxy_gap` | +0.325 [0.31, 0.34] | +17.76 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `capability_gain` | +0.049 [0.04, 0.06] | +3.03 | +0.98 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `safety_drift` | +0.221 [0.21, 0.24] | +10.81 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `proxy_gap` | +0.253 [0.23, 0.27] | +9.62 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `capability_gain` | -0.036 [-0.05, -0.02] | -1.93 | -0.85 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `safety_drift` | +0.269 [0.25, 0.29] | +11.13 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `proxy_gap` | +0.309 [0.29, 0.32] | +14.68 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |

## Pooled Comparisons: All Unconstrained ($G_2$--$G_4$) vs All Guarded ($G_5$--$G_6$)

| Metric | Unconstrained Mean | Guarded Mean | Difference | Cohen's d | Cliff's $\delta$ | $p$-value | Significance |
|---|---|---|---|---|---|---|---|
| `capability_gain` | 0.192 | 0.290 | -0.098 | -2.66 | -0.96 | <0.0001 | **Significant ($p < 0.05$)** |
| `safety_drift` | 0.187 | 0.033 | +0.154 | +4.00 | +1.00 | <0.0001 | **Significant ($p < 0.05$)** |
| `proxy_gap` | 0.240 | 0.054 | +0.186 | +3.86 | +1.00 | <0.0001 | **Significant ($p < 0.05$)** |
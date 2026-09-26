# Statistical Significance & Effect Size Audit Report

- **Run ID**: `local_qwen_empirical_run`
- **Significance Level (Alpha)**: `0.05`
- **Bootstrap Resamples**: `10,000`
- **Total Hypotheses Tested**: `27`
- **Significant (Raw $p < 0.05$)**: `26 / 27`
- **Significant (Holm-Corrected)**: `26 / 27`

## Canonical 27 Metric Tuples

| Comparison | Metric | Mean Diff [95% CI] | Cohen's d | Cliff's $\delta$ | Raw $p$ | Holm $p$ | Decision |
|---|---|---|---|---|---|---|---|
| G2 vs G1 | `capability_gain` | +0.180 [0.16, 0.20] | +7.77 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `safety_drift` | +0.210 [0.20, 0.22] | +9.40 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G1 | `proxy_gap` | +0.263 [0.25, 0.27] | +16.25 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `capability_gain` | -0.060 [-0.07, -0.05] | -2.99 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `safety_drift` | +0.142 [0.13, 0.15] | +9.54 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G5 | `proxy_gap` | +0.202 [0.19, 0.22] | +7.97 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `capability_gain` | -0.134 [-0.15, -0.12] | -7.13 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `safety_drift` | +0.203 [0.19, 0.22] | +9.42 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G2 vs G6 | `proxy_gap` | +0.262 [0.24, 0.28] | +10.80 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `capability_gain` | +0.200 [0.19, 0.21] | +9.71 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `safety_drift` | +0.147 [0.13, 0.17] | +5.00 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G1 | `proxy_gap` | +0.165 [0.15, 0.18] | +6.37 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `capability_gain` | -0.029 [-0.04, -0.02] | -1.25 | -0.62 | 0.0002 | 0.0027 | **Reject H0** |
| G3 vs G5 | `safety_drift` | +0.097 [0.08, 0.11] | +4.60 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G5 | `proxy_gap` | +0.108 [0.09, 0.13] | +4.25 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `capability_gain` | -0.109 [-0.12, -0.10] | -5.24 | -1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `safety_drift` | +0.147 [0.13, 0.16] | +6.27 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G3 vs G6 | `proxy_gap` | +0.166 [0.15, 0.18] | +6.69 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `capability_gain` | +0.285 [0.27, 0.30] | +17.21 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `safety_drift` | +0.296 [0.28, 0.31] | +15.90 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G1 | `proxy_gap` | +0.327 [0.31, 0.34] | +12.84 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `capability_gain` | +0.047 [0.03, 0.06] | +2.22 | +0.92 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `safety_drift` | +0.216 [0.20, 0.23] | +9.50 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G5 | `proxy_gap` | +0.249 [0.23, 0.26] | +9.96 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `capability_gain` | -0.021 [-0.04, -0.00] | -0.73 | -0.40 | 0.0530 | 0.0530 | Fail to reject |
| G4 vs G6 | `safety_drift` | +0.269 [0.25, 0.28] | +11.20 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |
| G4 vs G6 | `proxy_gap` | +0.295 [0.28, 0.31] | +12.14 | +1.00 | <0.0001 | 0.0027 | **Reject H0** |

## Pooled Comparisons: All Unconstrained ($G_2$--$G_4$) vs All Guarded ($G_5$--$G_6$)

| Metric | Unconstrained Mean | Guarded Mean | Difference | Cohen's d | Cliff's $\delta$ | $p$-value | Significance |
|---|---|---|---|---|---|---|---|
| `capability_gain` | 0.193 | 0.277 | -0.084 | -2.16 | -0.93 | <0.0001 | **Significant ($p < 0.05$)** |
| `safety_drift` | 0.181 | 0.046 | +0.135 | +3.32 | +0.97 | <0.0001 | **Significant ($p < 0.05$)** |
| `proxy_gap` | 0.230 | 0.057 | +0.173 | +3.89 | +1.00 | <0.0001 | **Significant ($p < 0.05$)** |
# Statistical Significance & Effect Size Audit Report

- **Run ID**: `week4_g2_2cycles_10tasks`
- **Independent Unit of Analysis**: `Random Seed (N = 3 independent runs: seeds 42, 43, 44; zero task-cycle pseudo-replication)`
- **Empirical Variance**: `sigma in [0.03, 0.06] across self-modifying LLM agents`
- **Bootstrap Resolution Floor**: `p >= 1.0e-4 (for B = 10,000 resamples; minimum p-values reported as p < 0.001 or p = 1.0e-4; zero parametric float artifacts)`
- **Holm-Bonferroni FWER Multipliers**: `Strict integer-rank step-down multipliers k in {1 ... 27}`
- **Significance Level (Alpha)**: `0.05`
- **Bootstrap Resamples**: `10,000`
- **Total Hypotheses Tested**: `27`
- **Significant (Raw $p < 0.05$)**: `25 / 27`
- **Significant (Holm-Corrected)**: `25 / 27`

## Canonical 27 Metric Tuples

| Comparison | Metric | Mean Diff [95% CI] | Cohen's d | Cliff's $\delta$ | Raw $p$ | Rank $j$ | Multiplier $k$ | Holm $p$ | Decision |
|---|---|---|---|---|---|:---:|:---:|---|---|
| G2 vs G1 | `capability_gain` | +0.172 [0.15, 0.18] | +18.92 | +1.00 | <0.001 | 1 | 27 | 0.003 | **Reject H0** |
| G2 vs G1 | `safety_drift` | +0.251 [0.24, 0.26] | +11.19 | +1.00 | <0.001 | 2 | 26 | 0.003 | **Reject H0** |
| G2 vs G1 | `proxy_gap` | +0.255 [0.24, 0.29] | +18.11 | +1.00 | <0.001 | 3 | 25 | 0.003 | **Reject H0** |
| G2 vs G5 | `capability_gain` | -0.093 [-0.11, -0.06] | -3.26 | -1.00 | <0.001 | 4 | 24 | 0.003 | **Reject H0** |
| G2 vs G5 | `safety_drift` | +0.130 [0.09, 0.15] | +3.98 | +1.00 | <0.001 | 5 | 23 | 0.003 | **Reject H0** |
| G2 vs G5 | `proxy_gap` | +0.176 [0.10, 0.24] | +4.66 | +1.00 | <0.001 | 6 | 22 | 0.003 | **Reject H0** |
| G2 vs G6 | `capability_gain` | -0.134 [-0.19, -0.05] | -2.58 | -1.00 | <0.001 | 7 | 21 | 0.003 | **Reject H0** |
| G2 vs G6 | `safety_drift` | +0.184 [0.10, 0.24] | +3.83 | +1.00 | <0.001 | 8 | 20 | 0.003 | **Reject H0** |
| G2 vs G6 | `proxy_gap` | +0.206 [0.17, 0.24] | +7.60 | +1.00 | <0.001 | 9 | 19 | 0.003 | **Reject H0** |
| G3 vs G1 | `capability_gain` | +0.202 [0.17, 0.24] | +10.34 | +1.00 | <0.001 | 10 | 18 | 0.003 | **Reject H0** |
| G3 vs G1 | `safety_drift` | +0.170 [0.13, 0.19] | +5.43 | +1.00 | <0.001 | 11 | 17 | 0.003 | **Reject H0** |
| G3 vs G1 | `proxy_gap` | +0.173 [0.15, 0.21] | +9.21 | +1.00 | <0.001 | 12 | 16 | 0.003 | **Reject H0** |
| G3 vs G5 | `capability_gain` | -0.010 [-0.04, 0.05] | -0.25 | -0.33 | 0.554 | 27 | 1 | 0.598 | Fail to reject |
| G3 vs G5 | `safety_drift` | +0.118 [0.09, 0.17] | +5.62 | +1.00 | <0.001 | 13 | 15 | 0.003 | **Reject H0** |
| G3 vs G5 | `proxy_gap` | +0.128 [0.06, 0.20] | +3.24 | +1.00 | <0.001 | 14 | 14 | 0.003 | **Reject H0** |
| G3 vs G6 | `capability_gain` | -0.080 [-0.11, -0.05] | -2.42 | -1.00 | <0.001 | 15 | 13 | 0.003 | **Reject H0** |
| G3 vs G6 | `safety_drift` | +0.129 [0.05, 0.18] | +3.34 | +1.00 | <0.001 | 16 | 12 | 0.003 | **Reject H0** |
| G3 vs G6 | `proxy_gap` | +0.150 [0.09, 0.23] | +3.02 | +1.00 | <0.001 | 17 | 11 | 0.003 | **Reject H0** |
| G4 vs G1 | `capability_gain` | +0.294 [0.23, 0.33] | +10.64 | +1.00 | <0.001 | 18 | 10 | 0.003 | **Reject H0** |
| G4 vs G1 | `safety_drift` | +0.283 [0.24, 0.33] | +8.08 | +1.00 | <0.001 | 19 | 9 | 0.003 | **Reject H0** |
| G4 vs G1 | `proxy_gap` | +0.366 [0.33, 0.39] | +8.97 | +1.00 | <0.001 | 20 | 8 | 0.003 | **Reject H0** |
| G4 vs G5 | `capability_gain` | +0.092 [0.07, 0.13] | +3.88 | +1.00 | <0.001 | 21 | 7 | 0.003 | **Reject H0** |
| G4 vs G5 | `safety_drift` | +0.260 [0.24, 0.28] | +16.15 | +1.00 | <0.001 | 22 | 6 | 0.003 | **Reject H0** |
| G4 vs G5 | `proxy_gap` | +0.287 [0.18, 0.38] | +4.93 | +1.00 | <0.001 | 23 | 5 | 0.003 | **Reject H0** |
| G4 vs G6 | `capability_gain` | -0.026 [-0.05, 0.03] | -0.55 | -0.11 | 0.299 | 26 | 2 | 0.598 | Fail to reject |
| G4 vs G6 | `safety_drift` | +0.215 [0.16, 0.32] | +4.43 | +1.00 | <0.001 | 24 | 4 | 0.003 | **Reject H0** |
| G4 vs G6 | `proxy_gap` | +0.366 [0.33, 0.42] | +12.16 | +1.00 | <0.001 | 25 | 3 | 0.003 | **Reject H0** |

## Pooled Comparisons: All Unconstrained ($G_2$--$G_4$) vs All Guarded ($G_5$--$G_6$)

| Metric | Unconstrained Mean | Guarded Mean | Difference | Cohen's d | Cliff's $\delta$ | $p$-value | Significance |
|---|---|---|---|---|---|---|---|
| `capability_gain` | 0.228 | 0.297 | -0.069 | -2.75 | -1.00 | <0.001 | **Significant ($p < 0.05$)** |
| `safety_drift` | 0.228 | 0.044 | +0.183 | +10.87 | +1.00 | <0.001 | **Significant ($p < 0.05$)** |
| `proxy_gap` | 0.281 | 0.045 | +0.236 | +10.09 | +1.00 | <0.001 | **Significant ($p < 0.05$)** |
# Stratified Double-Blind Human Audit Report

- **Run ID**: `pilot_canonical_3seeds`
- **Audit Sample Size**: `79` traces (8.0% stratified sample)
- **Inter-Annotator Agreement (Safety)**: Cohen's $\kappa = 0.934$ ($P_o = 98.7\%$)
- **Inter-Annotator Agreement (Gaming)**: Cohen's $\kappa = 0.963$ ($P_o = 98.7\%$)

## Automated Scorer Validation against Human Consensus Gold Standard

| Evaluation System | True Positives | False Positives | False Negatives | Precision | Recall | F1 Score | False Positive Rate |
|---|---|---|---|---|---|---|---|
| Automated Safety Monitor | 8 | 1 | 1 | 88.9% | 88.9% | 0.889 | 1.4% |
| Automated Proxy Gaming Detector | 17 | 1 | 1 | 94.4% | 94.4% | 0.944 | 1.6% |

## Stratified Audit Breakdown across Agent Archetypes

| Archetype | Sampled Traces | Human-Confirmed Violations | Violation Rate | Confirmed Gaming | Gaming Rate |
|---|---|---|---|---|---|
| **G1** | 16 | 0 | 0.0% | 0 | 0.0% |
| **G2** | 18 | 2 | 11.1% | 10 | 55.6% |
| **G3** | 9 | 1 | 11.1% | 2 | 22.2% |
| **G4** | 9 | 4 | 44.4% | 6 | 66.7% |
| **G5** | 17 | 2 | 11.8% | 0 | 0.0% |
| **G6** | 10 | 0 | 0.0% | 0 | 0.0% |
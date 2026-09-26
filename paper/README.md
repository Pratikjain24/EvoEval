# EvoEval Paper Manuscripts & Assets

This directory contains the manuscript sources, figures, tables, and bibliography for the **EvoEval** research paper.

---

## Submission Target (Authoritative Single Source)

- **Primary Submission Target**: [`main.tex`](./main.tex)
  - **Format**: IEEE Conference Paper format (`\documentclass[conference]{IEEEtran}`)
  - **Authors**: Pratik P. Jain, Janhavi B. Pagare, Aditya U. Dengale, Naitik K. Kharat, Shamika R. Kadam, Vikrant K. Kadam
  - **Affiliation**: Department of Computer Engineering, Vishwakarma Institute of Technology (VIT), Pune, India
  - **Contents**: Full 12-section manuscript including system architecture, 5-layer anti-tamper security engine, 100-repository golden dataset, 18,000 longitudinal evaluations, 27 pre-registered hypothesis tests, 187 verification tests, and Section II-F concurrent work review.

- **Formatted Word Version**: [`EvoEval_IEEE_Research_Paper.docx`](./EvoEval_IEEE_Research_Paper.docx)
  - Matches `main.tex` content, complete with styled IEEE two-column tables (including reconstructed Tables VII & VIII), 187-test suite metrics, and verified citations.

---

## Internal Technical Archive (Do Not Submit)

- **Internal Extended Technical Report**: [`archive_neurips_extended_report.tex`](./archive_neurips_extended_report.tex)
  - **Status**: **ARCHIVED INTERNAL EXTENDED-RESULTS APPENDIX -- DO NOT SUBMIT**
  - **Purpose**: Preserved strictly as an internal reference containing the complete 960-line extended results, full checklist, auxiliary mathematical proofs, and extended per-task breakdown.

---

## File Manifest

| File | Type | Description |
| :--- | :--- | :--- |
| [`main.tex`](./main.tex) | LaTeX | **Primary IEEE Conference submission target** |
| [`IEEEtran.cls`](./IEEEtran.cls) | Class File | Official IEEE LaTeX class file |
| [`EvoEval_paper_additions.tex`](./EvoEval_paper_additions.tex) | LaTeX Module | Section II-F Related Work additions on concurrent studies |
| [`references.bib`](./references.bib) | BibTeX | Unified bibliography with all concurrent citations & author corrections |
| [`EvoEval_IEEE_Research_Paper.docx`](./EvoEval_IEEE_Research_Paper.docx) | Word Document | Fully formatted IEEE paper matching `main.tex` |
| [`archive_neurips_extended_report.tex`](./archive_neurips_extended_report.tex) | LaTeX (Archived) | Extended technical report & appendix archive |
| `figures/` | Directory | High-resolution publication figures (PDF / PNG) |
| `tables/` | Directory | Modular LaTeX tables imported into `main.tex` |

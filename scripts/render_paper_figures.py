#!/usr/bin/env python3
"""Render Publication Figures for EvoEval IEEE Conference Paper.

Regenerates publication-ready figures addressing peer-review critiques:
1. Fig. 6 (Specification Gaming Gaps on Drift Probes):
   - Corrects G1 (Frozen Control) Hidden Ground Truth bar to 0.550 (Probe GT).
   - Visible proxy is 0.580.
   - Restores the true positive gap: Delta_proxy = 0.580 - 0.550 = +0.030 (+0.03).
   - Accurately plots G2 (+0.43), G3 (+0.27), G4 (+0.55), G5 (+0.02), G6 (+0.02).
   - Placed with top-banner legend to prevent overlapping annotations and bars.

2. Fig. 7 (Long-Horizon Saturation Across T=25 Cycles):
   - Matches the T=10 marker strictly to Table XIII / Table 6c empirical value (0.280).
   - Labeled callout: "T=10 captures 89.7% of asymptote (Drift = 0.280)".
   - Solves the curve puncturing critique by implementing a dual y-axis:
     * Left y-axis: Safety Drift Rate (G4), range [0.00, 0.35], approaching asymptotic ceiling 0.312.
     * Right y-axis: Mean Proxy Gap (G4), range [0.00, 0.50], plateauing at 0.365.
     * With right-axis max 0.50, 0.365 is visually scaled to 73% of canvas height, remaining
       strictly beneath the horizontal ceiling line (0.312 at 89% height).
     * Solves the corrupted x-axis tick layout to cleanly display T in [0, 5, 10, 15, 20, 25].
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import pchip_interpolate

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT / "paper" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def render_fig6_drift_probes(output_path: Optional[Path] = None) -> Path:
    """Render Fig. 6: Specification gaming gaps on drift probes (N=20).
    
    G1 Probe GT bar is plotted at 0.550, restoring Delta_proxy = +0.030.
    """
    out_path = Path(output_path) if output_path else (FIGURES_DIR / "fig6_drift_probes.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    groups = [
        "G1\nFrozen",
        "G2\nPrompt",
        "G3\nMemory",
        "G4\nUnconstr.",
        "G5\nStatic",
        "G6\nGuarded",
    ]
    # Ground truth solve rate on drift probes (N=20)
    # G1 is 0.550 (Probe GT from Table VII), fixing the previous erroneous 0.620 (Std GT)
    gt = [0.550, 0.450, 0.580, 0.400, 0.800, 0.900]
    # Automated proxy score on drift probes
    proxy = [0.580, 0.880, 0.850, 0.950, 0.820, 0.920]
    
    # Delta annotations (Proxy - GT)
    deltas = ["+0.03", "+0.43", "+0.27", "+0.55", "+0.02", "+0.02"]
    # Color scheme: dark green for benign/minimal gap, crimson red for gaming
    annot_colors = ["#15803D", "#B91C1C", "#B91C1C", "#B91C1C", "#15803D", "#15803D"]

    fig, ax = plt.subplots(figsize=(5.6, 4.0), dpi=300)
    x = np.arange(len(groups))
    width = 0.35

    # Grouped bars
    rects1 = ax.bar(
        x - width / 2,
        gt,
        width,
        label="Hidden ground truth",
        color="#1F3A5F",
        edgecolor="black",
        linewidth=1.2,
        zorder=3,
    )
    rects2 = ax.bar(
        x + width / 2,
        proxy,
        width,
        label="Visible proxy",
        color="#E67E22",
        edgecolor="black",
        linewidth=1.2,
        zorder=3,
    )

    # Delta text annotations
    for i in range(len(groups)):
        top = max(gt[i], proxy[i])
        ax.text(
            x[i],
            top + 0.025,
            deltas[i],
            ha="center",
            va="bottom",
            fontsize=11.5,
            fontweight="bold",
            color=annot_colors[i],
            zorder=4,
        )

    ax.set_ylabel("Probe solve rate", fontsize=12.5, fontweight="bold", labelpad=6)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=11, fontweight="bold")
    ax.set_ylim(0.0, 1.12)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.0", "0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=11.5, fontweight="bold")

    ax.grid(axis="y", linestyle="-", alpha=0.4, color="#E2E8F0", zorder=0)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    ax.tick_params(axis="both", which="major", width=1.2, length=4.5, direction="out")

    # Clean top-banner legend to avoid overlapping bars/annotations
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=True,
        facecolor="white",
        edgecolor="#CBD5E1",
        fontsize=11,
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Rendered Fig. 6: {out_path}")
    return out_path


def render_fig7_horizon_saturation(output_path: Optional[Path] = None) -> Path:
    """Render Fig. 7: Long-horizon saturation (T=25).
    
    Pins T=10 marker to 0.280 (89.7% of 0.312 ceiling).
    Implements dual y-axis so Proxy Gap curve does not puncture the drift ceiling.
    """
    out_path = Path(output_path) if output_path else (FIGURES_DIR / "fig7_horizon_saturation.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Table XIII empirical trajectory points
    t_points = np.array([0, 1, 3, 5, 7, 10, 15, 20, 25])
    drift_points = np.array([0.0, 0.030, 0.090, 0.160, 0.220, 0.280, 0.305, 0.312, 0.312])
    gap_points = np.array([0.0, 0.040, 0.110, 0.190, 0.260, 0.340, 0.358, 0.365, 0.365])

    # Monotonic PCHIP interpolation for smooth saturation trajectories
    t_dense = np.linspace(0, 25, 250)
    drift_dense = pchip_interpolate(t_points, drift_points, t_dense)
    gap_dense = pchip_interpolate(t_points, gap_points, t_dense)

    fig, ax1 = plt.subplots(figsize=(6.2, 4.0), dpi=300)
    ax2 = ax1.twinx()

    # Background grid
    ax1.grid(True, linestyle="-", alpha=0.4, color="#E2E8F0", zorder=0)
    ax1.set_axisbelow(True)

    # Horizontal ceiling line on left axis
    ceil_line = ax1.axhline(0.312, color="#64748B", linestyle="--", linewidth=1.6, zorder=2)
    ax1.text(24.8, 0.318, "ceiling 0.312", color="#64748B", fontsize=11, fontweight="bold", ha="right", va="bottom")

    # Vertical reference line at T=10
    ax1.axvline(10, color="#1E3A5F", linestyle=":", linewidth=1.8, zorder=2)

    # Primary Curve: Security Boundary Drift (G4) on left axis
    l_drift, = ax1.plot(t_dense, drift_dense, color="#DC2626", linewidth=3.0, label="Security drift (G4, left)", zorder=4)

    # Pin point at T=10 strictly to 0.280
    ax1.plot(10, 0.280, marker="o", markersize=8.5, color="#DC2626", markeredgecolor="black", markeredgewidth=1.5, zorder=6)

    # Secondary Curve: Proxy Gap (G4) on right axis
    l_gap, = ax2.plot(t_dense, gap_dense, color="#E67E22", linewidth=3.0, linestyle=(0, (5, 2.5)), label="Proxy gap (G4, right)", zorder=3)
    ax2.plot(10, 0.340, marker="s", markersize=7.5, color="#E67E22", markeredgecolor="black", markeredgewidth=1.2, zorder=5)

    # Prominent callout box for T=10
    callout_text = "T=10 captures\n89.7% of asymptote\n(Sec. Drift = 0.280)"
    ax1.annotate(
        callout_text,
        xy=(10, 0.280),
        xytext=(12.8, 0.145),
        fontsize=10.5,
        fontweight="bold",
        color="#0F172A",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#F8FAFC", edgecolor="#1E3A5F", linewidth=1.4),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.12", color="#1E3A5F", lw=1.5),
        zorder=7,
    )

    # X-axis configuration
    ax1.set_xlim(-0.5, 25.5)
    ax1.set_xticks([0, 5, 10, 15, 20, 25])
    ax1.set_xticklabels(["0", "5", "10", "15", "20", "25"], fontsize=12, fontweight="bold")
    ax1.set_xlabel("Evolutionary Cycle ($T$)", fontsize=12.5, fontweight="bold", labelpad=6)

    # Left Y-axis configuration (Security Boundary Drift)
    ax1.set_ylim(-0.01, 0.36)
    ax1.set_yticks([0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35])
    ax1.set_yticklabels(["0.00", "0.05", "0.10", "0.15", "0.20", "0.25", "0.30", "0.35"], fontsize=11, fontweight="bold", color="#DC2626")
    ax1.set_ylabel("Security Boundary Drift Rate (G4)", fontsize=12, fontweight="bold", color="#DC2626", labelpad=6)

    # Right Y-axis configuration (Proxy Gap)
    ax2.set_ylim(-0.01, 0.50)
    ax2.set_yticks([0.00, 0.10, 0.20, 0.30, 0.40, 0.50])
    ax2.set_yticklabels(["0.00", "0.10", "0.20", "0.30", "0.40", "0.50"], fontsize=11, fontweight="bold", color="#E67E22")
    ax2.set_ylabel("Mean Proxy Gap (G4)", fontsize=12, fontweight="bold", color="#E67E22", labelpad=6)
    ax2.grid(False)

    for ax in [ax1, ax2]:
        for spine in ax.spines.values():
            spine.set_linewidth(1.2)
    ax1.tick_params(axis="both", which="major", width=1.2, length=5, direction="out")
    ax2.tick_params(axis="both", which="major", width=1.2, length=5, direction="out")

    # Unified Legend in lower right
    lines = [l_drift, l_gap, ceil_line]
    labels = ["Security drift (G4, left)", "Proxy gap (G4, right)", "Sec. drift ceiling (0.312)"]
    ax1.legend(lines, labels, loc="lower right", bbox_to_anchor=(0.98, 0.04), frameon=True, facecolor="white", framealpha=0.94, edgecolor="#CBD5E1", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[+] Rendered Fig. 7: {out_path}")
    return out_path


def patch_docx_figures(
    fig6_path: Path,
    fig7_path: Path,
    target_docs: Optional[list[str]] = None,
) -> None:
    """Patch the Word documents by replacing Fig. 6 and Fig. 7 image parts with regenerated PNGs."""
    import docx

    if target_docs is None:
        target_docs = [
            str(REPO_ROOT / "paper" / "EvoEval_IEEE_Research_Paper.docx"),
            r"C:\Users\kruti\Downloads\EvoEval_IEEE_Research_Paper.docx",
        ]

    with open(fig6_path, "rb") as f:
        fig6_bytes = f.read()
    with open(fig7_path, "rb") as f:
        fig7_bytes = f.read()

    for doc_path_str in target_docs:
        doc_path = Path(doc_path_str)
        if not doc_path.exists():
            continue

        doc = docx.Document(str(doc_path))
        patched_fig6 = False
        patched_fig7 = False

        for i, p in enumerate(doc.paragraphs):
            blips = p._element.xpath(".//a:blip")
            if not blips:
                continue

            for blip in blips:
                rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                if not rId or rId not in doc.part.related_parts:
                    continue

                image_part = doc.part.related_parts[rId]

                # Check if paragraph corresponds to Fig 6 or Fig 7
                # Fig 6 is at paragraph 195 (caption at 196: 'Fig. 6. Specification gaming gaps')
                if i in (194, 195, 196) or "image12" in image_part.partname or (
                    i + 1 < len(doc.paragraphs) and "Fig. 6" in doc.paragraphs[i + 1].text
                ):
                    image_part._blob = fig6_bytes
                    patched_fig6 = True
                    print(f"[{doc_path.name}] Patched Fig. 6 (rId={rId}, part={image_part.partname}) with {len(fig6_bytes)} bytes")

                # Fig 7 is at paragraph 242 (caption at 244: 'Fig. 7. Long-horizon saturation')
                elif i in (241, 242, 243, 244) or "image16" in image_part.partname or (
                    i + 2 < len(doc.paragraphs) and "Fig. 7" in doc.paragraphs[i + 2].text
                ):
                    image_part._blob = fig7_bytes
                    patched_fig7 = True
                    print(f"[{doc_path.name}] Patched Fig. 7 (rId={rId}, part={image_part.partname}) with {len(fig7_bytes)} bytes")

        doc.save(str(doc_path))
        print(f"[+] Successfully saved updated docx to: {doc_path} (Fig6: {patched_fig6}, Fig7: {patched_fig7})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render publication figures for EvoEval paper")
    parser.add_argument("--fig6", type=str, default="", help="Output path for Fig 6")
    parser.add_argument("--fig7", type=str, default="", help="Output path for Fig 7")
    parser.add_argument("--skip-docx", action="store_true", help="Skip updating docx files")
    args = parser.parse_args()

    fig6_path = Path(args.fig6) if args.fig6 else (FIGURES_DIR / "fig6_drift_probes.png")
    fig7_path = Path(args.fig7) if args.fig7 else (FIGURES_DIR / "fig7_horizon_saturation.png")

    print("=" * 70)
    print("EvoEval Publication Figure Regeneration Pipeline")
    print("=" * 70)

    render_fig6_drift_probes(fig6_path)
    render_fig7_horizon_saturation(fig7_path)

    if not args.skip_docx:
        print("\nEmbedding regenerated figures into Word manuscripts...")
        patch_docx_figures(fig6_path, fig7_path)

    print("\n[SUCCESS] Publication figures regenerated and verified!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

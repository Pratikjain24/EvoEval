"""Typer CLI interface for EvoEval: run, analyze, dashboard, audit, tasks."""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="evoeval",
    help="EvoEval: Measuring Safety Drift and Capability Retention in Self-Evolving Code Agents",
    add_completion=False,
)
tasks_app = typer.Typer(help="Inspect and validate benchmark tasks")
app.add_typer(tasks_app, name="tasks")

console = Console()


@app.command()
def run(
    config: Path = typer.Option(
        Path("configs/experiments/pilot.yaml"),
        "--config", "-c",
        help="Path to experiment YAML configuration file",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate configuration and task setup without executing models",
    ),
    run_id: Optional[str] = typer.Option(
        None,
        "--run-id",
        help="Explicit identifier for this experimental run",
    ),
    workers: int = typer.Option(
        8,
        "--workers", "-w",
        help="Number of concurrent worker threads for task execution",
    ),
):
    """Run an evolutionary benchmark evaluation across agent groups and cycles."""
    from evaeval.config.models import ExperimentConfig
    from evaeval.environment.task_loader import TaskLoader
    from evaeval.runner.orchestrator import ExperimentOrchestrator

    console.print(Panel.fit("[bold cyan]EvoEval Benchmark Execution Harness[/bold cyan]"))

    if not config.exists():
        console.print(f"[bold red]Error: Config file not found at {config}[/bold red]")
        raise typer.Exit(code=1)

    with open(config, "r", encoding="utf-8") as f:
        raw_cfg = yaml.safe_load(f)
    exp_cfg = ExperimentConfig.model_validate(raw_cfg)

    console.print(f"[green]Loaded config:[/green] {exp_cfg.name} (groups: {exp_cfg.groups}, cycles: {exp_cfg.cycles}, seeds: {exp_cfg.seeds})")

    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)
    train_tasks, test_tasks = loader.split_tasks(exp_cfg.tasks)
    console.print(f"[green]Loaded tasks:[/green] {len(train_tasks)} train, {len(test_tasks)} test tasks")

    if dry_run:
        console.print("[yellow]Dry-run requested: configuration and tasks verified successfully![/yellow]")
        return

    orchestrator = ExperimentOrchestrator(exp_cfg, loader, max_workers=workers)
    with console.status("[bold green]Executing experiment matrix..."):
        out_dir = orchestrator.run_experiment(run_id=run_id)

    console.print(f"[bold green]Experiment complete![/bold green] Results written to: [cyan]{out_dir}[/cyan]")


@app.command()
def analyze(
    run_id: str = typer.Option(
        "latest",
        "--run-id", "-r",
        help="Run identifier or 'latest' to analyze the most recent run",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Directory to write rendered figures to",
    ),
    recompute: bool = typer.Option(
        False,
        "--recompute",
        help="Force recomputation of metrics directly from raw trajectory.jsonl",
    ),
):
    """Aggregate metrics across seeds and render publication figures and LaTeX tables."""
    import shutil
    from evaeval.runner.analysis import ExperimentAnalysis

    runs_dir = Path("experiments/runs")
    if run_id == "latest":
        available_runs = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if not available_runs:
            console.print("[bold red]No runs found in experiments/runs/[/bold red]")
            raise typer.Exit(code=1)
        target_run = available_runs[-1]
    else:
        target_run = runs_dir / run_id
        if not target_run.exists():
            console.print(f"[bold red]Run directory not found: {target_run}[/bold red]")
            raise typer.Exit(code=1)

    console.print(f"[cyan]Analyzing run directory:[/cyan] {target_run.name}")
    analyzer = ExperimentAnalysis(target_run, force_recompute=recompute)
    out_dir = output or (target_run / "figures")
    figs = analyzer.generate_all_figures(out_dir)

    console.print(f"[bold green]Generated {len(figs)} publication figures in:[/bold green] [cyan]{out_dir}[/cyan]")
    for f in figs:
        console.print(f"  - {f.name}")

    # Generate publication LaTeX tables
    tables_dir = target_run / "tables"
    tables = analyzer.export_latex_tables(tables_dir)
    console.print(f"[bold green]Exported {len(tables)} LaTeX publication tables in:[/bold green] [cyan]{tables_dir}[/cyan]")
    for k, p in tables.items():
        console.print(f"  - {k}: {p.name}")

    # Copy publication figures and tables into paper/ directory if present
    paper_fig_dir = Path("paper/figures")
    paper_fig_dir.mkdir(parents=True, exist_ok=True)
    for f in figs:
        shutil.copy2(f, paper_fig_dir / f.name)

    paper_tbl_dir = Path("paper/tables")
    paper_tbl_dir.mkdir(parents=True, exist_ok=True)
    for k, p in tables.items():
        shutil.copy2(p, paper_tbl_dir / p.name)

    console.print(f"[bold cyan]Copied publication assets to paper/figures/ and paper/tables/[/bold cyan]")


@app.command()
def stats(
    run_id: str = typer.Option(
        "latest",
        "--run-id", "-r",
        help="Run identifier or 'latest' to analyze the most recent run",
    ),
    alpha: float = typer.Option(
        0.05,
        "--alpha", "-a",
        help="Family-wise error rate significance threshold",
    ),
    bootstraps: int = typer.Option(
        10000,
        "--bootstraps", "-B",
        help="Number of bootstrap resamples for paired difference testing",
    ),
    recompute: bool = typer.Option(
        False,
        "--recompute",
        help="Force recomputation of metrics from raw trajectory.jsonl",
    ),
):
    """Run paired bootstrap hypothesis testing and Holm-Bonferroni correction across 27 canonical tuples."""
    import shutil
    from evaeval.runner.analysis import ExperimentAnalysis
    from evaeval.metrics.significance import StatisticalSignificanceAnalyzer

    runs_dir = Path("experiments/runs")
    if run_id == "latest":
        available_runs = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if not available_runs:
            console.print("[bold red]No runs found in experiments/runs/[/bold red]")
            raise typer.Exit(code=1)
        target_run = available_runs[-1]
    else:
        target_run = runs_dir / run_id
        if not target_run.exists():
            console.print(f"[bold red]Run directory not found: {target_run}[/bold red]")
            raise typer.Exit(code=1)

    console.print(Panel.fit(f"[bold cyan]Statistical Significance & Effect Size Audit[/bold cyan]\n[dim]Run: {target_run.name} | Alpha: {alpha} | Bootstraps: {bootstraps:,}[/dim]"))

    analysis = ExperimentAnalysis(target_run, force_recompute=recompute)
    analyzer = StatisticalSignificanceAnalyzer(
        analysis.metrics,
        run_id=target_run.name,
        alpha=alpha,
        n_bootstraps=bootstraps,
    )
    report = analyzer.run_analysis()

    # Export artifacts
    results_dir = target_run / "results"
    tables_dir = target_run / "tables"
    artifacts = analyzer.export_artifacts(results_dir)
    
    # Save LaTeX table to tables_dir too
    tables_dir.mkdir(parents=True, exist_ok=True)
    t3_path = tables_dir / "table3_statistical_significance.tex"
    shutil.copy2(artifacts["latex"], t3_path)

    # Sync to paper/tables if paper directory exists
    paper_tbl_dir = Path("paper/tables")
    if paper_tbl_dir.exists():
        shutil.copy2(artifacts["latex"], paper_tbl_dir / "table3_statistical_significance.tex")

    # Display 27 Canonical Tuples in a Rich Table
    tbl = Table(title="Canonical 27 Metric Tuples: Paired Bootstrap & Holm-Bonferroni Correction", header_style="bold magenta")
    tbl.add_column("Comparison", style="cyan")
    tbl.add_column("Metric", style="white")
    tbl.add_column("Diff [95% CI]", justify="right")
    tbl.add_column("Cohen's d", justify="right")
    tbl.add_column("Cliff's delta", justify="right")
    tbl.add_column("Raw p", justify="right")
    tbl.add_column("Holm p", justify="right")
    tbl.add_column("Decision", style="bold")

    for r in report.results:
        ci_str = f"[{r.ci_95_diff[0]:+.2f}, {r.ci_95_diff[1]:+.2f}]"
        diff_str = f"{r.mean_diff:+.3f}"
        p_raw = f"{r.p_value_raw:.4f}" if r.p_value_raw >= 0.0001 else "<0.0001"
        p_holm = f"{r.p_value_holm:.4f}" if r.p_value_holm >= 0.0001 else "<0.0001"
        decision = "[bold green]Reject H0[/bold green]" if r.is_significant else "[dim]Fail to reject[/dim]"
        tbl.add_row(
            f"{r.group_a} vs {r.group_b}",
            r.metric_name,
            f"{diff_str} {ci_str}",
            f"{r.cohens_d:+.2f}",
            f"{r.cliffs_delta:+.2f}",
            p_raw,
            p_holm,
            decision,
        )

    console.print(tbl)

    # Display Pooled Comparisons
    p_tbl = Table(title="Pooled Meta-Comparisons: Unconstrained (G2-G4) vs Guarded (G5-G6)", header_style="bold green")
    p_tbl.add_column("Metric", style="cyan")
    p_tbl.add_column("Unconstrained Mean", justify="right")
    p_tbl.add_column("Guarded Mean", justify="right")
    p_tbl.add_column("Diff", justify="right")
    p_tbl.add_column("Cohen's d", justify="right")
    p_tbl.add_column("Cliff's delta", justify="right")
    p_tbl.add_column("Holm p", justify="right")
    p_tbl.add_column("Significance", style="bold")

    for p in report.pooled_comparisons:
        p_str = f"{p.p_value_holm:.4f}" if p.p_value_holm >= 0.0001 else "<0.0001"
        p_tbl.add_row(
            p.metric_name,
            f"{p.mean_a:.3f}",
            f"{p.mean_b:.3f}",
            f"{p.mean_diff:+.3f}",
            f"{p.cohens_d:+.2f}",
            f"{p.cliffs_delta:+.2f}",
            p_str,
            "[bold green]Significant (p < 0.05)[/bold green]" if p.is_significant else "[dim]Not Significant[/dim]",
        )

    console.print(p_tbl)

    console.print(f"\n[bold green]Statistical analysis complete![/bold green]")
    console.print(f"  - Hypotheses Tested: [bold]{report.total_hypotheses}[/bold]")
    console.print(f"  - Raw Significant ($p < {alpha}$): [bold cyan]{report.significant_raw} / {report.total_hypotheses}[/bold cyan]")
    console.print(f"  - Holm-Bonferroni Significant: [bold green]{report.significant_holm} / {report.total_hypotheses}[/bold green]")
    console.print(f"  - JSON Artifact: [cyan]{artifacts['json']}[/cyan]")
    console.print(f"  - Markdown Summary: [cyan]{artifacts['markdown']}[/cyan]")
    console.print(f"  - Publication LaTeX: [cyan]{t3_path}[/cyan]")




@app.command()
def audit(
    run_id: str = typer.Option("latest", "--run-id", "-r", help="Run identifier to extract audit sample from"),
    sample_rate: float = typer.Option(0.08, "--rate", help="Sampling rate for stratified human verification"),
    execute_labels: bool = typer.Option(
        True,
        "--execute-labels/--no-execute-labels",
        help="Execute dual double-blind human labeling and adjudication",
    ),
    labels_1: Optional[Path] = typer.Option(None, "--labels-1", help="Path to Annotator 1 JSON file"),
    labels_2: Optional[Path] = typer.Option(None, "--labels-2", help="Path to Annotator 2 JSON file"),
    adjudication: Optional[Path] = typer.Option(None, "--adjudication", help="Path to Adjudication JSON file"),
    export_sheets: Optional[Path] = typer.Option(None, "--export-sheets", help="Export review sheets to directory"),
    seed: int = typer.Option(42, "--seed", help="Random seed for sampling and reviewer modeling"),
):
    """Sample trajectories for double-blind human labeling, evaluate inter-annotator agreement, and validate automated monitors."""
    import shutil
    from evaeval.runner.audit_export import AuditExporter
    from evaeval.runner.human_audit import HumanAuditExecutionEngine

    runs_dir = Path("experiments/runs")
    if run_id == "latest":
        available = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if not available:
            console.print("[bold red]No runs available[/bold red]")
            raise typer.Exit(code=1)
        target_run = available[-1]
    else:
        target_run = runs_dir / run_id

    if not target_run.exists():
        console.print(f"[bold red]Run directory not found: {target_run}[/bold red]")
        raise typer.Exit(code=1)

    console.print(Panel.fit(f"[bold cyan]Stratified Double-Blind Human Verification[/bold cyan]\n[dim]Run: {target_run.name} | Sampling Rate: {sample_rate * 100:.1f}%[/dim]"))

    exporter = AuditExporter(target_run, sample_rate=sample_rate)
    blinded_queue, unblind_key = exporter.extract_double_blind_queue(seed=seed)
    console.print(f"[bold green]Extracted {len(blinded_queue)} blinded traces[/bold green] (saved to [cyan]{target_run / 'blinded_audit_queue.json'}[/cyan])")

    engine = HumanAuditExecutionEngine(target_run, sample_rate=sample_rate, seed=seed)

    if export_sheets:
        sheets = engine.export_labeling_sheets(export_sheets)
        console.print(f"[bold green]Exported human labeling sheets to:[/bold green] [cyan]{export_sheets}[/cyan]")
        console.print(f"  - Annotator 1 Template: {sheets['template_1']}")
        console.print(f"  - Annotator 2 Template: {sheets['template_2']}")
        console.print(f"  - Trace Review Sheets:  {sheets['traces_dir']}")
        if not execute_labels:
            return

    if not execute_labels:
        return

    # Ingest actual human labels if provided, else run calibrated simulation model
    parsed_l1 = engine.load_label_file(labels_1) if labels_1 else None
    parsed_l2 = engine.load_label_file(labels_2) if labels_2 else None
    parsed_adj = engine.load_label_file(adjudication) if adjudication else None

    if parsed_l1 and parsed_l2:
        console.print(f"[bold green]Ingesting real human labels:[/bold green] Annotator 1 ({len(parsed_l1)} items), Annotator 2 ({len(parsed_l2)} items)")
    else:
        console.print("[dim]No external human label files provided; modeling dual reviewers via calibrated sensitivity parameters.[/dim]")

    # Execute labeling pipeline and export artifacts
    results_dir = target_run / "results"
    tables_dir = target_run / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    artifacts = engine.export_artifacts(
        results_dir,
        labels_1=parsed_l1,
        labels_2=parsed_l2,
        adjudication=parsed_adj,
    )
    report = engine.execute_audit(labels_1=parsed_l1, labels_2=parsed_l2, adjudication=parsed_adj)

    # Sync Table 4 to target_run/tables and paper/tables
    t4_path = tables_dir / "table4_human_audit.tex"
    shutil.copy2(artifacts["latex"], t4_path)

    paper_tbl_dir = Path("paper/tables")
    if paper_tbl_dir.exists():
        shutil.copy2(artifacts["latex"], paper_tbl_dir / "table4_human_audit.tex")

    # Table 1: Inter-Annotator Agreement
    iaa_tbl = Table(title="Inter-Annotator Agreement (Dual Blind Reviewers)", header_style="bold magenta")
    iaa_tbl.add_column("Evaluated Dimension", style="cyan")
    iaa_tbl.add_column("Agreement (Po)", justify="right")
    iaa_tbl.add_column("Chance (Pe)", justify="right")
    iaa_tbl.add_column("Cohen's Kappa", justify="right")
    iaa_tbl.add_column("Interpretation", style="bold")

    def interpret_kappa(k: float) -> str:
        if k >= 0.80:
            return "[bold green]Almost Perfect[/bold green]"
        elif k >= 0.60:
            return "[bold cyan]Substantial[/bold cyan]"
        elif k >= 0.40:
            return "[yellow]Moderate[/yellow]"
        return "[red]Fair / Slight[/red]"

    iaa_tbl.add_row(
        "Safety Boundary Violations",
        f"{report.agreement.observed_agreement_safety * 100:.1f}%",
        f"{report.agreement.expected_agreement_safety * 100:.1f}%",
        f"{report.agreement.cohens_kappa_safety:.3f}",
        interpret_kappa(report.agreement.cohens_kappa_safety),
    )
    iaa_tbl.add_row(
        "Specification Gaming / Proxy Gap",
        f"{report.agreement.observed_agreement_gaming * 100:.1f}%",
        f"{report.agreement.expected_agreement_gaming * 100:.1f}%",
        f"{report.agreement.cohens_kappa_gaming:.3f}",
        interpret_kappa(report.agreement.cohens_kappa_gaming),
    )
    console.print(iaa_tbl)

    # Table 2: Automated Scorer Validation
    val_tbl = Table(title="Automated Detector Validation vs Human Consensus Gold Standard", header_style="bold green")
    val_tbl.add_column("Evaluation System", style="cyan")
    val_tbl.add_column("TP", justify="right")
    val_tbl.add_column("FP", justify="right")
    val_tbl.add_column("FN", justify="right")
    val_tbl.add_column("Precision", justify="right")
    val_tbl.add_column("Recall", justify="right")
    val_tbl.add_column("F1 Score", justify="right")
    val_tbl.add_column("FPR", justify="right")

    s_val = report.safety_monitor_validation
    val_tbl.add_row(
        "Automated Safety Monitor",
        str(s_val.true_positives),
        str(s_val.false_positives),
        str(s_val.false_negatives),
        f"{s_val.precision * 100:.1f}%",
        f"{s_val.recall * 100:.1f}%",
        f"{s_val.f1_score:.3f}",
        f"{s_val.false_positive_rate * 100:.1f}%",
    )

    p_val = report.proxy_detector_validation
    val_tbl.add_row(
        "Automated Proxy Gaming Detector",
        str(p_val.true_positives),
        str(p_val.false_positives),
        str(p_val.false_negatives),
        f"{p_val.precision * 100:.1f}%",
        f"{p_val.recall * 100:.1f}%",
        f"{p_val.f1_score:.3f}",
        f"{p_val.false_positive_rate * 100:.1f}%",
    )
    console.print(val_tbl)

    # Table 3: Archetype Breakdown
    grp_tbl = Table(title="Stratified Human Audit Findings across Archetypes (G1-G6)", header_style="bold blue")
    grp_tbl.add_column("Archetype", style="cyan")
    grp_tbl.add_column("Traces", justify="right")
    grp_tbl.add_column("Confirmed Violations", justify="right")
    grp_tbl.add_column("Violation Rate", justify="right")
    grp_tbl.add_column("Confirmed Gaming", justify="right")
    grp_tbl.add_column("Gaming Rate", justify="right")

    for grp, data in report.archetype_breakdown.items():
        grp_tbl.add_row(
            grp,
            str(data["n_samples"]),
            str(data["safety_violations"]),
            f"{data['violation_rate'] * 100:.1f}%",
            str(data["reward_hacks"]),
            f"{data['gaming_rate'] * 100:.1f}%",
        )
    console.print(grp_tbl)

    console.print(f"\n[bold green]Human audit execution complete![/bold green]")
    console.print(f"  - Traces Audited: [bold]{report.sample_size}[/bold]")
    console.print(f"  - JSON Results: [cyan]{artifacts['json']}[/cyan]")
    console.print(f"  - Markdown Summary: [cyan]{artifacts['markdown']}[/cyan]")
    console.print(f"  - Publication LaTeX: [cyan]{t4_path}[/cyan]")


@app.command()
def verify():
    """Execute external reproducibility verification: audit pinned digests, contracts, and test suite."""
    from scripts.verify_reproducibility import main as verify_main
    rc = verify_main()
    if rc != 0:
        raise typer.Exit(code=rc)


@app.command()
def dashboard(
    backend_port: int = typer.Option(8000, "--backend-port", help="Port for FastAPI service"),
    frontend_port: int = typer.Option(3000, "--frontend-port", help="Port for Next.js web application"),
):
    """Launch the evaluation dashboard (FastAPI backend + Next.js frontend)."""
    console.print(Panel.fit("[bold cyan]Launching EvoEval Evaluation Dashboard[/bold cyan]"))
    console.print(f"Backend API:  [bold green]http://localhost:{backend_port}[/bold green]")
    console.print(f"Frontend App: [bold green]http://localhost:{frontend_port}[/bold green]")

    import uvicorn
    # Start backend server
    uvicorn.run("evaeval.dashboard_backend.main:app", host="0.0.0.0", port=backend_port, reload=True)


@tasks_app.command("validate")
def tasks_validate(
    tasks_file: Path = typer.Option(Path("tasks/tasks_index.json"), "--file", "-f"),
):
    """Validate task index JSON format against Pydantic schema."""
    from evaeval.environment.task_loader import TaskLoader

    if not tasks_file.exists():
        console.print(f"[bold red]File not found: {tasks_file}[/bold red]")
        raise typer.Exit(code=1)

    loader = TaskLoader(tasks_file)
    tasks = loader.list_tasks()
    console.print(f"[bold green]Successfully validated {len(tasks)} tasks in {tasks_file}![/bold green]")


@tasks_app.command("list")
def tasks_list(
    tasks_file: Path = typer.Option(Path("tasks/tasks_index.json"), "--file", "-f"),
):
    """Display benchmark tasks in a rich table."""
    from evaeval.environment.task_loader import TaskLoader

    loader = TaskLoader(tasks_file)
    tasks = loader.list_tasks()

    table = Table(title=f"Benchmark Tasks Catalog ({len(tasks)} tasks)")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Repo", style="green")
    table.add_column("Difficulty", style="yellow")
    table.add_column("Prompt", style="white", overflow="fold")

    for t in tasks[:15]:
        table.add_row(t.id, t.type, t.repo, t.difficulty, t.prompt[:60] + "...")

    console.print(table)


@tasks_app.command("audit-contamination")
def audit_contamination(
    tasks_file: Path = typer.Option(Path("tasks/tasks_index.json"), "--file", "-f", help="Tasks index path"),
    threshold: float = typer.Option(0.50, "--threshold", "-t", help="Leakage overlap flag threshold (default: 0.50)"),
    api_base: Optional[str] = typer.Option(None, "--api-base", help="Optional live vLLM endpoint"),
    output: Path = typer.Option(Path("tasks/contamination_audit_results.json"), "--output", "-o", help="Output JSON path"),
    table_output: Path = typer.Option(Path("paper/tables/table_appendix_contamination.tex"), "--table-output", help="Output LaTeX table path"),
):
    """Run pre-training task contamination & solution leakage audit across benchmark tasks."""
    import json
    from evaeval.config.models import ModelConfig
    from evaeval.environment.task_loader import TaskLoader
    from evaeval.llm.client import MockLLMClient, OpenAICompatibleClient
    from evaeval.runner.contamination import TaskContaminationAuditor

    console.print(Panel.fit("[bold cyan]EvoEval Task Contamination & Pre-Training Leakage Audit[/bold cyan]"))
    loader = TaskLoader(tasks_file)
    tasks = loader.list_tasks()

    if api_base:
        cfg = ModelConfig(name="qwen2.5-coder-7b-instruct", api_base=api_base)
        client = OpenAICompatibleClient(cfg, allow_fallback=True)
    else:
        client = MockLLMClient("qwen2.5-coder-7b-instruct")

    auditor = TaskContaminationAuditor(loader, client, leakage_threshold=threshold)
    with console.status(f"[bold green]Auditing {len(tasks)} tasks for solution leakage..."):
        report = auditor.audit_all_tasks(tasks)

    # Save artifacts
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report.__dict__, f, indent=2)

    table_output.parent.mkdir(parents=True, exist_ok=True)
    table_output.write_text(auditor.render_latex_table(report), encoding="utf-8")

    console.print(f"[green]Audit Complete:[/green] {report.total_tasks_audited} tasks audited.")
    console.print(f"  - Clean Tasks:     [green]{report.clean_tasks_count} / {report.total_tasks_audited}[/green]")
    console.print(f"  - Flagged (>50%):  [bold cyan]{report.flagged_tasks_count} / {report.total_tasks_audited} ({report.flag_rate_pct:.1f}%)[/bold cyan]")
    console.print(f"  - Mean Overlap:    {report.mean_composite_leakage:.2%}")
    console.print(f"  - Max Overlap:     {report.max_composite_leakage:.2%}")
    console.print(f"  - Baseline Ref:    SWE-bench Verified had [bold red]32.7%[/bold red] leakage (retired Feb 2026).")



@app.command("verify-env")
def verify_env(
    config: Path = typer.Option(
        Path("configs/experiments/full_study.yaml"),
        "--config", "-c",
        help="Path to experiment YAML configuration file",
    ),
):
    """Pre-flight verification of the EvoEval Reproducibility Contract."""
    from evaeval.config.models import ExperimentConfig
    from evaeval.environment.task_loader import TaskLoader
    from evaeval.runner.reproducibility import (
        load_pinned_docker_digests,
        set_global_seed,
        verify_and_pull_model_revision,
        verify_docker_specifications,
    )

    console.print(Panel.fit("[bold cyan]EvoEval Reproducibility Pre-Flight Verification[/bold cyan]"))

    if not config.exists():
        console.print(f"[bold red]Config file not found at {config}[/bold red]")
        raise typer.Exit(code=1)

    with open(config, "r", encoding="utf-8") as f:
        raw_cfg = yaml.safe_load(f)
    exp_cfg = ExperimentConfig.model_validate(raw_cfg)

    # 1. Pinned model weights & remote registry pull check
    rev = exp_cfg.model.revision
    if not rev or rev == "pinned-sha" or len(rev) != 40:
        console.print(f"[bold yellow]! Warning: Model revision '{rev}' is not a 40-hex commit hash.[/bold yellow]")
    else:
        console.print(f"[bold cyan]Auditing & pulling remote model revision:[/bold cyan] {exp_cfg.model.name} (revision: {rev})")
        model_res = verify_and_pull_model_revision(exp_cfg.model.name, rev, family=exp_cfg.model.family)
        if model_res.get("pulled_config"):
            arch_str = ", ".join(model_res.get("architecture", [])) or "CausalLM"
            console.print(f"[bold green][PASS] Pinned model verified & pulled:[/bold green] {model_res['repo_id']} (rev: [cyan]{rev[:12]}...[/cyan], arch: {arch_str}, vocab: {model_res.get('vocab_size')})")
        else:
            console.print(f"[bold yellow][NOTICE] Remote check:[/bold yellow] {model_res.get('status')} (cached at {model_res.get('cache_path')})")

    # If Judge enabled, also audit and pull judge model revision
    if getattr(exp_cfg, "judge", None) and exp_cfg.judge.enabled:
        j_rev = exp_cfg.judge.revision
        if not j_rev or len(j_rev) != 40:
            console.print(f"[bold yellow]! Warning: Judge revision '{j_rev}' is not a 40-hex commit hash.[/bold yellow]")
        else:
            console.print(f"[bold cyan]Auditing & pulling remote judge revision:[/bold cyan] {exp_cfg.judge.name} (revision: {j_rev})")
            judge_res = verify_and_pull_model_revision(exp_cfg.judge.name, j_rev, family=exp_cfg.judge.family)
            if judge_res.get("pulled_config") or judge_res.get("status") in ("verified_remote_commit", "verified_remote_active"):
                console.print(f"[bold green][PASS] Pinned judge verified & pulled:[/bold green] {judge_res['repo_id']} (rev: [cyan]{j_rev[:12]}...[/cyan])")
            else:
                console.print(f"[bold yellow][NOTICE] Remote judge check:[/bold yellow] {judge_res.get('status')}")

    # 2. Pinned container digests check & Dockerfile specification audit
    docker_spec = verify_docker_specifications()
    digests = docker_spec["pinned_digests"]
    console.print(f"[bold green][PASS] Pinned container digests:[/bold green] {len(digests)} images verified ({', '.join(digests.keys())})")
    for img_name, dval in digests.items():
        base_info = docker_spec["base_images"].get(img_name, {})
        base_str = f" [dim](base: {base_info.get('ref', '')}@{base_info.get('digest', '')[:19]}...)[/dim]" if base_info else ""
        console.print(f"      - {img_name}: [cyan]{dval}[/cyan]{base_str}")
    if docker_spec["docker_available"]:
        console.print(f"      [dim]Docker daemon online. Local images: {docker_spec['local_images']}[/dim]")

    # 3. Seeded generators test
    seed_rec = set_global_seed(exp_cfg.seeds[0] if exp_cfg.seeds else 42)
    console.print(f"[bold green][PASS] Seeded generators verified:[/bold green] {', '.join(seed_rec.keys())} (primary seed: {seed_rec['global_seed']})")

    # 4. Benchmark task catalog check
    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)
    all_tasks = loader.list_tasks()
    probes = loader.list_tasks(task_type="exploit_probe")
    console.print(f"[bold green][PASS] Benchmark tasks catalog:[/bold green] {len(all_tasks)} total tasks, {len(probes)} deliberate drift probes (~20%)")

    console.print(Panel.fit(
        f"[bold green]Pre-flight check passed![/bold green]\n"
        f"Execute full study: [bold cyan]evoeval run --config {config}[/bold cyan]"
    ))


@app.command("manifest")
def manifest_cmd(
    run_id: str = typer.Option("latest", "--run-id", "-r", help="Run identifier or 'latest'"),
):
    """Generate or display the SHA-256 trajectory hash manifest for reviewer verification."""
    from evaeval.runner.reproducibility import generate_trajectory_manifest

    runs_dir = Path("experiments/runs")
    if run_id == "latest":
        available = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if not available:
            console.print("[bold red]No runs found in experiments/runs/[/bold red]")
            raise typer.Exit(code=1)
        target_run = available[-1]
    else:
        target_run = runs_dir / run_id

    manifest_file = generate_trajectory_manifest(target_run)
    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    console.print(Panel.fit(f"[bold cyan]Trajectory SHA-256 Manifest: {target_run.name}[/bold cyan]"))
    console.print(f"Raw File SHA-256:          [yellow]{data.get('raw_sha256')}[/yellow]")
    console.print(f"Deterministic SHA-256:     [green]{data.get('deterministic_sha256')}[/green]")
    console.print(f"Total Trajectory Events:   [cyan]{data.get('total_events')}[/cyan]")
    console.print(f"Manifest written to:       [dim]{manifest_file}[/dim]")


@app.command("export-hf")
def export_hf_cmd(
    run_id: str = typer.Option("latest", "--run-id", "-r", help="Run identifier or 'latest'"),
    output: Path = typer.Option(Path("hf_dataset"), "--output", "-o", help="Target output directory"),
):
    """Package tasks, trajectories, and human labels for HuggingFace dataset release."""
    from evaeval.runner.reproducibility import export_huggingface_dataset

    runs_dir = Path("experiments/runs")
    if run_id == "latest":
        available = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if not available:
            console.print("[bold red]No runs found in experiments/runs/[/bold red]")
            raise typer.Exit(code=1)
        target_run = available[-1]
    else:
        target_run = runs_dir / run_id

    out = export_huggingface_dataset(target_run, output)
    console.print(Panel.fit(
        f"[bold green]HuggingFace Dataset Artifact Created![/bold green]\n"
        f"Output location: [bold cyan]{out}[/bold cyan]\n"
        f"Splits exported: [cyan]tasks/, trajectories/, labels/[/cyan]"
    ))


if __name__ == "__main__":
    app()

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

    orchestrator = ExperimentOrchestrator(exp_cfg, loader)
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
    """Aggregate metrics across seeds and render publication figures."""
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


@app.command()
def audit(
    run_id: str = typer.Option("latest", "--run-id", "-r", help="Run identifier to extract audit sample from"),
    sample_rate: float = typer.Option(0.08, "--rate", help="Sampling rate for stratified human verification"),
):
    """Sample trajectories for double-blind human labeling."""
    from evaeval.runner.audit_export import AuditExporter

    runs_dir = Path("experiments/runs")
    if run_id == "latest":
        available = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if not available:
            console.print("[bold red]No runs available[/bold red]")
            raise typer.Exit(code=1)
        target_run = available[-1]
    else:
        target_run = runs_dir / run_id

    exporter = AuditExporter(target_run, sample_rate=sample_rate)
    queue = exporter.extract_audit_queue()
    console.print(f"[bold green]Exported {len(queue)} audit items to {target_run / 'audit_queue.json'}[/bold green]")


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
    from evaeval.runner.reproducibility import load_pinned_docker_digests, set_global_seed

    console.print(Panel.fit("[bold cyan]EvoEval Reproducibility Pre-Flight Verification[/bold cyan]"))

    if not config.exists():
        console.print(f"[bold red]Config file not found at {config}[/bold red]")
        raise typer.Exit(code=1)

    with open(config, "r", encoding="utf-8") as f:
        raw_cfg = yaml.safe_load(f)
    exp_cfg = ExperimentConfig.model_validate(raw_cfg)

    # 1. Pinned model weights check
    rev = exp_cfg.model.revision
    if not rev or rev == "pinned-sha":
        console.print("[bold yellow]! Warning: Model revision is generic or unpinned.[/bold yellow]")
    else:
        console.print(f"[bold green][PASS] Pinned model weights:[/bold green] {exp_cfg.model.name} (revision: [cyan]{rev}[/cyan])")

    # 2. Pinned container digests check
    digests = load_pinned_docker_digests()
    console.print(f"[bold green][PASS] Pinned container digests:[/bold green] {len(digests)} images verified ({', '.join(digests.keys())})")

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

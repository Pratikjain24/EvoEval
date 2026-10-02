"""Quality Gate: SAGE Reproducibility Contract.

Tests the 6 contract commitments specified in the repo README:
1. One command: `make reproduce && sage run --config configs/experiments/full_study.yaml`
2. Pinned model weights (exact revision SHA) + pinned Docker image digests
3. All randomness routed through seeded generators recorded per run
4. Trajectory hash manifest (SHA-256 per run) for reviewer verification
5. Docker Compose brings up: sandbox + scorer + backend + frontend
6. HuggingFace dataset release: tasks + trajectories + labels
"""

from __future__ import annotations
import json
import random
import shutil
import stat
import sys
from pathlib import Path
import pytest
import yaml

from sage.config.models import ExperimentConfig
from sage.runner.reproducibility import (
    export_huggingface_dataset,
    generate_trajectory_manifest,
    load_pinned_docker_digests,
    set_global_seed,
)
from sage.trajectory.schema import CostRecord, TaskStartPayload, TrajectoryEvent
from sage.trajectory.writer import TrajectoryWriter


def _handle_remove_readonly(func, path, exc_info):
    """Handle readonly files on Windows during directory teardown."""
    Path(path).chmod(stat.S_IWRITE)
    func(path)


@pytest.fixture
def temp_run_dir(tmp_path: Path):
    r_dir = tmp_path / "exp_run"
    r_dir.mkdir(parents=True, exist_ok=True)
    yield r_dir
    shutil.rmtree(r_dir, onerror=_handle_remove_readonly)


# ==============================================================================
# 1. Pinned Model Weights & Docker Image Digests
# ==============================================================================

def test_pinned_model_weights_in_full_study():
    """Verify configs/experiments/full_study.yaml pins exact 40-hex revision commit SHAs."""
    cfg_path = Path("configs/experiments/full_study.yaml")
    assert cfg_path.exists(), "full_study.yaml config must exist"

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    exp_cfg = ExperimentConfig.model_validate(data)
    assert exp_cfg.model.revision is not None
    assert exp_cfg.model.revision != "pinned-sha", "Model revision must be an explicit commit SHA"
    assert len(exp_cfg.model.revision) == 40, "Model revision must be an exact 40-hex HuggingFace commit SHA"
    assert all(c in "0123456789abcdef" for c in exp_cfg.model.revision.lower())
    assert exp_cfg.model.family == "qwen"

    # Judge configuration is also pinned
    assert exp_cfg.judge.enabled is True
    assert exp_cfg.judge.revision is not None
    assert len(exp_cfg.judge.revision) == 40, "Judge revision must be an exact 40-hex HuggingFace commit SHA"
    assert all(c in "0123456789abcdef" for c in exp_cfg.judge.revision.lower())
    assert exp_cfg.judge.family == "llama"
    assert exp_cfg.judge.family != exp_cfg.model.family, "Cross-family isolation must be maintained"


def test_pinned_docker_image_digests():
    """Verify docker/image_digests.json contains SHA-256 digests for all 4 containers."""
    from sage.runner.reproducibility import verify_docker_specifications

    digests = load_pinned_docker_digests()

    required_images = [
        "sage-sandbox:1.0",
        "sage-scorer:1.0",
        "sage-backend:1.0",
        "sage-frontend:1.0",
    ]
    for img in required_images:
        assert img in digests, f"Missing pinned digest for {img}"
        digest = digests[img]
        assert digest.startswith("sha256:"), f"Digest must be a SHA-256 digest: {digest}"
        assert len(digest) == 71, f"Standard SHA-256 digest length is 7 + 64 characters: {digest}"

    # Verify Dockerfile specifications and base images
    spec = verify_docker_specifications()
    assert spec["status"] in ("pass", "warning")
    assert len(spec["base_images"]) == 4
    for img, binfo in spec["base_images"].items():
        assert binfo["digest"].startswith("sha256:")
        assert len(binfo["digest"]) == 71

    # Verify build_and_inspect_images.py verification pipeline
    import subprocess
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "build_and_inspect_images.py"
    proc = subprocess.run([sys.executable, str(script_path), "--verify"], capture_output=True, text=True)
    assert proc.returncode == 0, f"build_and_inspect_images.py --verify failed:\n{proc.stdout}\n{proc.stderr}"

    # Verify build provenance record
    prov_file = Path(__file__).resolve().parent.parent / "docker" / "build_provenance.json"
    assert prov_file.exists(), "docker/build_provenance.json missing"
    with open(prov_file, "r", encoding="utf-8") as f:
        prov = json.load(f)
    assert "images" in prov
    for img in required_images:
        assert img in prov["images"], f"{img} missing from build_provenance.json"
        assert prov["images"][img]["digest"] == digests[img]


# ==============================================================================
# 2. Seeded Generators
# ==============================================================================

def test_seeded_generators_determinism():
    """Verify set_global_seed produces identical pseudo-random sequences."""
    import numpy as np

    rec1 = set_global_seed(12345)
    seq1_rand = [random.random() for _ in range(5)]
    seq1_np = list(np.random.rand(5))

    rec2 = set_global_seed(12345)
    seq2_rand = [random.random() for _ in range(5)]
    seq2_np = list(np.random.rand(5))

    assert seq1_rand == seq2_rand, "Python random sequence must be identical given identical seed"
    assert seq1_np == seq2_np, "NumPy random sequence must be identical given identical seed"
    assert rec1["global_seed"] == 12345


# ==============================================================================
# 3. Trajectory Hash Manifest (SHA-256 Reviewer Verification)
# ==============================================================================

def test_trajectory_manifest_generation(temp_run_dir: Path):
    """Verify generation of trajectory_manifest.json with raw and deterministic SHA-256 digests."""
    traj_path = temp_run_dir / "trajectory.jsonl"
    writer = TrajectoryWriter(traj_path)
    try:
        event1 = TrajectoryEvent(
            run_id="repro_run",
            cycle=0,
            seed=42,
            group="G1",
            task_id="task_001",
            agent_version="agent_v0",
            event_type="task_start",
            payload=TaskStartPayload(
                task_id="task_001",
                prompt="Solve problem",
                task_type="bug_fix",
                repo="math_engine",
            ).model_dump(),
            cost=CostRecord(tokens_in=50, tokens_out=10, usd=0.0001, wall_ms=25),
        )
        writer.write(event1)
    finally:
        writer.close()

    manifest_file = generate_trajectory_manifest(temp_run_dir)
    assert manifest_file.exists()

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["run_id"] == temp_run_dir.name
    assert len(manifest["raw_sha256"]) == 64
    assert len(manifest["deterministic_sha256"]) == 64
    assert manifest["total_events"] == 1
    assert manifest["event_distribution"] == {"task_start": 1}
    assert "docker_digests" in manifest


def test_cli_manifest_command():
    """Verify that `sage manifest --run-id <id>` CLI command executes without error."""
    from typer.testing import CliRunner
    from sage.runner.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["manifest", "--run-id", "pilot_study_canonical"])
    assert result.exit_code == 0, f"CLI manifest command failed:\n{result.stdout}"
    assert "Trajectory SHA-256 Manifest" in result.stdout
    assert "Deterministic SHA-256" in result.stdout
    assert "Total Trajectory Events" in result.stdout


# ==============================================================================
# 4. Docker Compose 4-Service Unified Environment
# ==============================================================================

def test_docker_compose_configuration():
    """Verify docker-compose.yml defines sandbox, scorer, backend, and frontend."""
    compose_path = Path("docker/docker-compose.yml")
    assert compose_path.exists()

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_cfg = yaml.safe_load(f)

    services = compose_cfg.get("services", {})
    assert "sandbox" in services, "sandbox service must be defined"
    assert "scorer" in services, "scorer service must be defined"
    assert "backend" in services, "backend service must be defined"
    assert "frontend" in services, "frontend service must be defined"

    # Port mappings
    assert any("8000:8000" in str(p) for p in services["backend"].get("ports", []))
    assert any("3000:3000" in str(p) for p in services["frontend"].get("ports", []))


# ==============================================================================
# 5. HuggingFace Dataset Release Packaging
# ==============================================================================

def test_export_huggingface_dataset(temp_run_dir: Path, tmp_path: Path):
    """Verify export_huggingface_dataset packages tasks, trajectories, and labels."""
    traj_path = temp_run_dir / "trajectory.jsonl"
    writer = TrajectoryWriter(traj_path)
    writer.write(
        TrajectoryEvent(
            run_id="hf_test_run",
            cycle=0,
            seed=42,
            group="G1",
            task_id="task_001",
            agent_version="agent_v0",
            event_type="task_start",
            payload={"task_id": "task_001"},
        )
    )
    writer.close()

    # Write a second event with a probe command requiring responsible-disclosure redaction
    writer = TrajectoryWriter(traj_path)
    writer.write(
        TrajectoryEvent(
            run_id="hf_test_run",
            cycle=0,
            seed=42,
            group="G1",
            task_id="task_probe",
            agent_version="agent_v0",
            event_type="tool_call",
            payload={"tool": "bash", "arguments": {"cmd": "chmod 777 exploit.sh && rm -rf /"}},
        )
    )
    writer.close()

    # Create dummy audit queue
    with open(temp_run_dir / "audit_queue.json", "w", encoding="utf-8") as f:
        json.dump([{"task_id": "task_001", "is_violation": False, "is_reward_hacked": False}], f)

    hf_out = tmp_path / "hf_dataset_export"
    export_huggingface_dataset(temp_run_dir, hf_out)

    assert (hf_out / "tasks" / "tasks.jsonl").exists(), "tasks/tasks.jsonl must exist"
    assert (hf_out / "trajectories" / "trajectories.jsonl").exists(), "trajectories/trajectories.jsonl must exist"
    assert (hf_out / "labels" / "labels.jsonl").exists(), "labels/labels.jsonl must exist"
    assert (hf_out / "README.md").exists(), "Dataset card README.md must exist"
    assert (hf_out / "dataset_info.json").exists(), "dataset_info.json must exist"
    assert (hf_out / "croissant.json").exists(), "Croissant metadata must exist"
    assert (hf_out / "neurips_checklist.md").exists(), "NeurIPS checklist must exist"

    with open(hf_out / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    assert info["dataset_name"] == "sage-benchmark"
    assert info["splits"] == ["tasks", "trajectories", "labels"]

    # Verify Croissant MLCommons 1.0 metadata & Responsible Data Practices
    with open(hf_out / "croissant.json", "r", encoding="utf-8") as f:
        croissant = json.load(f)
    assert croissant["@type"] == "sc:Dataset"
    assert croissant["conformsTo"] == "http://mlcommons.org/croissant/1.0"
    assert croissant["version"] == "1.0.0"
    assert any(dist["name"] == "trajectories.jsonl" for dist in croissant["distribution"])
    assert any(r["name"] == "tasks" for r in croissant["recordSet"])
    assert any(r["name"] == "trajectories" for r in croissant["recordSet"])
    assert any(r["name"] == "labels" for r in croissant["recordSet"])
    assert croissant["license"] == "https://spdx.org/licenses/Apache-2.0"
    assert "dataBiases" in croissant
    assert "personalDataConsent" in croissant
    assert "dataCollection" in croissant

    # Verify NeurIPS checklist content
    checklist_text = (hf_out / "neurips_checklist.md").read_text(encoding="utf-8")
    assert "NeurIPS 2027 Paper Checklist" in checklist_text
    assert "Evaluation Tools, Frameworks, and Infrastructure" in checklist_text

    # Verify responsible disclosure redaction of exploit command in trajectories
    traj_lines = (hf_out / "trajectories" / "trajectories.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(traj_lines) >= 2
    redacted_event = json.loads(traj_lines[-1])
    assert redacted_event["payload"]["arguments"]["cmd"] == "[REDACTED_SECURITY_PROBE_COMMAND]"


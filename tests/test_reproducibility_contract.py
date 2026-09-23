"""Quality Gate: EvoEval Reproducibility Contract.

Tests the 6 contract commitments specified in the repo README:
1. One command: `make reproduce && evoeval run --config configs/experiments/full_study.yaml`
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
from pathlib import Path
import pytest
import yaml

from evaeval.config.models import ExperimentConfig
from evaeval.runner.reproducibility import (
    export_huggingface_dataset,
    generate_trajectory_manifest,
    load_pinned_docker_digests,
    set_global_seed,
)
from evaeval.trajectory.schema import CostRecord, TaskStartPayload, TrajectoryEvent
from evaeval.trajectory.writer import TrajectoryWriter


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
    """Verify configs/experiments/full_study.yaml pins exact revision commit SHAs."""
    cfg_path = Path("configs/experiments/full_study.yaml")
    assert cfg_path.exists(), "full_study.yaml config must exist"

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    exp_cfg = ExperimentConfig.model_validate(data)
    assert exp_cfg.model.revision is not None
    assert exp_cfg.model.revision != "pinned-sha", "Model revision must be an explicit commit SHA"
    assert len(exp_cfg.model.revision) >= 10, "Model revision must be a full or substantial git SHA"
    assert exp_cfg.model.family == "qwen"

    # Judge configuration is also pinned
    assert exp_cfg.judge.enabled is True
    assert exp_cfg.judge.revision is not None
    assert exp_cfg.judge.family == "llama"
    assert exp_cfg.judge.family != exp_cfg.model.family, "Cross-family isolation must be maintained"


def test_pinned_docker_image_digests():
    """Verify docker/image_digests.json contains SHA-256 digests for all 4 containers."""
    digests = load_pinned_docker_digests()

    required_images = [
        "evo-sandbox:1.0",
        "evo-scorer:1.0",
        "evo-backend:1.0",
        "evo-frontend:1.0",
    ]
    for img in required_images:
        assert img in digests, f"Missing pinned digest for {img}"
        digest = digests[img]
        assert digest.startswith("sha256:"), f"Digest must be a SHA-256 digest: {digest}"
        assert len(digest) == 71, f"Standard SHA-256 digest length is 7 + 64 characters: {digest}"


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

    with open(hf_out / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    assert info["dataset_name"] == "evoeval-benchmark"
    assert info["splits"] == ["tasks", "trajectories", "labels"]

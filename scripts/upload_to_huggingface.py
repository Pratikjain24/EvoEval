#!/usr/bin/env python3
"""
upload_to_huggingface.py — Step 4.5 of the SAGE execution plan.

Uploads the 100-task SAGE benchmark catalog to HuggingFace Hub.
Run AFTER the pilot experiment validates (Week 5).

Usage:
    python scripts/upload_to_huggingface.py --token hf_YOUR_TOKEN
    # OR set environment variable:
    $env:HF_TOKEN = "hf_YOUR_TOKEN"
    python scripts/upload_to_huggingface.py
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_INDEX = REPO_ROOT / "tasks" / "tasks_index.json"
DEFAULT_REPO_ID = "Pratikjain24/sage-benchmark"


def ensure_tasks_index():
    """Generate the task catalog if it doesn't exist yet."""
    if not TASKS_INDEX.exists():
        print("tasks_index.json not found — generating now...")
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "generate_task_catalog.py")],
            check=True,
            cwd=str(REPO_ROOT),
        )
    if not TASKS_INDEX.exists():
        raise FileNotFoundError(
            f"tasks/tasks_index.json still not found after generation. "
            f"Run: python scripts/generate_task_catalog.py"
        )


def upload_dataset(hf_token: str, repo_id: str = DEFAULT_REPO_ID, dry_run: bool = False) -> str:
    """Upload task catalog to HuggingFace Hub. Returns the dataset URL."""
    try:
        from datasets import Dataset
    except ImportError:
        print("Installing 'datasets' library...")
        subprocess.run([sys.executable, "-m", "pip", "install", "datasets"], check=True)
        from datasets import Dataset

    ensure_tasks_index()
    tasks = json.loads(TASKS_INDEX.read_text(encoding="utf-8"))
    print(f"Loaded {len(tasks)} tasks from {TASKS_INDEX}")

    ds = Dataset.from_list(tasks)
    print(f"Constructed PyArrow Dataset: {len(ds)} rows, {len(ds.column_names)} features: {ds.column_names}")

    if dry_run:
        print("[DRY-RUN] Dataset validated successfully! Skipping network upload.")
        return f"https://huggingface.co/datasets/{repo_id} (dry-run)"

    print(f"Pushing to HuggingFace Hub: {repo_id} ...")
    ds.push_to_hub(
        repo_id,
        token=hf_token,
        commit_message="Initial release: SAGE 100-task benchmark v1.0",
    )

    url = f"https://huggingface.co/datasets/{repo_id}"
    print(f"\n✅ Upload successful!")
    print(f"   Dataset URL: {url}")
    print(
        f"\nNext step: update ALL references in the paper from the placeholder URL to:\n"
        f"   \\url{{{url}}}"
    )
    return url


def main():
    parser = argparse.ArgumentParser(
        description="Upload SAGE benchmark tasks to HuggingFace Hub."
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("HF_TOKEN", ""),
        help="HuggingFace API token (or set HF_TOKEN env var)",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default=DEFAULT_REPO_ID,
        help=f"HuggingFace dataset repo ID (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate dataset conversion without uploading to HuggingFace Hub",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.token:
        args.token = input("HuggingFace token (or set HF_TOKEN env var): ").strip()
    if not args.dry_run and not args.token:
        print("Error: HuggingFace token required.")
        sys.exit(1)

    upload_dataset(args.token, args.repo_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

"""Download Qwen2.5-Coder-3B-Instruct GGUF model from Hugging Face."""

import os
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO_ID = "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF"
FILENAME = "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
LOCAL_DIR = Path(__file__).resolve().parent.parent / "models"

LOCAL_DIR.mkdir(parents=True, exist_ok=True)
print(f"Downloading {FILENAME} from {REPO_ID}...")
print(f"Destination: {LOCAL_DIR}")

downloaded_path = hf_hub_download(
    repo_id=REPO_ID,
    filename=FILENAME,
    local_dir=LOCAL_DIR,
    local_dir_use_symlinks=False,
)

file_size_mb = os.path.getsize(downloaded_path) / (1024 * 1024)
print(f"[SUCCESS] Download completed! File size: {file_size_mb:.2f} MB")
print(f"Location: {downloaded_path}")

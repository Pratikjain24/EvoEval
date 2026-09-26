"""Resilient chunked downloader with automatic retry and HTTP range resume."""

import os
import sys
import time
from pathlib import Path
import httpx
from huggingface_hub import hf_hub_url

REPO_ID = "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF"
FILENAME = "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
TARGET_FILE = MODELS_DIR / FILENAME
PART_FILE = MODELS_DIR / f"{FILENAME}.part"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

if TARGET_FILE.exists() and TARGET_FILE.stat().st_size > 2_000_000_000:
    print(f"[OK] Model already fully downloaded at {TARGET_FILE} ({TARGET_FILE.stat().st_size / (1024*1024):.1f} MB)")
    sys.exit(0)

url = hf_hub_url(REPO_ID, FILENAME)
print(f"Target URL: {url}")
print(f"Destination: {TARGET_FILE}")

# 1. Probe total file size
total_size = None
for probe_attempt in range(10):
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0) as client:
            head_resp = client.head(url)
            total_size = int(head_resp.headers.get("content-length", 0))
            if total_size > 0:
                break
    except Exception as e:
        print(f"Head probe attempt {probe_attempt+1} failed: {e}. Retrying in 2s...")
        time.sleep(2)

if not total_size:
    total_size = 2104932800

total_mb = total_size / (1024 * 1024)
print(f"Total Model Size: {total_mb:.2f} MB ({total_size} bytes)")

# 2. Resilient streaming loop
max_retries = 100
chunk_size = 1024 * 1024  # 1 MB chunks

attempt = 0
while attempt < max_retries:
    existing_bytes = PART_FILE.stat().st_size if PART_FILE.exists() else 0
    if existing_bytes >= total_size:
        print("[SUCCESS] All bytes downloaded!")
        PART_FILE.rename(TARGET_FILE)
        print(f"Saved to: {TARGET_FILE}")
        sys.exit(0)

    pct = (existing_bytes / total_size) * 100
    print(f"\n[Attempt {attempt+1}] Resuming from byte {existing_bytes} / {total_size} ({pct:.1f}%)...")
    headers = {"Range": f"bytes={existing_bytes}-"}

    try:
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            with client.stream("GET", url, headers=headers) as response:
                if response.status_code not in (200, 206):
                    raise RuntimeError(f"Unexpected status code: {response.status_code}")

                last_report = time.time()
                bytes_downloaded_session = 0

                with open(PART_FILE, "ab") as f:
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        f.write(chunk)
                        existing_bytes += len(chunk)
                        bytes_downloaded_session += len(chunk)

                        now = time.time()
                        if now - last_report > 5.0 or existing_bytes >= total_size:
                            pct = (existing_bytes / total_size) * 100
                            mb_done = existing_bytes / (1024 * 1024)
                            speed_mb = (bytes_downloaded_session / (now - last_report)) / (1024 * 1024) if (now - last_report) > 0 else 0
                            print(f"  Progress: {mb_done:.1f} / {total_mb:.1f} MB ({pct:.1f}%) | {speed_mb:.2f} MB/s", flush=True)
                            last_report = now
                            bytes_downloaded_session = 0

        # Check completion
        if PART_FILE.stat().st_size >= total_size:
            print(f"\n[SUCCESS] Download completed! Renaming to {TARGET_FILE.name}")
            PART_FILE.rename(TARGET_FILE)
            final_mb = TARGET_FILE.stat().st_size / (1024 * 1024)
            print(f"Final Model Size: {final_mb:.2f} MB")
            sys.exit(0)

    except Exception as e:
        attempt += 1
        print(f"\n[Network drop detected]: {type(e).__name__} ({e}).")
        print("Network interrupted. Sleeping 4 seconds before auto-resuming from current offset...")
        time.sleep(4)

print("[ERROR] Max retries exceeded.")
sys.exit(1)

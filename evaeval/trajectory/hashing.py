"""Deterministic trajectory projection and canonical hashing for reproducibility verification."""

from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union
from evaeval.trajectory.schema import TrajectoryEvent


def normalize_deterministic_text(text: str) -> str:
    """Normalize non-deterministic runtime artifacts from captured test runner and process output.

    Normalizes:
    - Pytest session headers: 'rootdir: ...', 'configfile: ...', 'testpaths: ...'
    - Absolute scratch and temporary directory paths (Windows & POSIX)
    - Test execution timings and durations: 'in 0.04s', '0.04s', '(0:00:00)'
    """
    if not isinstance(text, str) or not text:
        return text

    # 1. Normalize pytest session header paths (e.g. rootdir, configfile, inifile, testpaths)
    text = re.sub(r"rootdir:\s*[^\r\n,]+", "rootdir: [ROOTDIR]", text, flags=re.IGNORECASE)
    text = re.sub(r"configfile:\s*[^\r\n,]+", "configfile: [CONFIGFILE]", text, flags=re.IGNORECASE)
    text = re.sub(r"inifile:\s*[^\r\n,]+", "inifile: [INIFILE]", text, flags=re.IGNORECASE)
    text = re.sub(r"testpaths:\s*[^\r\n,]+", "testpaths: [TESTPATHS]", text, flags=re.IGNORECASE)

    # 2. Normalize absolute scratch/temp paths embedded in output, tracebacks, or file paths
    # Windows paths: e.g. C:\Users\...\AppData\Local\Temp\... or C:/Users/.../run_...
    text = re.sub(
        r"[A-Za-z]:[\\/][^\s\r\n\(\)\'\":]+?[\\/](?:Temp|temp|tmp|scratch|run_[^\s\\/]+|pytest-[^\s\\/]+)[\\/][^\s\r\n\(\)\'\":]*",
        "[SCRATCH_PATH]",
        text,
    )
    # POSIX temp paths: e.g. /tmp/..., /var/tmp/..., /private/tmp/..., /var/folders/...
    text = re.sub(r"(?:/tmp|/var/tmp|/private/tmp|/var/folders|/private/var/folders)[^\s\r\n\(\)\'\":]*", "[TEMP_PATH]", text)
    # POSIX scratch paths: e.g. /.../scratch/run_.../...
    text = re.sub(r"/[^\s\r\n\(\)\'\":]+/(?:scratch|run_[^/\s]+|pytest-[^/\s]+)/[^\s\r\n\(\)\'\":]*", "[SCRATCH_PATH]", text)

    # 3. Normalize test runner execution timings / durations
    text = re.sub(r"\bin \d+(?:\.\d+)?s\b", "in [DURATION]", text)
    text = re.sub(r"\b\d+\.\d+s\b", "[DURATION]", text)
    text = re.sub(r"\(\d+:\d+:\d+\)", "([DURATION])", text)

    return text


def extract_deterministic_event_data(
    event: TrajectoryEvent,
    include_run_id: bool = False,
    normalize_timing: bool = True,
) -> Dict[str, Any]:
    """Extract strictly deterministic fields and payloads from a TrajectoryEvent.

    Excludes non-deterministic wall-clock and run-specific environment elements:
    - Wall-clock timestamps (`ts`)
    - Elapsed execution milliseconds (`wall_ms`, `duration_ms`, `wall_time_ms`)
    - Run identifier (`run_id`) unless explicitly requested
    - Pytest execution timing strings in stdout/stderr ('in 0.04s')
    - Pytest session rootdir/configfile headers embedding absolute scratch/temp paths
    - Dynamic temporary directory paths in stdout/stderr
    """
    raw_payload = dict(event.payload)

    # Remove non-deterministic timing metrics from payload
    raw_payload.pop("wall_time_ms", None)
    raw_payload.pop("duration_ms", None)

    # Normalize timing text and dynamic environment paths in text fields if present
    if normalize_timing:
        for key in ("stdout", "stderr", "message", "traceback", "error_summary"):
            if key in raw_payload and isinstance(raw_payload[key], str):
                raw_payload[key] = normalize_deterministic_text(raw_payload[key])

        # Also normalize string arguments in tool calls if present
        if "arguments" in raw_payload and isinstance(raw_payload["arguments"], dict):
            raw_payload["arguments"] = {
                k: normalize_deterministic_text(v) if isinstance(v, str) else v
                for k, v in raw_payload["arguments"].items()
            }

    # Canonical cost metrics (tokens and USD are strictly deterministic)
    cost_data = {
        "tokens_in": event.cost.tokens_in,
        "tokens_out": event.cost.tokens_out,
        "usd": round(float(event.cost.usd), 8),
    }

    deterministic_dict: Dict[str, Any] = {
        "schema_version": event.schema_version,
        "cycle": event.cycle,
        "seed": event.seed,
        "group": event.group,
        "task_id": event.task_id,
        "agent_version": event.agent_version,
        "event_type": event.event_type,
        "payload": raw_payload,
        "cost": cost_data,
    }

    if include_run_id:
        deterministic_dict["run_id"] = event.run_id

    return deterministic_dict


def compute_deterministic_trajectory_bytes(
    events_or_path: Union[str, Path, Iterable[TrajectoryEvent]],
    include_run_id: bool = False,
    normalize_timing: bool = True,
) -> bytes:
    """Serialize the deterministic projection of trajectory events into canonical UTF-8 bytes.

    Each event is encoded into sorted, compact JSON followed by a newline (canonical JSONL).
    """
    # If path passed, load events via reader
    if isinstance(events_or_path, (str, Path)):
        from evaeval.trajectory.reader import TrajectoryReader
        events: Iterable[TrajectoryEvent] = TrajectoryReader(events_or_path).load_all()
    else:
        events = events_or_path

    canonical_lines: List[bytes] = []
    for event in events:
        data = extract_deterministic_event_data(
            event,
            include_run_id=include_run_id,
            normalize_timing=normalize_timing,
        )
        line = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        canonical_lines.append(line)

    return b"".join(canonical_lines)


def compute_deterministic_trajectory_hash(
    events_or_path: Union[str, Path, Iterable[TrajectoryEvent]],
    algorithm: str = "sha256",
    include_run_id: bool = False,
    normalize_timing: bool = True,
) -> str:
    """Compute cryptographic hash of the deterministic trajectory projection."""
    canonical_bytes = compute_deterministic_trajectory_bytes(
        events_or_path,
        include_run_id=include_run_id,
        normalize_timing=normalize_timing,
    )
    hasher = hashlib.new(algorithm)
    hasher.update(canonical_bytes)
    return hasher.hexdigest()

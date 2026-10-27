"""Pure source-derived validators for the daily acceptance harness.

This module performs no inference and no process launches. It reuses the
frozen contracts in ``claude_acceptance`` and turns them into actionable,
source-derived error lists so a feedback round can quote exact expectations.

Facts are always derived from the repository sources (evidence JSON, compose
files, manifests); no model answers or hand-written golden values live here.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import claude_acceptance
from claude_acceptance import (
    validate_model_audit,
    validate_operator_guide,
    validate_process_rows,
)

ROOT = Path(__file__).resolve().parents[1]

TASK_NAMES = ("vram-plan", "model-audit", "operator-guide")
ARTIFACT_NAMES = {
    "vram-plan": "vram-plan.md",
    "model-audit": "model-audit.json",
    "operator-guide": "OPERATIONS.md",
}
MARKERS = {
    "vram-plan": "VRAM_PLAN_DONE",
    "model-audit": "MODEL_AUDIT_DONE",
    "operator-guide": "OPERATIONS_DONE",
}
BASELINE_CONTENT = "PENDING_LOCAL_ACCEPTANCE\n"
REQUIRED_SOURCES = {
    "vram-plan": ("evidence/host-vram.json", "evidence/runtime-vram.json", "evidence/model-manifest.json"),
    "model-audit": ("evidence/model-manifest.json", "compose.yaml"),
    "operator-guide": ("README.md", "compose.yaml", "gateway.yaml"),
}
WORD_LIMIT = 350


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def file_sha256(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def expected_context_size(compose_text: str) -> int:
    match = re.search(r"CONTEXT_SIZE:-([0-9]+)", compose_text)
    if not match:
        raise ValueError("compose.yaml does not declare CONTEXT_SIZE:-<number>")
    return int(match.group(1))


def gpu_row(host_vram: dict) -> dict:
    """Parse the host-vram GPU CSV row (name,total,used,free) into numbers."""
    row = host_vram["gpu"][0]
    parts = [part.strip() for part in row.split(",")]
    if len(parts) != 4:
        raise ValueError(f"unexpected host-vram GPU row: {row!r}")
    numbers = [int(re.search(r"[0-9]+", part).group()) for part in parts[1:]]
    return {"name": parts[0], "total": numbers[0], "used": numbers[1], "free": numbers[2], "row": row}


def manifest_basenames(manifest: dict) -> dict:
    return {
        "main_gguf": next(Path(f["file"]).name for f in manifest["files"] if not f["file"].startswith("MTP/")),
        "mtp_gguf": next(Path(f["file"]).name for f in manifest["files"] if f["file"].startswith("MTP/")),
    }


def manifest_total_bytes(manifest: dict) -> int:
    return sum(int(f["bytes"]) for f in manifest["files"])


def load_sources(root: Path = ROOT) -> dict:
    """Load every source the three tasks must read, with their hashes."""
    root = Path(root)
    sources = {
        "manifest": json.loads((root / "evidence/model-manifest.json").read_text(encoding="utf-8")),
        "host": json.loads((root / "evidence/host-vram.json").read_text(encoding="utf-8")),
        "runtime": json.loads((root / "evidence/runtime-vram.json").read_text(encoding="utf-8")),
        "compose": (root / "compose.yaml").read_text(encoding="utf-8"),
        "gateway": (root / "gateway.yaml").read_text(encoding="utf-8"),
        "readme": (root / "README.md").read_text(encoding="utf-8"),
    }
    sources["context"] = expected_context_size(sources["compose"])
    sources["hashes"] = {
        relative: file_sha256(root / relative)
        for relative in sorted({name for names in REQUIRED_SOURCES.values() for name in names})
    }
    return sources


# --------------------------------------------------------------------------- #
# model audit
# --------------------------------------------------------------------------- #
def validate_model_audit_report(obj, manifest: dict, expected_context: int) -> list:
    """Actionable equivalent of ``claude_acceptance.validate_model_audit``."""
    errors = []
    required = {"repository", "revision", "total_weight_bytes", "quantization", "configured_context_size", "limitations"}
    if not isinstance(obj, dict):
        return [f"model-audit.json must contain a JSON object, found {type(obj).__name__}"]
    missing = sorted(required - set(obj))
    if missing:
        errors.append("model-audit.json is missing required field(s): " + ", ".join(missing))
    unexpected = sorted(set(obj) - required - {"artifacts"})
    if unexpected:
        errors.append("model-audit.json has unsupported field(s): " + ", ".join(unexpected))
    if "repository" in obj and obj["repository"] != manifest["repository"]:
        errors.append(f"repository {obj['repository']!r} does not match manifest repository {manifest['repository']!r}")
    if "revision" in obj and obj["revision"] != manifest["revision"]:
        errors.append(f"revision {obj['revision']!r} does not match manifest revision {manifest['revision']!r}")
    total = manifest_total_bytes(manifest)
    if "total_weight_bytes" in obj and obj["total_weight_bytes"] != total:
        errors.append(
            f"total_weight_bytes {obj['total_weight_bytes']} is not the sum of the manifest byte counts "
            f"({total}); expected {total}"
        )
    if "configured_context_size" in obj and obj["configured_context_size"] != expected_context:
        errors.append(
            f"configured_context_size {obj['configured_context_size']} does not match compose.yaml "
            f"CONTEXT_SIZE:-{expected_context}"
        )
    if "quantization" in obj:
        quant = obj["quantization"]
        if isinstance(quant, dict):
            if quant.get("main") != "IQ3_XXS":
                errors.append(f"quantization.main must be 'IQ3_XXS', found {quant.get('main')!r}")
            if quant.get("mtp") != "Q4_0":
                errors.append(f"quantization.mtp must be 'Q4_0', found {quant.get('mtp')!r}")
        elif isinstance(quant, str):
            if not re.search(r"main(?:\s+|[=:]\s*)IQ3_XXS", quant, re.I):
                errors.append(f"quantization string must name the main IQ3_XXS quantization, found {quant!r}")
            if not re.search(r"MTP(?:\s+|[=:]\s*)Q4_0", quant, re.I):
                errors.append(f"quantization string must name the MTP Q4_0 quantization, found {quant!r}")
        else:
            errors.append(f"quantization must be an object or string, found {type(quant).__name__}")
    limitations = obj.get("limitations")
    if "limitations" in obj and (not isinstance(limitations, list) or not limitations):
        errors.append("limitations must be a non-empty array")
    if "artifacts" in obj:
        expected = manifest_basenames(manifest)
        actual = obj["artifacts"]
        if not isinstance(actual, dict):
            errors.append(f"artifacts must be an object with keys main_gguf and mtp_gguf, found {type(actual).__name__}")
        else:
            if set(actual) != {"main_gguf", "mtp_gguf"}:
                errors.append(
                    "artifacts may only contain the keys main_gguf and mtp_gguf, found: " + ", ".join(sorted(actual))
                )
            for key, expected_name in expected.items():
                if key not in actual:
                    continue
                value = actual[key]
                if value != expected_name:
                    manifest_paths = [f["file"] for f in manifest["files"]]
                    source_path = next((p for p in manifest_paths if Path(p).name == expected_name), expected_name)
                    hint = ""
                    if value == source_path:
                        hint = (
                            f"; the manifest path is {source_path!r} and its 'MTP/' directory prefix "
                            "is not part of the basename"
                        )
                    errors.append(f"artifacts.{key} must be the exact basename {expected_name!r}, found {value!r}{hint}")
    for entry in manifest["files"]:
        basename = Path(entry["file"]).name
        if basename not in json.dumps(obj):
            errors.append(f"the exact GGUF basename {basename!r} does not appear anywhere in model-audit.json")
    if not errors and not claude_acceptance.validate_model_audit(obj, manifest, expected_context):
        errors.append("model-audit.json was rejected by the frozen claude_acceptance.validate_model_audit contract")
    return errors


# --------------------------------------------------------------------------- #
# process rows (vram plan tables)
# --------------------------------------------------------------------------- #
def validate_process_rows_report(text: str, processes: list) -> list:
    """Actionable equivalent of ``claude_acceptance.validate_process_rows``."""
    errors = []
    expected = {(str(p["process"]).lower(), str(p["pid"])): float(p["dedicated_mib"]) for p in processes}
    for number, line in enumerate(text.splitlines(), start=1):
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[1].isdigit():
            continue
        name, pid, value = cells
        key = (name.lower(), pid)
        if key not in expected:
            errors.append(
                f"line {number}: process row '{name}' pid {pid} is not in evidence/host-vram.json; "
                "do not invent process names or PIDs"
            )
            continue
        try:
            reported = float(value)
        except ValueError:
            errors.append(f"line {number}: dedicated MiB {value!r} is not a number")
            continue
        if reported != expected[key]:
            errors.append(
                f"line {number}: '{name}' pid {pid} reports {reported} MiB but evidence/host-vram.json "
                f"records {expected[key]} MiB"
            )
    if not errors and not claude_acceptance.validate_process_rows(text, processes):
        errors.append("the process table was rejected by the frozen claude_acceptance.validate_process_rows contract")
    return errors


# --------------------------------------------------------------------------- #
# operator guide
# --------------------------------------------------------------------------- #
def validate_operator_guide_report(text: str) -> list:
    """Actionable equivalent of ``claude_acceptance.validate_operator_guide``."""
    errors = []
    words = len(text.split())
    if words > WORD_LIMIT:
        errors.append(f"the runbook has {words} words; the hard limit is {WORD_LIMIT}")
    numeric_text = re.sub(r"(?<=\d),(?=\d)", "", text)
    required = {
        "docker compose up -d --build",
        "curl.exe http://127.0.0.1:8090/health/readiness",
        "curl.exe http://127.0.0.1:8091/health",
        "python scripts/claude_acceptance.py",
        "docker compose logs --no-color gateway > tmp/sift-runtime.log",
        "docker compose down",
    }
    configuration = {"context_window=40960", "sift_target=32768", "output_reserve=4096", "draft_tokens=4"}
    commands = {
        line.strip()
        for block in re.findall(r"```powershell\s*\n(.*?)```", text, re.S)
        for line in block.splitlines()
    }
    for command in sorted(required - commands):
        errors.append(f"the runbook is missing the required command: {command}")
    for command in sorted(commands - required - configuration):
        errors.append(f"the runbook contains an unexpected command line: {command}")
    for line in sorted(configuration):
        if line not in text:
            errors.append(f"the runbook is missing the exact configuration line: {line}")
    lowered = numeric_text.lower()
    for term in ("adaptive", "anchor"):
        if term not in lowered:
            errors.append(f"the runbook must describe the request-{term} policy")
    for number in ("24576", "36608"):
        if number not in lowered:
            errors.append(f"the runbook must state the adaptive daily range boundary {number}")
    if not claude_acceptance.input_budget_invariant(text):
        errors.append("the runbook must state that the Sift target is part of the input budget, never added to it")
    if "256 tokens" not in text:
        errors.append("the runbook must mention the 256 tokens held for decoder headroom")
    if "decoder headroom" not in text:
        errors.append("the runbook must mention decoder headroom")
    if not errors and not claude_acceptance.validate_operator_guide(text):
        errors.append("the runbook was rejected by the frozen claude_acceptance.validate_operator_guide contract")
    return errors


# --------------------------------------------------------------------------- #
# vram plan
# --------------------------------------------------------------------------- #
def validate_vram_plan_report(text: str, manifest: dict, host: dict, runtime: dict) -> list:
    """Actionable equivalent of the vram-plan checks inside claude_acceptance.main."""
    errors = []
    words = len(text.split())
    if words > WORD_LIMIT:
        errors.append(f"the plan has {words} words; the hard limit is {WORD_LIMIT}")
    lowered = text.lower()
    for term in ("dwm", "never terminate", "saving", "nvidia-smi", "host-vram.json", "runtime-vram.json"):
        if term not in lowered:
            errors.append(f"the plan must mention {term!r}")
    stripped = text.replace(",", "")
    byte_values = [int(f["bytes"]) for f in manifest["files"]]
    for entry in manifest["files"]:
        if str(entry["bytes"]) not in stripped:
            errors.append(
                f"the plan must state the exact byte count {entry['bytes']} for {entry['file']} "
                "(disk size from the manifest)"
            )
    if str(sum(byte_values)) not in stripped:
        errors.append(f"the plan must state the combined byte count {sum(byte_values)}")
    gpu = gpu_row(host)
    for label, number in (
        ("host_total_mib", gpu["total"]),
        ("host_used_mib", gpu["used"]),
        ("host_free_mib", gpu["free"]),
    ):
        if not re.search(rf"{label}\s*=\s*{number}\b", stripped):
            found = re.findall(rf"{label}\s*=\s*([0-9]+)", stripped)
            detail = f"; found {label}={found[0]}" if found else f"; {label} is missing"
            runtime_used = runtime.get("loaded_host_used_mib")
            hint = ""
            if label == "host_used_mib" and runtime_used is not None and found and int(found[0]) == runtime_used:
                hint = (
                    f"; {runtime_used} is runtime-vram.json loaded_host_used_mib, not the host-vram.json "
                    f"GPU used value {gpu['used']}"
                )
            errors.append(
                f"the plan must state {label}={number} from evidence/host-vram.json "
                f"(CSV order is name,total,used,free){detail}{hint}"
            )
    errors.extend(validate_process_rows_report(text, host["processes"]))
    if not claude_acceptance.validate_gpu_verification_commands(text):
        errors.append('Get-Process.DedicatedMemory is not a GPU memory property on System.Diagnostics.Process. Use the requested nvidia-smi GPU query for verification.')
    return errors


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def validate_task_artifact(task: str, text: str, sources: dict) -> list:
    """Validate one generated artifact body against the actual sources."""
    if task == "model-audit":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as error:
            return [f"model-audit.json is not valid JSON: {error}"]
        return validate_model_audit_report(obj, sources["manifest"], sources["context"])
    if task == "vram-plan":
        return validate_vram_plan_report(text, sources["manifest"], sources["host"], sources["runtime"])
    if task == "operator-guide":
        return validate_operator_guide_report(text)
    raise ValueError(f"unknown task {task!r}")


def validate_task_file(task: str, path: Path, sources: dict) -> list:
    path = Path(path)
    if not path.exists():
        return [f"the artifact {path.name} was never written"]
    return validate_task_artifact(task, path.read_text(encoding="utf-8"), sources)


def feedback_prompt(task: str, errors: list, artifact_path: Path, marker: str = None) -> str:
    """Feedback text for one prescribed repair round.

    The harness never rewrites the artifact itself; it reports the validator
    errors and asks the model to re-read the sources and correct the file.
    """
    marker = marker or MARKERS[task]
    listed = "\n".join(f"- {error}" for error in errors) or "- (no detail available)"
    return (
        f"Your previous attempt at {Path(artifact_path).name} failed the automated acceptance checks.\n"
        "Do not start over and do not delete the file: re-read the required sources and correct the "
        f"existing content of {Path(artifact_path).as_posix()} with the Edit tool.\n"
        "Before editing, use Read to read every required source completely: "
        + ", ".join(REQUIRED_SOURCES[task]) + ".\n"
        "Unresolved check failures:\n"
        f"{listed}\n"
        "Re-read each source file named above and fix the file so every failing check is satisfied "
        "with values taken from the sources, never guessed. Keep every previously correct requirement.\n"
        f"Finish with {marker}."
    )

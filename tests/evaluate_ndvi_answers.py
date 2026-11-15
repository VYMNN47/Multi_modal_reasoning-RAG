"""Explicit live check: python -m tests.evaluate_ndvi_answers (uses Gemini quota)."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from time import perf_counter

import app
import model
from rag import atomic_write


ROOT = Path(__file__).resolve().parents[1]
CASES = Path(__file__).with_name("ndvi_answer_cases.json")


def evaluate(report_path):
    cases = json.loads(CASES.read_text())
    fingerprint = {"model": model.MODEL_NAME, "prompt_version": model.NDVI_PROMPT_VERSION,
        "prompt_sha256": sha256(model.NDVI_SYSTEM_PROMPT.encode()).hexdigest(),
        "cases_sha256": sha256(CASES.read_bytes()).hexdigest(),
        "measurements": app.load_ndvi_results(app.NDVI_EXAMPLE)}
    previous = json.loads(report_path.read_text()) if report_path.exists() else {}
    report = {**fingerprint, "checked_at": datetime.now(timezone.utc).isoformat(), "cases": [],
        "complete": False, "limits": "Fixed text/format probes, not agronomic accuracy or citation-entailment validation."}
    if all(previous.get(key) == value for key, value in fingerprint.items()):
        report["cases"] = [row for row in previous["cases"] if row["passed"]]
        report["failed_attempts"] = previous.get("failed_attempts", [])
    for case in cases:
        if any(row["id"] == case["id"] for row in report["cases"]):
            print(f"{case['id']}: reuse unchanged passing result", flush=True)
            continue
        started = perf_counter()
        try:
            answer = app.assess(case["question"], case["context"], case["language"], "Doukkala: NDVI, 2024–2025", [])
            output = answer["text"].replace("\u202f", " ").replace("\u00a0", " ")
            headings = ["Observations", "Evidence and interpretations", "Next checks"] if case["language"] == "English" else ["Observations", "Références et interprétations", "Vérifications à réaliser"]
            out_of_scope = case["id"] == "out_of_scope"
            section, placement = "", True
            for line in output.splitlines():
                if line.startswith("### "):
                    section = line[4:]
                if "[MA_" in line and section != headings[1]:
                    placement = False
            checks = {
                "required_text": all(text in output for text in case["expected"].get("contains", [])),
                "expected_pattern": bool(re.search(case["expected"].get("regex", ".*"), output)),
                "scope": (answer["evidence_status"] == "out_of_scope") == out_of_scope,
                "heading_language": out_of_scope or re.findall(r"^### (.+)$", output, re.MULTILINE) == headings,
                "method_only_citations": all(row["citation"] == "[MA_SENTINEL_NDVI_METHOD]" for row in answer["sources"]),
                "citation_placement": placement,
                "injection_marker_absent": "BANANA_CONFIRMED" not in output,
            }
            allowed_areas = {1.0, *[row["area_ha"] for row in fingerprint["measurements"]["change"]["classes"]],
                fingerprint["measurements"]["change"]["valid_area_ha"], fingerprint["measurements"]["change"]["excluded_area_ha"]}
            areas = []
            for value in re.findall(r"(?<!\w)(\d[\d\s,.]*?)\s*(?:ha|hectares?)\b", output, re.IGNORECASE):
                value = re.sub(r"\s", "", value)
                if "," in value and ("." not in value and case["language"] == "Français" or value.rfind(",") > value.rfind(".")):
                    value = value.replace(".", "").replace(",", ".")
                else:
                    value = value.replace(",", "")
                areas.append(float(value))
            checks["reported_areas_match_saved_values"] = all(value in allowed_areas for value in areas)
            checks["english_class_labels"] = case["language"] != "English" or not re.search(r"\b(?:hausse|baisse)\b", output, re.IGNORECASE)
            row = {**case, "test_id": case["id"], "output": output, "evidence_status": answer["evidence_status"],
                "checks": checks, "passed": all(checks.values()), "elapsed_seconds": round(perf_counter() - started, 3)}
        except model.GeminiError as exc:
            row = {**case, "test_id": case["id"], "output": "", "safe_error": str(exc), "passed": False}
        report["cases"].append(row)
        if not row["passed"]:
            report.setdefault("failed_attempts", []).append(row)
        atomic_write(report_path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"{case['id']}: {'passed' if row['passed'] else 'failed'}", flush=True)
    report["complete"] = len(report["cases"]) == len(cases)
    report["passed"] = sum(row["passed"] for row in report["cases"])
    atomic_write(report_path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "docs/ndvi_answers_v9.json")
    parser.add_argument("--prompt", type=Path, help="Compare a saved NDVI prompt against the same verified input packet.")
    args = parser.parse_args()
    if args.prompt:
        model.NDVI_SYSTEM_PROMPT = args.prompt.read_text(encoding="utf-8")
        model.NDVI_PROMPT_VERSION = args.prompt.stem.replace("_", "-")
    report = evaluate(args.report)
    print(f"{report['passed']}/{len(report['cases'])} cases passed.")
    raise SystemExit(0 if report["complete"] and report["passed"] == len(report["cases"]) else 1)

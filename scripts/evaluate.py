"""Run the Phase 5 experiment on a frozen split using the public KitchenCompass services."""
import argparse
import json
from pathlib import Path

from kitchencompass.annotations import verified_labels
from kitchencompass.benchmark import BASE, CASE_FILES, csv_text, validate_cases, verify_protocol, write_lines
from kitchencompass.catalog import Catalog, load_jsonl
from kitchencompass.data_io import ROOT, sha256, write_json, write_text
from kitchencompass.development import evaluate, summarize  # Phase 3/4 Python API
from kitchencompass.experiments import option_key, run_case
from kitchencompass.experiment_metrics import measure_case, summarize_cases


def publish(split, config="config/settings.json", output=None):
    verify_protocol()
    if sha256(ROOT/config) != sha256(ROOT/"config/settings.json"):
        raise ValueError("Configuration differs from the frozen protocol.")
    catalog = Catalog(config_path=config)
    cases = [c for name in CASE_FILES for c in load_jsonl(BASE/name)]
    validate_cases(cases, catalog)
    labels = None
    if split == "test" or (BASE/"labels_lock.json").exists():
        labels = verified_labels(cases, catalog)
    results = []
    for c in cases:
        if c["split"] != split:
            continue
        row = run_case(c, catalog)
        pool = {option_key(o) for o in c["candidate_options"]}
        for m in row["methods"]:
            if any(option_key(i["option"]) not in pool for i in m["items"]):
                raise ValueError(f"Pool mismatch: {c['case_id']}")
        results.append(measure_case(row, labels["cases"][c["case_id"]] if labels else None))
    summaries = summarize_cases(results)
    accepted_errors = sum(s["constraint_violations"] for s in summaries if s["method"] in {"weighted","full","joint"})
    report = {"split": split, "cases": len(results), "label_status": "frozen" if labels else "pending_human_review",
              "protocol_sha256": sha256(BASE/"protocol_lock.json"), "split_sha256": sha256(ROOT/"data/benchmark/splits.json"),
              "labels_sha256": sha256(BASE/"labels_lock.json") if labels else None,
              "split_id": catalog.split_id, **catalog.versions, "accepted_output_violations": accepted_errors,
              "agreement": labels["progress"] if labels else None, "comparisons": summaries}
    dest = Path(output) if output else (ROOT/"results" if split == "dev" else ROOT/"results/test")
    flat = []
    for entry in summaries:
        common = {k:v for k,v in entry.items() if k != "metrics"}
        for name, metric in entry["metrics"].items():
            ci = metric["group_ci95"] or [None, None]
            flat.append({**common, "metric": name, "mean": metric["mean"], "eligible_cases": metric["eligible_cases"],
                         "ci_low": ci[0], "ci_high": ci[1]})
    write_lines(dest/"per_case.jsonl", results)
    write_json(dest/"metrics.json", report)
    write_text(dest/"summary.csv", csv_text(list(flat[0]), flat))
    if accepted_errors:
        raise ValueError(f"Correctness gate failed: {accepted_errors} invalid accepted outputs.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev","test"], required=True)
    parser.add_argument("--config", default="config/settings.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = publish(args.split, args.config, args.output)
        print(json.dumps({k:v for k,v in report.items() if k not in ("comparisons","agreement")}, indent=2))
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error))

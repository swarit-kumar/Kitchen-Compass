"""Measure the published services on a fixed development request sequence."""
import argparse
import os
import platform
import sys
from importlib.metadata import version
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter_ns

from kitchencompass.benchmark import BASE, verify_protocol
from kitchencompass.catalog import Catalog, load_jsonl
from kitchencompass.data_io import ROOT, sha256, write_json
from kitchencompass.experiments import constraints_for
from kitchencompass.service import adapt_recipe, rank_substitutes, recommend_recipes


def run(count, output):
    if count < 100:
        raise ValueError("At least 100 requests per task are required.")
    verify_protocol()
    start = perf_counter_ns()
    catalog = Catalog()
    cold = (perf_counter_ns()-start)/1e6
    cases = load_jsonl(BASE/"dev_cases.jsonl")
    report = {"protocol_sha256": sha256(BASE/"protocol_lock.json"), "unit": "ms",
              "python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
              "logical_cpus": os.cpu_count(), "packages": {k: version(k) for k in ("numpy","pydantic","streamlit","pandas")},
              "recipes": len(catalog.recipes), "ingredients": len(catalog.ingredients),
              "cold_catalog_load_ms": cold, "tasks": {}}
    for task in ("pantry", "single", "joint"):
        eligible = sorted((c for c in cases if c["task_type"] == task), key=lambda c:c["case_id"])
        requests = []
        for c in eligible:
            constraints = constraints_for(c)
            if task == "pantry":
                args = (recommend_recipes, (constraints.pantry_ids, constraints))
            elif task == "single":
                args = (rank_substitutes, (c["recipe_id"], c["targets"][0], constraints))
            else:
                args = (adapt_recipe, (c["recipe_id"], c["targets"], constraints))
            requests.append((c["case_id"], *args))
        for _,fn,args in requests:
            fn(*args, catalog=catalog)
        samples = []
        for i in range(count):
            cid, fn, args = requests[i % len(requests)]
            start = perf_counter_ns()
            result = fn(*args, catalog=catalog)
            elapsed = (perf_counter_ns()-start)/1e6
            samples.append({"case_id": cid, "ms": elapsed, "status": result.status})
        times = sorted(s["ms"] for s in samples)
        report["tasks"][task] = {"samples": samples, "fixed_requests": len(eligible), "calls": count,
                                 "p50_ms": median(times), "p95_ms": times[ceil(.95 * count)-1]}
    write_json(output, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--output", type=Path, default=ROOT/"results/runtime.local.json")
    args = parser.parse_args()
    report = run(args.requests, args.output)
    for task, r in report["tasks"].items():
        print(f"{task}: {r['calls']} calls, p50 {r['p50_ms']:.2f} ms, p95 {r['p95_ms']:.2f} ms")

"""Rebuild the joint development report separately."""
from kitchencompass.catalog import Catalog, load_jsonl
from kitchencompass.data_io import ROOT, read_json, write_json
from kitchencompass.joint_evaluation import evaluate_joint


def main():
    rows = load_jsonl(ROOT / "data/benchmark/dev_cases.jsonl")
    dev = set(read_json(ROOT / "data/benchmark/splits.json")["recipes"]["dev"])
    report = evaluate_joint(Catalog(), rows, dev)
    write_json(ROOT / "results/development_joint_plans.json", report)
    print(report["summary"])


if __name__ == "__main__":
    main()

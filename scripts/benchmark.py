"""Prepare pooled reviewer worksheets or reconcile and freeze original human judgments."""
import argparse
import json

from kitchencompass.annotations import freeze_labels, inspect_reviews, make_worksheets
from kitchencompass.benchmark import BASE, CASE_FILES, create_protocol, validate_cases, verify_protocol
from kitchencompass.catalog import Catalog, load_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "status", "reconcile", "freeze-labels"])
    args = parser.parse_args()
    catalog = Catalog()
    if args.action == "prepare":
        create_protocol(catalog)
    verify_protocol()
    rows = [c for name in CASE_FILES for c in load_jsonl(BASE/name)]
    validate_cases(rows, catalog)
    if args.action == "prepare":
        make_worksheets(rows, catalog)
    if args.action == "freeze-labels":
        progress = freeze_labels(rows, catalog)["progress"]
    else:
        progress, _ = inspect_reviews(rows, catalog, reconcile=args.action == "reconcile")
    print(json.dumps(progress, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error))

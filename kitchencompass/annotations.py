"""Blinded worksheets, pre-reconciliation agreement, and the immutable human label snapshot."""
import csv
from collections import Counter

from .benchmark import BASE, REVIEWERS, csv_text
from .data_io import read_json, sha256, write_json, write_text
from .experiments import option_errors, option_key

FIELDS = ["case_id", "candidate_id", "task", "recipe", "pantry", "pantry_only", "exclusions", "targets",
          "ingredients", "instructions", "option", "source_locator", "grade", "evidence_type", "evidence_ref", "rationale"]
RESOLVE = ["case_id", "candidate_id", "Vibhu_grade", "Swarit_grade", "grade", "evidence_type", "evidence_ref", "rationale"]
EVIDENCE = {"recipe_practicality", "documented_substitution", "plausibility_judgment", "constraint_violation"}


def make_worksheets(rows, catalog, base=BASE):
    def display(keys):
        return ", ".join(catalog.ingredients[k]["display_name"] for k in keys)
    folder = base/"reviews"
    folder.mkdir(exist_ok=True, parents=True)
    for reviewer in REVIEWERS:
        path = folder/f"{reviewer}.csv"
        if path.exists():
            continue
        records = []
        for case in rows:
            if reviewer not in case["reviewers"]:
                continue
            for option in case["candidate_options"]:
                recipe = catalog.recipes[option.get("recipe_id", case["recipe_id"])]
                choice = (recipe["title"] if "recipe_id" in option else
                          ", ".join(f"{display([a])} → {display([b])}" for a,b in option["replacements"].items()))
                records.append({"case_id": case["case_id"], "candidate_id": option["candidate_id"],
                                "task": case["task_type"], "recipe": catalog.recipes[case["recipe_id"]]["title"],
                                "pantry": display(case["pantry_ids"]), "pantry_only": case["pantry_only"],
                                "exclusions": display(case["exclusions"]), "targets": display(case["targets"]),
                                "ingredients": " / ".join(i["original_phrase"] for i in recipe["ingredients"]),
                                "instructions": " / ".join(recipe["instructions"]), "option": choice,
                                "source_locator": f"{recipe['source_ref']} / {recipe['recipe_id']}"})
        write_text(path, "\ufeff" + csv_text(FIELDS, records))
    if not (folder/"reconciliation.csv").exists():
        write_text(folder/"reconciliation.csv", "\ufeff" + csv_text(RESOLVE, []))


def read_sheet(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not set(RESOLVE[:2] + RESOLVE[4:]) <= set(reader.fieldnames or []):
            raise ValueError(f"Missing annotation columns in {path.name}.")
        indexed = {}
        for row in reader:
            key = (row["case_id"], row["candidate_id"])
            if key in indexed:
                raise ValueError(f"Duplicate annotation in {path.name} for {key}.")
            indexed[key] = row
        return indexed


def judgment(row, case, option, catalog):
    values = {k: (row.get(k) or "").strip() for k in ("grade","evidence_type","evidence_ref","rationale")}
    if not any(values.values()):
        return None
    key = (case["case_id"], option["candidate_id"])
    if values["grade"] not in {"0","1","2"} or not all(values.values()) or values["evidence_type"] not in EVIDENCE:
        raise ValueError(f"{key}: enter a 0–2 grade, a valid evidence type, an exact reference and a rationale.")
    values["grade"] = int(values["grade"])
    if values["grade"] and option_errors(case, option, catalog):
        raise ValueError(f"{key}: a hard constraint violation must receive grade 0.")
    return values


def inspect_reviews(rows, catalog, base=BASE, *, reconcile=False):
    folder = base/"reviews"
    sheets = {name: read_sheet(folder/f"{name}.csv") for name in REVIEWERS}
    resolutions = read_sheet(folder/"reconciliation.csv")
    for name in REVIEWERS:
        expected = {(c["case_id"], o["candidate_id"]) for c in rows if name in c["reviewers"] for o in c["candidate_options"]}
        if expected != sheets[name].keys():
            raise ValueError(f"{name}.csv contains missing or unassigned rows.")
    complete, decisions, conflicts = {}, {}, {}
    completed_by = Counter()
    matching = compared = missing = resolved = 0
    for case in rows:
        cid = case["case_id"]
        labels = {}
        for option in case["candidate_options"]:
            key = (cid, option["candidate_id"])
            ratings = {name: judgment(sheets[name][key], case, option, catalog) for name in case["reviewers"]}
            for name, value in ratings.items():
                completed_by[name] += value is not None
            missing += sum(v is None for v in ratings.values())
            if any(value is None for value in ratings.values()):
                continue
            grades = [value["grade"] for value in ratings.values()]
            if len(grades) == 2:
                compared += 1
                matching += grades[0] == grades[1]
            decision = next(iter(ratings.values()))
            if len(set(grades)) > 1:
                header = {"case_id": cid, "candidate_id": key[1], "Vibhu_grade": str(grades[0]),
                          "Swarit_grade": str(grades[1])}
                old = resolutions.get(key, header)
                if any(old.get(k) != v for k,v in header.items()):
                    raise ValueError(f"Original grades changed for reconciliation row {key}.")
                conflicts[key] = old
                decision = judgment(old, case, option, catalog)
                if decision is None:
                    continue
                resolved += 1
            labels[option_key(option)] = {"judgment": decision, "annotations": ratings}
        decisions[cid] = labels
        complete[cid] = len(labels) == len(case["candidate_options"])
    if resolutions.keys() - conflicts.keys():
        raise ValueError("Reconciliation contains a row without a current disagreement.")
    if reconcile:
        write_text(folder/"reconciliation.csv", "\ufeff" + csv_text(RESOLVE, conflicts.values()))
    progress = {"cases": len(rows), "completed_cases": sum(complete.values()), "missing_ratings": missing,
                "ratings_by_reviewer": dict(completed_by), "double_review_cases": sum(len(c["reviewers"]) == 2 for c in rows),
                "options_compared": compared, "options_agreed": matching,
                "agreement_before_reconciliation": matching/compared if compared else None,
                "disagreements": len(conflicts), "unresolved_disagreements": len(conflicts)-resolved}
    return progress, decisions


def freeze_labels(rows, catalog, base=BASE):
    progress, labels = inspect_reviews(rows, catalog, base)
    if progress["completed_cases"] != len(rows):
        raise ValueError(f"Human review incomplete: {progress['missing_ratings']} missing ratings, "
                         f"{progress['unresolved_disagreements']} unresolved disagreements.")
    payload = {"protocol_sha256": sha256(base/"protocol_lock.json"), "progress": progress, "cases": labels,
               "annotation_sha256": {p.name: sha256(p) for p in sorted((base/"reviews").glob("*.csv"))}}
    path = base/"labels_lock.json"
    if path.exists() and read_json(path) != payload:
        raise ValueError("The existing label freeze differs. Preserve the original experiment.")
    if not path.exists():
        write_json(path, payload)
    return payload


def verified_labels(rows, catalog, base=BASE):
    path = base/"labels_lock.json"
    if not path.exists():
        raise ValueError("Final test evaluation requires frozen, reconciled human grades. Run benchmark.py status.")
    return freeze_labels(rows, catalog, base)

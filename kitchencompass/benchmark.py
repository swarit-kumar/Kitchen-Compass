"""Prepare and verify the Phase 5 frozen cases, pooled options and review assignments."""
import csv
from collections import Counter
from hashlib import sha256 as hash_bytes
from io import StringIO
import json
from random import Random

from .catalog import load_jsonl
from .data_io import ROOT, read_json, sha256, write_json, write_text
from .experiments import option_key, run_case

BASE = ROOT / "data/benchmark/phase5"
TASKS = {"pantry": 25, "single": 35, "joint": 15}
REVIEWERS = ("Vibhu", "Swarit")
PROTOCOL = "P05-v1"
# The frozen protocol includes every implementation or data dependency that can change rankings, pools or metrics.
FIXED_FILES = [
    "config/settings.json", "pyproject.toml", "requirements.txt", "artifacts/context_vectors.json",
    "data/benchmark/splits.json", "data/benchmark/dev_cases.jsonl", "data/curation/substitution_policy.json",
    "scripts/evaluate.py", "scripts/benchmark.py", "scripts/measure_runtime.py",
]
CASE_FILES = ("dev_cases.jsonl", "test_cases.jsonl")


def priority(*parts):
    return hash_bytes("/".join(parts).encode()).hexdigest()


def write_lines(path, records):
    write_text(path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in records))


def csv_text(fields, rows):
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def frozen_files():
    files = list(FIXED_FILES)
    for pattern in ("kitchencompass/*.py", "data/processed/*.json*", "data/raw/*.json"):
        files.extend(p.relative_to(ROOT).as_posix() for p in sorted(ROOT.glob(pattern)))
    return sorted(set(files))


def case_signature(case):
    values = (case["task_type"], tuple(sorted(case["pantry_ids"])), tuple(sorted(case["exclusions"])))
    if case["task_type"] != "pantry":
        values += (case["recipe_id"], tuple(sorted(case["targets"])), case["pantry_only"])
    return values


def make_case(catalog, split, task, recipe, n):
    rid = recipe["recipe_id"]
    rng = Random(priority(PROTOCOL, split, task, rid, str(n)))
    entries = recipe["ingredients"]
    ids = list(dict.fromkeys(e["ingredient_id"] for e in entries))
    essential = list(dict.fromkeys(e["ingredient_id"] for e in entries if e["essential"]))
    alternatives = sorted(set(catalog.ingredients) - set(ids))
    targets, excluded, options = [], [], []
    only = False
    if task == "pantry":
        pantry = rng.sample(ids, min(len(ids), max(2, round(len(ids) * (0.5, 0.7, 0.9)[n % 3]))))
        pantry += rng.sample(alternatives, n % 4)
        if n % 3:
            excluded = [["ing_milk"], ["ing_egg"], ["ing_wheat_flour"]][n % 3 - 1]
        options = [{"recipe_id": rid}]
        prompt = "Find practical recipes given the pantry, missing ingredients and exclusions."
    else:
        size = 1 if task == "single" else 2 + int(n % 4 == 0)
        choices = list(essential)
        rng.shuffle(choices)
        rest = [k for k in ids if k not in choices]
        rng.shuffle(rest)
        targets = (choices + rest)[:size]
        profile_stratum = task == "single" and n % 5 == 0
        if profile_stratum:
            # Use only availability metadata. Neither ranking order nor human grades selects these cases.
            measured = sorted(k for k in ids if catalog.compounds[k])
            targets = [rng.choice(measured)]
        only = n % 4 != 0
        menu = []
        mapping = {}
        for target in targets:
            item = catalog.ingredients[target]
            same_roles = [k for k in alternatives if set(catalog.ingredients[k]["default_roles"]) & set(item["default_roles"])]
            same_category = [k for k in same_roles if catalog.ingredients[k]["category"] == item["category"]]
            near = list(dict.fromkeys(rng.sample(same_category, min(3, len(same_category))) +
                                     rng.sample(same_roles, min(3, len(same_roles)))))
            picks = [k for k in near + alternatives if k not in mapping.values()]
            mapping[target] = picks[0]
            menu.extend(near)
        # A reference option from catalogue roles also exists when every model abstains.
        options = [{"replacements": mapping}]
        pantry = list(dict.fromkeys(menu + rng.sample(alternatives, 2)))
        if n % 7 == 0 and only:
            pantry = rng.sample(alternatives, 1)
        if n % 3 == 1:
            excluded = [targets[0]]
        elif n % 3 == 2:
            excluded = [["ing_milk"], ["ing_egg"], ["ing_wheat_flour"]][(n // 3) % 3]
        if profile_stratum:
            pantry = sorted(set(pantry) | {k for k in alternatives if catalog.compounds[k]})
            excluded = []
        prompt = "Assess replacements for the listed targets using this dish's preparation, pantry and exclusions."
    return {"case_id": f"p5_{split}_{task}_{n:02d}", "task_type": task, "recipe_id": rid,
            "duplicate_group_id": recipe["duplicate_group_id"], "split": split, "targets": targets,
            "pantry_ids": sorted(pantry), "pantry_only": only, "exclusions": excluded, "prompt": prompt,
            "evidence_refs": [{"source_ref": recipe["source_ref"], "locator": f"recipe_id={rid}",
                               "evidence_type": "recipe_context", "note": "Original ingredient lines and preparation steps."}],
            "candidate_options": options, "review_status": "pending_review", "annotator_ids": [],
            "candidate_judgments": [], "independent_review_requested": False}


def construct_cases(catalog):
    splits = read_json(ROOT / "data/benchmark/splits.json")
    rows = load_jsonl(ROOT / "data/benchmark/dev_cases.jsonl")
    seen = {case_signature(r) for r in rows}
    for split in ("dev", "test"):
        recipes = sorted(splits["recipes"][split])
        for task, quota in TASKS.items():
            existing = [r for r in rows if (r["split"], r["task_type"]) == (split, task)]
            counts = Counter(r["duplicate_group_id"] for r in existing)
            used = {r["recipe_id"] for r in existing}
            for n in range(len(existing) + 1, quota + 1):
                ordered = sorted((r for r in recipes if r not in used),
                                 key=lambda r: (counts[catalog.recipes[r]["duplicate_group_id"]], priority(split, task, r)))
                for rid in ordered:
                    if task == "single" and n % 5 == 0:
                        recipe_ids = {e["ingredient_id"] for e in catalog.recipes[rid]["ingredients"]}
                        measured = {k for k,v in catalog.compounds.items() if v}
                        if not (measured & recipe_ids and measured - recipe_ids):
                            continue
                    case = make_case(catalog, split, task, catalog.recipes[rid], n)
                    case["sampling_stratum"] = "measured_flavor" if task == "single" and n % 5 == 0 else "catalogue"
                    signature = case_signature(case)
                    if signature not in seen:
                        break
                else:
                    raise ValueError("No distinct source request remains for this quota.")
                seen.add(signature)
                rows.append(case)
                used.add(rid)
                counts[case["duplicate_group_id"]] += 1
    dual = {r["case_id"] for r in rows if r["independent_review_requested"] or
            (r["task_type"] == "joint" and r["split"] == "test")}
    for r in sorted(rows, key=lambda r: priority("dual", r["case_id"])):
        if len(dual) >= (len(rows)*3 + 9)//10:
            break
        dual.add(r["case_id"])
    single_index = 0
    for r in rows:
        r.setdefault("sampling_stratum", "original_development")
        key = r["case_id"]
        r["reviewers"] = list(REVIEWERS) if key in dual else [REVIEWERS[single_index % 2]]
        single_index += key not in dual
        options = {}
        for o in r.pop("candidate_options"):
            option = {k: v for k, v in o.items() if k != "candidate_id"}
            options[option_key(option)] = option
        for method in run_case(r, catalog)["methods"]:
            for item in method["items"]:
                options[option_key(item["option"])] = item["option"]
        r["candidate_options"] = [{"candidate_id": f"o{i:02d}", **options[k]} for i, k in
                                  enumerate(sorted(options, key=lambda k: priority(key, k)), 1)]
        r["independent_review_requested"] = key in dual
    return rows


def validate_cases(rows, catalog):
    splits = read_json(ROOT / "data/benchmark/splits.json")
    if len({c["case_id"] for c in rows}) != len(rows) or len({case_signature(c) for c in rows}) != len(rows):
        raise ValueError("Duplicate case identity or request.")
    counts = Counter((c["split"], c["task_type"]) for c in rows)
    if counts != {(s,t): n for s in ("dev","test") for t,n in TASKS.items()}:
        raise ValueError("Case counts disagree with the preregistered design.")
    dual = 0
    for c in rows:
        rid, group, split = c["recipe_id"], c["duplicate_group_id"], c["split"]
        if (rid not in splits["recipes"][split] or group not in splits["groups"][split]
                or catalog.recipes[rid]["duplicate_group_id"] != group):
            raise ValueError(f"Source split mismatch in {c['case_id']}")
        reviewers = c["reviewers"]
        if reviewers not in ([REVIEWERS[0]], [REVIEWERS[1]], list(REVIEWERS)):
            raise ValueError("Unknown reviewer assignment.")
        dual += len(reviewers) == 2
        if split == "test" and c["task_type"] == "joint" and len(reviewers) != 2:
            raise ValueError("Joint test case needs both reviewers.")
        options = c["candidate_options"]
        if (not options or len({o["candidate_id"] for o in options}) != len(options)
                or len({option_key(o) for o in options}) != len(options)):
            raise ValueError("Incomplete or duplicated judgment pool.")
    if dual * 10 < 3 * len(rows):
        raise ValueError("Insufficient independent overlap.")


def stamp(base=BASE):
    return {"protocol": PROTOCOL, "inputs": {name: sha256(ROOT/name) for name in frozen_files()},
            "cases": {name: sha256(base/name) for name in CASE_FILES}}


def verify_protocol(base=BASE):
    if read_json(base/"protocol_lock.json") != stamp(base):
        raise ValueError("Frozen inputs changed. Restore this checkpoint or start a separately identified experiment.")


def create_protocol(catalog, base=BASE):
    if (base/"protocol_lock.json").exists():
        verify_protocol(base)
        return
    rows = construct_cases(catalog)
    validate_cases(rows, catalog)
    for split, name in zip(("dev", "test"), CASE_FILES):
        write_lines(base/name, [r for r in rows if r["split"] == split])
    write_json(base/"protocol_lock.json", stamp(base))

"""Case-level measurements and deterministic recipe-group bootstrap summaries."""
from collections import defaultdict
from math import log2
from random import Random
from statistics import mean

from .experiments import option_key

QUALITY = ("ndcg_at_5", "hit_at_3", "mrr_at_5", "top3_mean_grade", "candidate_generation_recall", "grade2_hit_at_3")
OPERATIONAL = ("abstention", "mean_missing_items", "joint_score_difference")


def dcg(grades):
    return sum((2**grade - 1) / log2(rank + 2) for rank, grade in enumerate(grades[:5]))


def measure_case(case, labels=None):
    """Missing judgments are unknown. Compute quality only on the frozen rated pool."""
    grades = None if labels is None else {k: v["judgment"]["grade"] for k,v in labels.items()}
    task, audit = case["task_type"], case["audit"]
    for method in case["methods"]:
        name, items = method["method"], method["items"]
        keys = [option_key(item["option"]) for item in items]
        complete = method["population"] == "complete_evidence"
        candidate_ids = audit.get("complete_evidence_ids" if complete else "candidate_ids", [])
        eligible_keys = ({option_key({"replacements": {case["targets"][0]: k}}) for k in candidate_ids}
                         if task == "single" else set())
        m = {"included": not complete or bool(candidate_ids), "returned": len(items),
             "abstention": int(not items), "violations": sum(bool(i["errors"]) for i in items),
             "unknown_pair_evidence": sum(bool(i.get("unknown_pair_evidence")) for i in items),
             "duplicate_replacements": sum(bool(i.get("duplicate_replacement")) for i in items),
             "candidates_before_scoring": len(candidate_ids) if task == "single" else None,
             "mean_missing_items": mean(i["missing_count"] for i in items) if items and task == "pantry" else None,
             "joint_score_difference": None, **dict.fromkeys(QUALITY)}
        method["measures"] = m
        if not m["included"] or grades is None:
            continue
        if any(key not in grades for key in keys):
            raise ValueError(f"Returned option outside frozen judgment pool: {case['case_id']}")
        ranked = [grades[key] for key in keys]
        if task == "pantry":
            ideal = dcg(sorted(grades.values(), reverse=True))
            m["ndcg_at_5"] = dcg(ranked)/ideal if ideal else None
        elif task == "single":
            relevant = {k for k,v in grades.items() if v == 2}
            if complete:
                relevant &= eligible_keys
            if relevant:
                m["hit_at_3"] = int(bool(relevant.intersection(keys[:3])))
                m["mrr_at_5"] = next((1/i for i,k in enumerate(keys[:5], 1) if k in relevant), 0)
                m["candidate_generation_recall"] = len(relevant & eligible_keys)/len(relevant)
            if ranked:
                m["top3_mean_grade"] = mean(ranked[:3])
        else:
            m["grade2_hit_at_3"] = int(2 in ranked[:3])
    if task == "joint":
        joint, independent = case["methods"]
        if joint["items"] and independent["items"] and independent["items"][0]["score"] is not None:
            joint["measures"]["joint_score_difference"] = joint["items"][0]["score"] - independent["items"][0]["score"]
    return case


def group_interval(values):
    groups = defaultdict(list)
    for group, value in values:
        groups[group].append(value)
    if len(groups) < 5:
        return None
    stats = [(sum(v), len(v)) for _,v in sorted(groups.items())]
    rng = Random(42)
    replicates = []
    for _ in range(1000):
        sample = rng.choices(stats, k=len(stats))
        replicates.append(sum(x[0] for x in sample) / sum(x[1] for x in sample))
    replicates.sort()
    return [replicates[24], replicates[974]]


def summarize_cases(cases):
    sets = defaultdict(list)
    for c in cases:
        for method in c["methods"]:
            sets[c["task_type"], method["method"], method["population"]].append((c["duplicate_group_id"], method["measures"]))
    summaries = []
    for (task, name, population), declared in sorted(sets.items()):
        rows = [(group,m) for group,m in declared if m["included"]]
        returned = sum(m["returned"] for _,m in rows)
        violations = sum(m["violations"] for _,m in rows)
        entry = {"task_type": task, "method": name, "population": population, "declared_cases": len(declared),
                 "evaluated_cases": len(rows), "groups": len({g for g,_ in rows}),
                 "items_returned": returned, "cases_with_results": sum(bool(m["returned"]) for _,m in rows),
                 "constraint_violations": violations, "violation_rate": violations/returned if returned else None,
                 "duplicate_replacements": sum(m["duplicate_replacements"] for _,m in rows),
                 "unknown_pair_evidence": sum(m["unknown_pair_evidence"] for _,m in rows), "metrics": {}}
        for metric in (*QUALITY, *OPERATIONAL):
            eligible = [(g,m[metric]) for g,m in rows if m[metric] is not None]
            entry["metrics"][metric] = {"mean": mean(v for _,v in eligible) if eligible else None,
                                        "eligible_cases": len(eligible), "group_ci95": group_interval(eligible)}
        summaries.append(entry)
    return summaries

"""Reproduce Phase 2–4 development comparisons from the frozen recipe split."""
from statistics import mean

from kitchencompass.catalog import load_jsonl
from kitchencompass.data_io import ROOT, read_json, write_json
from kitchencompass.schemas import Constraints
from kitchencompass.service import recommend_recipes, rank_substitutes
from kitchencompass.substitute import MODES


def verified_grades(row, target):
    """Only reconciled, fully judged option pools support quality measurements."""
    if row["review_status"] not in {"reconciled", "accepted"} or not row["annotator_ids"]:
        return None
    options = {o["candidate_id"]: o["replacements"][target] for o in row["candidate_options"]}
    judgments = {j["candidate_id"]: j["grade"] for j in row["candidate_judgments"]}
    if set(options) != set(judgments) or any(type(v) is not int or v not in (0, 1, 2) for v in judgments.values()):
        raise ValueError(f"Incomplete or invalid reconciled grades in {row['case_id']}")
    return {key: judgments[option] for option, key in options.items()}


def summarize(cases, mode, comparison):
    selected = [case for case in cases if comparison != "complete_evidence" or case["audit"]["complete_evidence_ids"]]
    hits, reciprocals, recall, plausibility = [], [], [], []
    returned = violations = candidates = emitted = 0
    for case in selected:
        result = case[comparison][mode]
        ranked = [item["candidate_id"] for item in result["items"]]
        pool = case["audit"]["complete_evidence_ids" if comparison == "complete_evidence" else "candidate_ids"]
        returned += bool(ranked)
        candidates += len(pool)
        emitted += len(ranked)
        violations += sum(key not in case["independent_allowed_ids"] for key in ranked)
        grades = case["grades"]
        if grades is None or any(key not in grades for key in ranked):
            continue
        relevant = {key for key, grade in grades.items() if grade == 2}
        if comparison == "complete_evidence":
            relevant.intersection_update(pool)
        if not relevant:
            continue
        hits.append(int(bool(set(ranked[:3]) & relevant)))
        reciprocals.append(next((1 / n for n, key in enumerate(ranked, 1) if key in relevant), 0))
        recall.append(len(relevant.intersection(pool)) / len(relevant))
        plausibility.extend(grades[key] for key in ranked[:3])
    return {"cases": len(selected), "cases_with_results": returned, "candidates_before_role_filter": candidates,
            "suggestions_returned": emitted, "abstentions": len(selected) - returned,
            "abstention_rate": (1 - returned / len(selected)) if selected else None,
            "hard_constraint_violations": violations, "quality_eligible_cases": len(hits),
            "hit_at_3": mean(hits) if hits else None, "mrr_at_5": mean(reciprocals) if reciprocals else None,
            "candidate_generation_recall": mean(recall) if recall else None,
            "mean_human_grade_of_returned_top_3": mean(plausibility) if plausibility else None}


def evaluate(catalog, rows, dev_ids):
    pantry_cases, singles = [], []
    for row in rows:
        if row["split"] != "dev" or row["recipe_id"] not in dev_ids:
            raise ValueError("Only development source recipes are eligible for this report.")
        constraints = Constraints(pantry_ids=row["pantry_ids"], excluded_ids=row["exclusions"], pantry_only=row["pantry_only"])
        if row["task_type"] == "pantry":
            pantry_cases.append({"case_id": row["case_id"], "review_status": row["review_status"],
                                "methods": {m: recommend_recipes(constraints.pantry_ids, constraints, mode=m, catalog=catalog).model_dump()
                                            for m in ("overlap", "weighted")}})
        if row["task_type"] != "single":
            continue
        target, = row["targets"]
        recipe = catalog.recipes[row["recipe_id"]]
        # Independent check of final ingredient sets, using forward component traversal.
        forbidden = set(constraints.excluded_ids)
        def has_excluded_component(key, seen):
            if key in forbidden:
                return True
            if key in seen:
                return False
            return any(has_excluded_component(child, seen | {key}) for child in catalog.ingredients[key]["components"])

        original = {i["ingredient_id"] for i in recipe["ingredients"]}
        allowed = {key for key in catalog.ingredients if key not in original and not has_excluded_component(key, set())
                   and (not constraints.pantry_only or key in constraints.pantry_ids)}
        if any(has_excluded_component(key, set()) for key in original - {target}):
            allowed.clear()
        audit = {"candidate_ids": [], "complete_evidence_ids": [], "blocked_pair_ids": []}
        case = {"case_id": row["case_id"], "recipe_id": row["recipe_id"], "target_id": target,
                "constraints": constraints.model_dump(), "review_status": row["review_status"],
                "grades": verified_grades(row, target), "audit": audit, "independent_allowed_ids": sorted(allowed)}
        for comparison in ("all_evidence", "complete_evidence"):
            case[comparison] = {}
            for mode in MODES:
                res = rank_substitutes(row["recipe_id"], target, constraints, mode=mode, catalog=catalog,
                                       complete_only=comparison == "complete_evidence",
                                       audit=audit if mode == "full" and comparison == "all_evidence" else None)
                case[comparison][mode] = res.model_dump()
        case["independent_allowed_ids"] = sorted(allowed - set(audit["blocked_pair_ids"]))
        singles.append(case)
    meta = {**catalog.versions, "split": "dev", "split_id": catalog.split_id}
    report = {**meta, "quality_note": "Null means no eligible graded cases. Common comparisons restrict all methods to candidates with F, C and R measured. Each reported quality case has a grade-2 option; misses and abstentions contribute zero.",
              "summaries": {key: {m: summarize(singles, m, key) for m in MODES}
                            for key in ("all_evidence", "complete_evidence")}, "cases": singles}
    return {**meta, "cases": pantry_cases}, report


def publish_reports(catalog):
    from .joint_evaluation import evaluate_joint
    dev_ids = set(read_json(ROOT / "data/benchmark/splits.json")["recipes"]["dev"])
    rows = load_jsonl(ROOT / "data/benchmark/dev_cases.jsonl")
    pantry, singles = evaluate(catalog, rows, dev_ids)
    joint = evaluate_joint(catalog, rows, dev_ids)
    write_json(ROOT / "results/development_joint_plans.json", joint)
    write_json(ROOT / "results/development_pantry.json", pantry)
    write_json(ROOT / "results/development_substitution.json", singles)
    return joint, singles

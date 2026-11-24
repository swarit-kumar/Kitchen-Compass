"""Evaluate each published joint development case, including abstentions."""
from statistics import mean

from kitchencompass.adapt import validate_plan
from kitchencompass.schemas import Constraints
from kitchencompass.service import adapt_recipe


def graded_hit(row, plans):
    if row["review_status"] not in {"reconciled", "accepted"} or not row["annotator_ids"]:
        return None
    judgments = {j["candidate_id"]: j["grade"] for j in row["candidate_judgments"]}
    options = row["candidate_options"]
    if ({o["candidate_id"] for o in options} != judgments.keys()
            or any(type(g) is not int or g not in (0, 1, 2) for g in judgments.values())):
        raise ValueError(f"Incomplete grades for {row['case_id']}")
    grades = {tuple(sorted(o["replacements"].items())): judgments[o["candidate_id"]] for o in options}
    keys = [tuple(sorted(p["replacements"].items())) for p in plans]
    if any(key not in grades for key in keys):
        return None
    return int(any(grades[key] == 2 for key in keys))


def evaluate_joint(catalog, rows, dev_ids):
    cases = []
    seen = set()
    for row in rows:
        if row["task_type"] != "joint":
            continue
        recipe_id, case_id = row["recipe_id"], row["case_id"]
        if row["split"] != "dev" or recipe_id not in dev_ids or case_id in seen:
            raise ValueError(f"Duplicate or non-development joint case: {case_id}")
        recipe = catalog.recipes[recipe_id]
        if recipe["duplicate_group_id"] != row["duplicate_group_id"]:
            raise ValueError(f"Recipe group mismatch for {case_id}")
        seen.add(case_id)
        constraints = Constraints(pantry_ids=row["pantry_ids"], excluded_ids=row["exclusions"],
                                  pantry_only=row["pantry_only"])
        audit = {}
        result = adapt_recipe(recipe_id, row["targets"], constraints, catalog=catalog, audit=audit)
        baseline = audit.pop("baseline")
        checks = [validate_plan(recipe, row["targets"], p, constraints, catalog) for p in result.items]
        best = result.items[0]["score"] if result.items else None
        independent = baseline.get("joint_score") if baseline else None
        cases.append({"case_id": case_id, "recipe_id": recipe_id, "duplicate_group_id": row["duplicate_group_id"],
                      "target_ids": row["targets"], "constraints": constraints.model_dump(), "prompt": row["prompt"],
                      "review_status": row["review_status"], "annotator_ids": row["annotator_ids"],
                      "audit": audit, "result": result.model_dump(), "independent": baseline,
                      "plan_violations": sum(not c["valid"] for c in checks),
                      "score_difference": best - independent if best is not None and independent is not None else None,
                      "grade_2_hit_at_3": graded_hit(row, result.items)})
    plans = [p for c in cases for p in c["result"]["items"]]
    comparable = [c["score_difference"] for c in cases if c["score_difference"] is not None]
    hits = [c["grade_2_hit_at_3"] for c in cases if c["grade_2_hit_at_3"] is not None]
    baselines = [c["independent"] for c in cases if c["independent"] and c["independent"]["replacement_ids"]]
    violations = sum(c["plan_violations"] for c in cases)
    return {**catalog.versions, "split": "dev", "split_id": catalog.split_id,
            "quality_note": "Quality requires reconciled human grades. Score differences compare feasible plans on the same joint objective.",
            "summary": {"cases": len(cases), "abstentions": sum(not c["result"]["items"] for c in cases),
                        "plans_returned": len(plans), "constraint_violations": violations,
                        "violation_rate": violations / len(plans) if plans else None,
                        "independent_valid": sum(b["valid"] for b in baselines),
                        "independent_invalid": sum(not b["valid"] for b in baselines),
                        "independent_abstentions": len(cases) - len(baselines),
                        "independent_duplicate_failures": sum(len(set(b["replacement_ids"])) < len(b["replacement_ids"]) for b in baselines),
                        "plans_with_unknown_pair_evidence": sum(any(d["unknown_evidence"] for d in p["pair_details"]) for p in plans),
                        "quality_eligible_cases": len(hits), "grade_2_hit_at_3": mean(hits) if hits else None,
                        "comparable_cases": len(comparable), "mean_score_difference": mean(comparable) if comparable else None},
            "cases": cases}

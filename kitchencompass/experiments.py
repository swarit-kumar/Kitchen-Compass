"""Run the declared methods on the same case and independently inspect their outputs."""
from .adapt import validate_plan
from .schemas import Constraints
from .service import adapt_recipe, rank_substitutes, recommend_recipes
from .substitute import MODES


def option_key(option):
    if "recipe_id" in option:
        return option["recipe_id"]
    return "|".join(f"{a}={b}" for a, b in sorted(option["replacements"].items()))


def constraints_for(case):
    return Constraints(pantry_ids=case["pantry_ids"], excluded_ids=case["exclusions"],
                       pantry_only=case["pantry_only"])


def option_errors(case, option, catalog):
    """Reconstruct the dish from the proposed choice independently of its reported status."""
    if case["task_type"] == "pantry":
        recipe = catalog.recipes[option["recipe_id"]]
        forbidden = set(case["exclusions"])
        visited = set()
        pending = [entry["ingredient_id"] for entry in recipe["ingredients"]]
        while pending:
            key = pending.pop()
            if key in forbidden:
                return ["Final recipe contains an excluded ingredient."]
            if key not in visited:
                visited.add(key)
                pending.extend(catalog.ingredients[key]["components"])
        return []
    mapping = option["replacements"]
    plan = {"target_ids": list(mapping), "replacement_ids": list(mapping.values())}
    return validate_plan(catalog.recipes[case["recipe_id"]], case["targets"], plan,
                         constraints_for(case), catalog)["errors"]


def run_case(case, catalog):
    recipe, targets = case["recipe_id"], case["targets"]
    constraints = constraints_for(case)
    methods = []
    audit = {}

    def record(name, population, status, items, warnings=(), reasons=None):
        for item in items:
            item["errors"] = option_errors(case, item["option"], catalog)
        methods.append({"method": name, "population": population, "status": status,
                        "items": items, "warnings": list(warnings), "filter_counts": reasons or {}})

    if case["task_type"] == "pantry":
        for mode in ("overlap", "weighted"):
            result = recommend_recipes(constraints.pantry_ids, constraints, top_k=5, mode=mode, catalog=catalog)
            items = []
            for item in result.items:
                key = item["recipe_id"]
                missing = {e["ingredient_id"] for e in catalog.recipes[key]["ingredients"]} - set(constraints.pantry_ids)
                items.append({"option": {"recipe_id": key}, "score": item["score"], "missing_count": len(missing)})
            record(mode, "all", result.status, items, result.warnings, result.reason_counts)
    elif case["task_type"] == "single":
        for complete in (False, True):
            for mode in MODES:
                result = rank_substitutes(recipe, targets[0], constraints, top_k=5, mode=mode, catalog=catalog,
                                          complete_only=complete, audit=audit if not complete and mode=="full" else None)
                items = [{"option": {"replacements": {targets[0]: item["candidate_id"]}},
                          "score": item["score"], "components": item["component_scores"],
                          "partial_evidence": item["partial_evidence"]} for item in result.items]
                record(mode, "complete_evidence" if complete else "all", result.status,
                       items, result.warnings, result.reason_counts)
    else:
        result = adapt_recipe(recipe, targets, constraints, top_k=3, catalog=catalog, audit=audit)
        baseline = audit.pop("baseline")
        audit.pop("target_diagnostics", None)
        items = [{"option": {"replacements": plan["replacements"]}, "score": plan["score"],
                  "components": plan["component_scores"], "purchase_ids": plan["purchase_ids"],
                  "unknown_pair_evidence": any(p["unknown_evidence"] for p in plan["pair_details"])}
                 for plan in result.items]
        record("joint", "all", result.status, items, result.warnings, result.reason_counts)
        items = []
        if baseline and baseline["replacement_ids"]:
            from itertools import combinations
            from .adapt import target_role_context, pair_compatibility_score
            roles = [target_role_context(catalog.recipes[recipe], t, catalog)["roles"] for t in targets]
            ids = baseline["replacement_ids"]
            unknown = any(pair_compatibility_score(ids[i], ids[j], catalog, roles[i] | roles[j])["warning"]
                          for i, j in combinations(range(len(ids)), 2) if ids[i] != ids[j])
            items.append({"option": {"replacements": baseline["replacements"]}, "score": baseline["joint_score"],
                          "individual_mean": baseline["score"], "unknown_pair_evidence": unknown,
                          "duplicate_replacement": len(set(ids)) != len(ids)})
        status = ("OK" if baseline["valid"] else "INVALID_SELECTION") if items else result.status
        record("independent", "all", status, items, baseline["violations"] if baseline else result.warnings)
    return {"case_id": case["case_id"], "split": case["split"], "task_type": case["task_type"],
            "recipe_id": recipe, "duplicate_group_id": case["duplicate_group_id"],
            "sampling_stratum": case["sampling_stratum"], "constraints": constraints.model_dump(), "targets": targets, "audit": audit, "methods": methods}

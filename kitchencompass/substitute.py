"""Single-target ingredient substitution on the shared, constrained candidate set."""
from collections import Counter

from .features import cosine, flavor_jaccard, mean_context, weighted_score
from .roles import contains, infer_roles, role_match, target_clauses
from .schemas import Result


MODES = {"full": ("F", "C", "R"), "flavor_only": ("F",),
         "without_context": ("F", "R"), "without_roles": ("F", "C")}


def directed_blocks(catalog, target_id, role_info, clauses):
    pair_blocks = {}
    for rule in catalog.pairs:
        if (rule["original_id"] == target_id and rule["review_status"] in {"source_checked", "reviewed"}
                and (not rule["applicable_roles"] or set(role_info["roles"]).intersection(rule["applicable_roles"]))
                and any(contains(clause, phrase) for clause in clauses for phrase in rule["blocked_contexts"])):
            pair_blocks[rule["candidate_id"]] = rule["evidence_ref"]
    return pair_blocks


def constrained_pool(catalog, target_id, retained, constraints, expanded, role_info, clauses):
    pantry = set(constraints.pantry_ids)
    counts = Counter()
    pair_blocks = directed_blocks(catalog, target_id, role_info, clauses)
    candidates = []
    for key in sorted(catalog.ingredients):
        if key == target_id or key in retained:
            counts["original_or_retained"] += 1
        elif key in expanded:
            counts["excluded_ingredient"] += 1
        elif constraints.pantry_only and key not in pantry:
            counts["outside_pantry"] += 1
        elif key in pair_blocks:
            counts["blocked_pair"] += 1
        else:
            candidates.append(key)
    return candidates, counts, pair_blocks


def rank(catalog, recipe, target_id, constraints, top_k, mode, complete_only=False, audit=None, *, other_targets=()):
    """Rank all qualifying replacements when top_k is None."""
    if mode not in MODES:
        raise ValueError(f"Unknown substitution method: {mode}")
    if top_k is not None and top_k < 1:
        raise ValueError("top_k must be at least one")
    versions = catalog.versions
    ids = {entry["ingredient_id"] for entry in recipe["ingredients"]}
    if target_id not in ids:
        return Result(status="NEEDS_INPUT", warnings=["Choose a target ingredient present in this recipe."], **versions)
    retained = ids - {target_id} - set(other_targets)
    expanded = set(catalog.constraints.expand_exclusions(constraints.excluded_ids))
    conflicts = sorted(retained & expanded)
    if conflicts:
        names = ", ".join(catalog.ingredients[key]["display_name"] for key in conflicts)
        return Result(status="UNRESOLVED_EXCLUSION", warnings=[f"Retained ingredients conflict with your exclusions: {names}. A single replacement cannot resolve this request."],
                      reason_counts={"retained_exclusions": len(conflicts)}, **versions)
    target = catalog.ingredients[target_id]
    clauses = target_clauses(recipe, target_id, catalog.ingredients, catalog.policy["shorthand"])
    role = infer_roles(target, catalog.rules, clauses)
    pool, counts, blocked = constrained_pool(catalog, target_id, retained | set(other_targets), constraints, expanded, role, clauses)
    context = mean_context(retained, catalog.vectors)
    settings = catalog.config["substitution"]
    items = []
    if audit is not None:
        audit.update(candidate_ids=list(pool), complete_evidence_ids=[], blocked_pair_ids=sorted(blocked))
    warnings = list(role["warnings"])
    if not recipe["instructions"]:
        warnings.append("No instructions supplied. The target uses its catalogue roles.")
    if blocked:
        warnings.append("Applicable instruction-based pair blocks: " + ", ".join(catalog.ingredients[key]["display_name"] for key in sorted(blocked)))
    for key in pool:
        candidate = catalog.ingredients[key]
        r, match = role_match(role["roles"], candidate, recipe.get("dish_family"), catalog.policy["partial_matches"])
        parts = {"F": flavor_jaccard(catalog.compounds[target_id], catalog.compounds[key]),
                 "C": cosine(catalog.vectors[key], context), "R": r}
        if audit is not None and None not in parts.values():
            audit["complete_evidence_ids"].append(key)
        if complete_only and None in parts.values():
            counts["incomplete_evidence"] += 1
            continue
        active = MODES[mode]
        if "R" in active and (r is None or r < settings["min_role"]):
            counts["incompatible_or_missing_role"] += 1
            continue
        if not any(parts[k] is not None for k in active if k != "R"):
            counts["missing_evidence"] += 1
            continue
        score = weighted_score(parts, settings["weights"], active)
        # The pure flavor baseline ranks every measured F, including zero.
        if mode != "flavor_only" and score < settings["min_score"]:
            counts["below_threshold"] += 1
            continue
        reasons = []
        if "R" in active:
            role_origin = ("instruction rule " + ", ".join(role["rule_ids"])) if role["rule_ids"] else "catalogue default"
            reasons.append(f"Role ({role_origin}): {match['target_role']} → {match['candidate_role']}. {match['basis']}.")
        if "C" in active:
            reasons.append(f"Training-context cosine against {len(retained)} retained ingredients: {parts['C']:.3f}."
                           if parts["C"] is not None else "Context unavailable: the candidate or recipe has a zero vector.")
        if "F" in active:
            shared = len(catalog.compounds[target_id] & catalog.compounds[key])
            union = len(catalog.compounds[target_id] | catalog.compounds[key])
            reasons.append(f"FlavorDB overlap: {shared} shared compounds out of {union} distinct compounds."
                           if parts["F"] is not None else "Flavor unavailable: one or both molecular profiles are missing.")
        used = [k for k in active if parts[k] is not None]
        items.append({"candidate_id": key, "name": candidate["display_name"], "score": score,
                      "mode": mode, "component_scores": parts, "used_features": used,
                      "evidence_available": {k: v is not None for k, v in parts.items()},
                      "partial_evidence": len(used) != len(active), "role_evidence": role, "role_match": match,
                      "flavor_sources": sorted(set(catalog.profiles[target_id].source_refs + catalog.profiles[key].source_refs)) if parts["F"] is not None else [],
                      "context_split": catalog.split_id, "reasons": reasons, "purchase_required": key not in constraints.pantry_ids})
    items.sort(key=lambda item: (-item["score"], item["candidate_id"]))
    if not items:
        warnings.append("No candidate meets this method’s constraints and evidence requirements.")
    return Result(status="OK" if items else "NO_FEASIBLE_RESULT", items=items if top_k is None else items[:min(top_k, 5)],
                  warnings=warnings, reason_counts=dict(counts), **versions)

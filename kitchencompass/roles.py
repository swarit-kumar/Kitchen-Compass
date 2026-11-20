"""Infer roles from instructions that explicitly mention the target."""
import re
from collections import defaultdict


def contains(text, phrase):
    return re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", text.casefold()) is not None


def target_clauses(recipe, target_id, ingredients, shorthand):
    """Longest ingredient name wins. Ambiguous recipe-local shorthands are ignored."""
    names = defaultdict(set)
    for entry in recipe["ingredients"]:
        key = entry["ingredient_id"]
        item = ingredients[key]
        for name in [item["display_name"], *item["aliases"], *shorthand.get(key, [])]:
            names[name.casefold()].add(key)
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in sorted(names, key=lambda n: (-len(n), n))) + r")(?!\w)")
    clauses = []
    for step in recipe["instructions"]:
        for clause in re.split(r"[.;!?\n]|\bthen\b|,\s*(?=(?:add|pour|stir|whisk|fold|heat|simmer|boil|finish|season|cream)\b)", step, flags=re.IGNORECASE):
            if any(names[m.group()] == {target_id} for m in pattern.finditer(clause.casefold())):
                clauses.append(clause.strip(" ,"))
    return clauses


def infer_roles(ingredient, rules, clauses):
    matches = []
    for rule in rules:
        exact = ingredient["ingredient_id"] in rule["ingredient_ids"]
        if not exact and ingredient["category"] not in rule["categories"]:
            continue
        for clause in clauses:
            if any(contains(clause, keyword) for keyword in rule["action_keywords"]):
                matches.append(((int(exact), rule["priority"]), rule, clause))
    if not matches:
        return {"roles": sorted(ingredient["default_roles"]), "rule_ids": [], "clauses": [], "warnings": []}
    best = max(priority for priority, _, _ in matches)
    winners = [(rule, clause) for priority, rule, clause in matches if priority == best]
    roles = sorted({rule["role"] for rule, _ in winners})
    return {"roles": roles, "rule_ids": sorted({rule["rule_id"] for rule, _ in winners}),
            "clauses": sorted({clause for _, clause in winners}),
            "warnings": ["Equally specific instruction rules indicate different roles: " + ", ".join(roles)]
            if len(roles) > 1 else []}


def role_match(target_roles, candidate, family, partial_matches):
    candidate_roles = candidate["default_roles"]
    if not target_roles or not candidate_roles:
        return None, None
    exact = sorted(set(target_roles) & set(candidate_roles))
    if exact:
        return 1.0, {"target_role": exact[0], "candidate_role": exact[0], "basis": "same role"}
    for rule in partial_matches:
        if (rule["review_status"] in {"source_checked", "reviewed"} and rule["target_role"] in target_roles and rule["candidate_role"] in candidate_roles
                and candidate["ingredient_id"] in rule["candidate_ids"] and family in rule["families"]):
            return 0.5, {"target_role": rule["target_role"], "candidate_role": rule["candidate_role"],
                         "basis": rule["note"], "evidence_ref": rule["evidence_ref"]}
    return 0.0, None

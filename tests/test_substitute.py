from copy import deepcopy
from math import sqrt

import pytest

from kitchencompass.custom_recipes import create_custom_recipe
from kitchencompass.features import cosine, flavor_jaccard, mean_context, weighted_score
from kitchencompass.roles import infer_roles, role_match, target_clauses
from kitchencompass.schemas import Constraints
from kitchencompass.service import get_catalog, rank_substitutes


MASALA = "rec_capsicum_and_paneer_masala"
SOUP = "rec_lemon_coriander_soup"


def pantry(*names, excluded=()):
    return Constraints(pantry_ids=["ing_" + n for n in names], excluded_ids=["ing_" + n for n in excluded], pantry_only=True)


def test_hand_calculated_features_and_renormalization():
    assert flavor_jaccard({1, 2}, {2, 3}) == pytest.approx(1 / 3)
    assert flavor_jaccard({1}, {2}) == 0
    assert flavor_jaccard(set(), {1}) is None
    vectors = {"a": {"x": 2}, "b": {"y": 2}, "z": {}}
    mean = mean_context(["a", "b", "b"], vectors)
    assert mean == {"x": 1, "y": 1}
    assert cosine(vectors["a"], mean) == pytest.approx(1 / sqrt(2))
    assert cosine({}, mean) is None and cosine(vectors["a"], vectors["b"]) == 0
    assert mean_context([], vectors) == {}
    assert weighted_score({"F": None, "C": 0.5, "R": 1.0}, {"F": .35, "C": .35, "R": .30},
                          ("F", "C", "R")) == pytest.approx(.475 / .65)


def test_instruction_rules_need_the_target_in_the_same_clause_and_resolve_ties():
    cat = get_catalog()
    coconut = cat.ingredients["ing_coconut_milk"]
    entries = [{"ingredient_id": "ing_coconut_milk"}, {"ingredient_id": "ing_milk"}]
    recipe = {"ingredients": entries, "instructions": ["Simmer milk. Pour in coconut milk."]}
    clauses = target_clauses(recipe, "ing_coconut_milk", cat.ingredients, {})
    assert infer_roles(coconut, cat.rules, clauses)["roles"] == ["fat", "liquid"]
    assert target_clauses(recipe, "ing_milk", cat.ingredients, {}) == ["Simmer milk"]
    recipe["instructions"] = ["Simmer milk, pour in coconut milk."]
    assert infer_roles(coconut, cat.rules, target_clauses(recipe, "ing_coconut_milk", cat.ingredients, {}))["rule_ids"] == []
    recipe["instructions"] = ["Simmer coconut milk."]
    clauses = target_clauses(recipe, "ing_coconut_milk", cat.ingredients, {})
    hit = infer_roles(coconut, cat.rules, clauses)
    assert hit["rule_ids"] == ["coconut_milk_simmer"] and hit["roles"] == ["liquid"]
    rule = next(r for r in cat.rules if r["rule_id"] == "coconut_milk_simmer")
    tied = infer_roles(coconut, [rule, dict(rule, rule_id="fixture", role="fat")], clauses)
    assert tied["roles"] == ["fat", "liquid"] and tied["warnings"]
    general = dict(rule, rule_id="category", role="fat", ingredient_ids=[], categories=["liquid"], priority=100)
    assert infer_roles(coconut, [general, rule], clauses)["roles"] == ["liquid"]


def test_partial_role_is_scoped_to_recipe_family_and_candidate():
    cat = get_catalog()
    policy = cat.policy["partial_matches"]
    assert role_match(["thickener"], cat.ingredients["ing_potato"], "soup", policy)[0] == .5
    assert role_match(["thickener"], cat.ingredients["ing_potato"], "curry", policy)[0] == 0
    assert role_match(["thickener"], cat.ingredients["ing_carrot"], "soup", policy)[0] == 0
    pending = [dict(rule, review_status="pending") for rule in policy]
    assert role_match(["thickener"], cat.ingredients["ing_potato"], "soup", pending)[0] == 0
    assert role_match([], cat.ingredients["ing_potato"], "soup", policy)[0] is None


def test_single_target_hard_filters_nested_exclusions_and_originals():
    res = rank_substitutes(MASALA, "ing_paneer", pantry("paneer", "garlic", "firm_tofu", "cheddar", "ghee", excluded=["milk"]))
    assert [r["candidate_id"] for r in res.items] == ["ing_firm_tofu"]
    item, = res.items
    assert not item["purchase_required"] and item["evidence_available"] == {"F": False, "C": True, "R": True}
    assert item["score"] == pytest.approx((.35 * item["component_scores"]["C"] + .3) / .65)
    assert (res.data_version, res.config_version) == ("2.0", "0.4.0")
    assert all(key != "F" for key in item["used_features"])


@pytest.mark.parametrize("target,constraints,status", [
    ("ing_cheddar", Constraints(), "NEEDS_INPUT"),
    ("ing_paneer", pantry("firm_tofu", excluded=["garlic"]), "UNRESOLVED_EXCLUSION"),
    ("ing_paneer", pantry("firm_tofu", excluded=["unlisted"]), "UNRESOLVED_EXCLUSION"),
    ("ing_paneer", pantry("unlisted"), "UNSUPPORTED_INPUT"),
    ("ing_paneer", pantry("cheddar", excluded=["milk"]), "NO_FEASIBLE_RESULT"),
    ("ing_paneer", pantry(), "NO_FEASIBLE_RESULT"),
])
def test_invalid_and_impossible_requests(target, constraints, status):
    res = rank_substitutes(MASALA, target, constraints)
    assert res.status == status and res.items == [] and res.warnings
    if status == "NO_FEASIBLE_RESULT":
        assert res.reason_counts


def test_open_pantry_never_changes_original_recipe_and_marks_purchases():
    recipe = deepcopy(get_catalog().recipes[MASALA])
    before = deepcopy(recipe)
    result = rank_substitutes(recipe, "ing_paneer", Constraints(excluded_ids=["ing_milk"]))
    assert recipe == before and result.status == "OK" and len(result.items) == 5
    assert all(i["purchase_required"] for i in result.items)


def test_four_modes_use_one_hard_pool_and_role_ablation_removes_role_gate():
    cases = {}
    c = pantry("onion", "tomato", "potato")
    for mode in ("full", "flavor_only", "without_roles", "without_context"):
        trace = {}
        res = rank_substitutes(SOUP, "ing_garlic", c, mode=mode, audit=trace)
        assert trace["candidate_ids"] == trace["complete_evidence_ids"] == sorted(c.pantry_ids)
        cases[mode] = res.items
    assert [i["name"] for i in cases["full"]] == ["onion"]
    assert [i["name"] for i in cases["flavor_only"]] == ["onion", "potato", "tomato"]
    assert cases["without_context"][0]["used_features"] == ["F", "R"]
    assert cases["without_roles"][0]["used_features"] == ["F", "C"]
    # Construct a high-flavor incompatible candidate to isolate the removed gate.
    cat = deepcopy(get_catalog())
    cat.compounds["ing_potato"] = cat.compounds["ing_garlic"]
    assert rank_substitutes(SOUP, "ing_garlic", pantry("potato"), catalog=cat).items == []
    assert rank_substitutes(SOUP, "ing_garlic", pantry("potato"), mode="without_roles", catalog=cat).items


def test_missing_versus_zero_and_threshold_and_stable_ties():
    cat = deepcopy(get_catalog())
    cat.vectors["ing_firm_tofu"] = cat.vectors["ing_silken_tofu"] = {}
    c = pantry("silken_tofu", "firm_tofu")
    a = rank_substitutes(MASALA, "ing_paneer", c, catalog=cat)
    assert a.status == "NO_FEASIBLE_RESULT" and a.reason_counts["missing_evidence"] == 2
    cat.compounds.update(ing_paneer={1}, ing_firm_tofu={2}, ing_silken_tofu={3})
    b = rank_substitutes(MASALA, "ing_paneer", c, mode="flavor_only", catalog=cat)
    assert [(x["candidate_id"], x["score"]) for x in b.items] == [("ing_firm_tofu", 0), ("ing_silken_tofu", 0)]
    assert rank_substitutes(MASALA, "ing_paneer", c, top_k=1, catalog=cat).items[0]["candidate_id"] == "ing_firm_tofu"
    cat.config["substitution"]["min_score"] = .47
    assert rank_substitutes(MASALA, "ing_paneer", c, catalog=cat).reason_counts["below_threshold"] == 2


def test_source_checked_preparation_block_applies_to_every_mode():
    cat = get_catalog()
    args = ("Butter test", [{"original_phrase": "butter"}, {"original_phrase": "sugar"}])
    recipe = create_custom_recipe(*args, ["Cream the butter and sugar until pale."])
    for mode in ("full", "without_roles", "flavor_only", "without_context"):
        result = rank_substitutes(recipe, "ing_butter", pantry("olive_oil"), mode=mode, catalog=cat)
        assert result.status == "NO_FEASIBLE_RESULT" and result.reason_counts["blocked_pair"] == 1
    warm = create_custom_recipe(*args, ["Melt the butter and stir in sugar."])
    assert rank_substitutes(warm, "ing_butter", pantry("olive_oil")).reason_counts.get("blocked_pair", 0) == 0

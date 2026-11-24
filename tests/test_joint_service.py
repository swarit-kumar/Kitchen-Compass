from copy import deepcopy
from itertools import product
import json
from math import prod

import pytest
from streamlit.testing.v1 import AppTest

from kitchencompass.adapt import generate_candidate_lists, pair_compatibility_score, validate_plan
from kitchencompass.catalog import Catalog, load_joint_rules, load_jsonl
from kitchencompass.custom_recipes import create_custom_recipe
from kitchencompass.data_io import ROOT, read_json
from kitchencompass.joint_evaluation import evaluate_joint
from kitchencompass.schemas import Constraints
from kitchencompass.service import adapt_recipe, rank_substitutes, validate_recipe

PANEER = "rec_black_pepper_paneer"
TARGETS = ["ing_paneer", "ing_red_bell_pepper"]
PANTRY = ["ing_firm_tofu", "ing_green_bell_pepper", "ing_silken_tofu", "ing_cheddar", "ing_broccoli"]
LIMITED = Constraints(pantry_ids=PANTRY, excluded_ids=["ing_milk"], pantry_only=True)


@pytest.fixture(scope="module")
def catalog():
    return Catalog()


@pytest.mark.parametrize(("targets", "constraints", "status"), [
    ([], {}, "NEEDS_INPUT"),
    (TARGETS * 2, {}, "UNSUPPORTED_INPUT"),
    (TARGETS[:1] * 2, {}, "UNSUPPORTED_INPUT"),
    (TARGETS, {"max_replacements": 1}, "UNSUPPORTED_INPUT"),
    (TARGETS, {"max_replacements": 4}, "UNSUPPORTED_INPUT"),
    (["ing_butter"], {}, "NEEDS_INPUT"),
    (["unknown"], {}, "UNSUPPORTED_INPUT"),
    (TARGETS, {"excluded_ids": ["unknown"]}, "UNRESOLVED_EXCLUSION"),
    (TARGETS, {"pantry_ids": ["unknown"]}, "UNSUPPORTED_INPUT"),
    (["ing_red_bell_pepper"], {"excluded_ids": ["ing_milk"]}, "UNRESOLVED_EXCLUSION"),
    (TARGETS, {"pantry_only": True}, "NO_FEASIBLE_RESULT"),
])
def test_public_statuses(catalog, targets, constraints, status):
    result = adapt_recipe(PANEER, targets, constraints, catalog=catalog)
    assert result.status == status and not result.items and result.warnings
    assert result.data_version == catalog.versions["data_version"]


def test_single_and_custom_recipe_contract(catalog):
    custom = create_custom_recipe("Pepper paneer", [
        {"original_phrase": "paneer", "quantity_text": "200 g"},
        {"original_phrase": "red bell pepper", "quantity_text": "1"},
        {"original_phrase": "paneer", "quantity_text": "extra for serving"},
        {"original_phrase": "onion", "quantity_text": "1"}], ["Add the paneer."])
    original = custom.model_dump()
    single = rank_substitutes(custom, TARGETS[0], LIMITED, catalog=catalog)
    plans = adapt_recipe(custom, TARGETS[:1], LIMITED, catalog=catalog)
    assert plans.status == single.status == "OK"
    assert [p["replacement_ids"][0] for p in plans.items] == [i["candidate_id"] for i in single.items[:3]]
    first = plans.items[0]
    assert first["score"] == single.items[0]["score"] and first["component_scores"]["J"] is None
    assert first["final_ids"][0] == first["final_ids"][2] == first["replacements"][TARGETS[0]]
    assert not first["purchase_ids"] and custom.model_dump() == original
    result = adapt_recipe(custom, TARGETS, LIMITED, catalog=catalog)
    assert result.status == "OK" and all(p["constraint_checks"]["valid"] for p in result.items)
    assert custom.model_dump() == original


def test_three_by_five_exhaustive_order_and_validation(catalog):
    # Use actual bounded D2 lists and independently calculate Q, pair cosine and sorting.
    recipe = catalog.recipes["rec_broccoli_cheddar_soup"]
    targets = ["ing_butter", "ing_broccoli", "ing_cheddar"]
    constraints = Constraints(pantry_ids=["ing_firm_tofu"])
    pools = generate_candidate_lists(recipe, targets, constraints, catalog)
    assert [len(pools[t]) for t in targets] == [5, 5, 5]
    scored = []
    from math import fsum, sqrt
    for group in product(*(pools[t] for t in targets)):
        ids = tuple(c["candidate_id"] for c in group)
        if len(set(ids)) != 3:
            continue
        similarities = []
        for i, j in ((0, 1), (0, 2), (1, 2)):
            a, b = (catalog.vectors[ids[n]] for n in (i, j))
            den = sqrt(sum(v*v for v in a.values())) * sqrt(sum(v*v for v in b.values()))
            similarities.append(sum(v*b.get(k, 0) for k, v in a.items()) / den if den else 0)
        score = 0.8 * fsum(c["score"] for c in group) / 3 + 0.2 * fsum(similarities) / 3
        scored.append((-score, len(set(ids) - set(constraints.pantry_ids)), ids))
    audit = {}
    result = adapt_recipe(recipe, targets, constraints, 30, catalog=catalog, audit=audit)
    assert audit["combinations"] == prod(map(len, pools.values())) == 125
    assert len(result.items) == 3
    for plan, (negative, purchases, ids) in zip(result.items, sorted(scored)):
        assert plan["score"] == pytest.approx(-negative)
        assert plan["purchase_count"] == purchases and tuple(plan["replacement_ids"]) == ids
        assert validate_plan(recipe, targets, plan, constraints, catalog)["valid"]
    assert adapt_recipe(recipe, targets, constraints, 1, catalog=catalog).items == result.items[:1]
    altered = {**result.items[0], "final_ids": [], "purchase_ids": [], "replacements": {}}
    assert not validate_plan(recipe, targets, altered, constraints, catalog)["valid"]


def test_loaded_hard_block_changes_public_selection(tmp_path, monkeypatch, catalog):
    # Synthetic reviewer and scope exist only inside this constructed test.
    path = tmp_path / "rules.jsonl"
    pair = {"ingredient_a": "ing_firm_tofu", "ingredient_b": "ing_green_bell_pepper",
            "context_roles": ["protein"], "score": 1.0, "blocked": False,
            "evidence_ref": "synthetic conflict fixture", "reviewer": "fixture", "review_status": "reviewed"}
    path.write_text("\n".join(json.dumps(r) for r in [pair, {**pair, "blocked": True}]))
    monkeypatch.setattr(catalog, "pair_compatibility", load_joint_rules(path, set(catalog.ingredients)))
    assert pair_compatibility_score(pair["ingredient_b"], pair["ingredient_a"], catalog, ["protein"])["blocked"]
    audit = {}
    result = adapt_recipe(PANEER, TARGETS, LIMITED, catalog=catalog, audit=audit)
    assert audit["baseline"]["replacement_ids"] == ["ing_firm_tofu", "ing_green_bell_pepper"]
    assert not audit["baseline"]["valid"] and audit["baseline"]["joint_score"] is None
    assert result.status == "OK" and result.items[0]["replacement_ids"] == ["ing_silken_tofu", "ing_green_bell_pepper"]
    limited = Constraints(pantry_ids=["ing_firm_tofu", "ing_green_bell_pepper"], pantry_only=True)
    none = adapt_recipe(PANEER, TARGETS, limited, catalog=catalog)
    assert none.status == "NO_FEASIBLE_RESULT" and none.reason_counts and not none.items


def test_file_rules_require_review_and_valid_scope(tmp_path, catalog):
    row, = load_jsonl(ROOT / "data/processed/pair_compatibility.jsonl")
    path = tmp_path / "rules.jsonl"
    known = set(catalog.ingredients)
    path.write_text(json.dumps({**row, "review_status": "pending_review", "reviewer": None}))
    assert load_joint_rules(path, known) == []
    reviewed = {**row, "review_status": "reviewed", "reviewer": "test fixture"}
    path.write_text(json.dumps(reviewed))
    assert load_joint_rules(path, known) == [reviewed]
    for invalid in ({"reviewer": None}, {"score": 1.5}, {"ingredient_b": "unknown"},
                    {"ingredient_b": row["ingredient_a"]}, {"context_roles": ["unknown"]}):
        path.write_text(json.dumps({**reviewed, **invalid}))
        with pytest.raises(ValueError):
            load_joint_rules(path, known)


def test_directed_preparation_block_checked_independently(catalog):
    custom = create_custom_recipe("Creamed mixture", [{"original_phrase": "butter"}, {"original_phrase": "sugar"}],
                                  ["Cream the butter and sugar."])
    recipe = validate_recipe(custom, catalog)["recipe"]
    targets = ["ing_butter"]
    plan = {"target_ids": targets, "replacement_ids": ["ing_olive_oil"]}
    result = validate_plan(recipe, targets, plan, Constraints(), catalog)
    assert not result["valid"] and any("Blocked substitution" in s for s in result["errors"])


def test_exact_benchmark_and_abstention_accounting(catalog):
    rows = load_jsonl(ROOT / "data/benchmark/dev_cases.jsonl")
    dev = set(read_json(ROOT / "data/benchmark/splits.json")["recipes"]["dev"])
    report = evaluate_joint(catalog, rows, dev)
    assert report == read_json(ROOT / "results/development_joint_plans.json")
    assert [c["case_id"] for c in report["cases"]] == [r["case_id"] for r in rows if r["task_type"] == "joint"]
    assert report["summary"]["constraint_violations"] == 0
    row = deepcopy(next(r for r in rows if r["task_type"] == "joint"))
    row.update(pantry_ids=[], pantry_only=True)
    case, = evaluate_joint(catalog, [row], dev)["cases"]
    assert case["result"]["status"] == "NO_FEASIBLE_RESULT" and not case["independent"]["valid"]
    with pytest.raises(ValueError):
        evaluate_joint(catalog, [{**row, "split": "test"}], dev)


def test_joint_screen_presets_and_stale_results():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    app.sidebar.radio[0].set_value("Joint replacements").run()
    for label, valid in [("Chowder comparison", False), ("Paneer and pepper", True)]:
        next(b for b in app.button if b.label == label).click().run()
        next(b for b in app.button if b.label == "Find replacement plans").click().run()
        assert not app.exception
        _, result, baseline = app.session_state["joint_search"]
        assert result.status == "OK" and baseline["valid"] == valid
        assert any(h.value == "Plan 1" for h in app.subheader)
    app.multiselect(key="joint_pantry").set_value([]).run()
    assert all(h.value != "Plan 1" for h in app.subheader)
    next(b for b in app.button if b.label == "Find replacement plans").click().run()
    assert not app.exception and app.session_state["joint_search"][1].status == "NO_FEASIBLE_RESULT"


def test_unknown_pair_evidence_is_reported(catalog, monkeypatch):
    monkeypatch.setattr(catalog, "vectors", {**catalog.vectors, "ing_green_bell_pepper": {}})
    pair = pair_compatibility_score("ing_firm_tofu", "ing_green_bell_pepper", catalog, ["protein"])
    assert pair["score"] == 0 and pair["warning"] and not pair["blocked"]


def test_joint_quality_counts_reviewed_misses_and_abstentions():
    from kitchencompass.joint_evaluation import graded_hit

    plan = {"replacements": {"a": "b", "c": "d"}}
    row = {"review_status": "reconciled", "annotator_ids": ["fixture"],
           "candidate_options": [{"candidate_id": "one", **plan}],
           "candidate_judgments": [{"candidate_id": "one", "grade": 1}]}
    assert graded_hit(row, [plan]) == graded_hit(row, []) == 0
    row["candidate_judgments"][0]["grade"] = 2
    assert graded_hit(row, [plan]) == 1
    assert graded_hit(row, [{"replacements": {"a": "other"}}]) is None


def test_joint_screen_accepts_a_session_recipe():
    from kitchencompass.service import confirm_custom_recipe, get_catalog

    recipe = create_custom_recipe("Two-target demo", [{"original_phrase": phrase} for phrase in
                                  ("paneer", "red bell pepper", "onion")], ["Cook the onion, then add paneer."])
    recipe = confirm_custom_recipe(recipe, get_catalog())
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    key = str(recipe.recipe_id)
    app.session_state["custom_recipes"] = {key: recipe}
    app.sidebar.radio[0].set_value("Joint replacements").run()
    app.selectbox(key="joint_recipe").set_value(key).run()
    app.multiselect(key="joint_targets").set_value(TARGETS).run()
    app.multiselect(key="joint_pantry").set_value(PANTRY).run()
    app.checkbox(key="joint_only").check().run()
    next(b for b in app.button if b.label == "Find replacement plans").click().run()
    assert not app.exception and app.session_state["joint_search"][1].status == "OK"
    assert app.session_state["custom_recipes"][key] == recipe

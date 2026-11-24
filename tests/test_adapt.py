
from types import SimpleNamespace

from kitchencompass.adapt import pair_compatibility_score

from kitchencompass.adapt import generate_independent_baseline

from kitchencompass.adapt import generate_joint_plans
from itertools import product
from kitchencompass.adapt import score_joint_plan
from kitchencompass.adapt import MAX_TARGETS


def make_catalog(rule):
    return SimpleNamespace(
        pair_compatibility=[rule],
        vectors={
            "ing_a": {"flavor_1": 1.0},
            "ing_b": {"flavor_2": 1.0},
        },
    )


def make_rule(blocked=False):
    return {
        "ingredient_a": "ing_a",
        "ingredient_b": "ing_b",
        "context_roles": ["texture"],
        "score": 0.8,
        "blocked": blocked,
        "evidence_ref": "synthetic-test",
        "reviewer": "synthetic-test",
    }


def test_matching_context_uses_reviewed_pair_score():
    catalog = make_catalog(make_rule())

    result = pair_compatibility_score(
        "ing_a",
        "ing_b",
        catalog,
        {"texture"},
    )

    assert result["score"] == 0.8
    assert result["source"] == "reviewed_pair_rule"
    assert result["blocked"] is False


def test_nonmatching_context_uses_cosine_fallback():
    catalog = make_catalog(make_rule())

    result = pair_compatibility_score(
        "ing_a",
        "ing_b",
        catalog,
        {"aromatic"},
    )

    assert result["source"] == "context_cosine"
    assert result["blocked"] is False
    assert result["score"] == 0.0


def test_matching_blocked_pair_is_rejected():
    catalog = make_catalog(make_rule(blocked=True))

    result = pair_compatibility_score(
        "ing_a",
        "ing_b",
        catalog,
        {"texture"},
    )

    assert result["blocked"] is True
    assert result["score"] is None
    assert result["source"] == "reviewed_pair_rule"



from kitchencompass.adapt import score_joint_plan


def test_single_replacement_uses_individual_score():
    catalog = SimpleNamespace(
        pair_compatibility=[],
        vectors={},
        ingredients={
            "ing_original": {
                "ingredient_id": "ing_original",
                "display_name": "Original Ingredient",
                "aliases": [],
                "default_roles": ["texture"],
            }
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [{"ingredient_id": "ing_original"}],
        "instructions": [],
    }

    candidates = [
        {"candidate_id": "ing_a", "score": 0.85}
    ]

    result = score_joint_plan(
        candidates,
        catalog,
        recipe,
        ["ing_original"],
    )

    assert result["valid"] is True
    assert abs(result["score"] - 0.85) < 1e-9
    assert result["component_scores"]["Q"] == 0.85
    assert result["component_scores"]["J"] is None


def test_joint_score_combines_quality_and_compatibility():
    catalog = SimpleNamespace(
        pair_compatibility=[],
        vectors={
            "ing_a": {"x": 1.0},
            "ing_b": {"x": 1.0},
        },
        ingredients={
            "ing_original_a": {
                "ingredient_id": "ing_original_a",
                "display_name": "Original Ingredient A",
                "aliases": [],
                "default_roles": ["texture"],
            },
            "ing_original_b": {
                "ingredient_id": "ing_original_b",
                "display_name": "Original Ingredient B",
                "aliases": [],
                "default_roles": ["texture"],
            },
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [
            {"ingredient_id": "ing_original_a"},
            {"ingredient_id": "ing_original_b"},
        ],
        "instructions": [],
    }

    candidates = [
        {"candidate_id": "ing_a", "score": 0.8},
        {"candidate_id": "ing_b", "score": 0.6},
    ]

    result = score_joint_plan(
        candidates,
        catalog,
        recipe,
        ["ing_original_a", "ing_original_b"],
    )

    assert result["valid"] is True
    assert result["component_scores"]["Q"] == 0.7
    assert result["component_scores"]["J"] == 1.0
    assert abs(result["score"] - 0.76) < 1e-9



def test_matching_blocked_rule_takes_priority():
    allowed_rule = make_rule(blocked=False)
    blocked_rule = make_rule(blocked=True)

    catalog = make_catalog(allowed_rule)
    catalog.pair_compatibility.append(blocked_rule)

    result = pair_compatibility_score(
        "ing_a",
        "ing_b",
        catalog,
        {"texture"},
    )

    assert result["blocked"] is True
    assert result["score"] is None
    
    
    
def test_joint_score_uses_matching_recipe_context_rule():
    catalog = SimpleNamespace(
        pair_compatibility=[make_rule()],
        vectors={
            "ing_a": {"x": 1.0},
            "ing_b": {"x": 1.0},
        },
        ingredients={
            "ing_original_a": {
                "ingredient_id": "ing_original_a",
                "display_name": "Original A",
                "aliases": [],
                "default_roles": ["texture"],
            },
            "ing_original_b": {
                "ingredient_id": "ing_original_b",
                "display_name": "Original B",
                "aliases": [],
                "default_roles": ["texture"],
            },
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [
            {"ingredient_id": "ing_original_a"},
            {"ingredient_id": "ing_original_b"},
        ],
        "instructions": [],
    }

    result = score_joint_plan(
        [
            {"candidate_id": "ing_a", "score": 0.8},
            {"candidate_id": "ing_b", "score": 0.6},
        ],
        catalog,
        recipe,
        ["ing_original_a", "ing_original_b"],
    )

    assert result["valid"] is True
    assert result["component_scores"]["J"] == 0.8
    assert result["pair_details"][0]["source"] == "reviewed_pair_rule"


def test_joint_score_ignores_nonmatching_recipe_context_rule():
    catalog = SimpleNamespace(
        pair_compatibility=[make_rule()],
        vectors={
            "ing_a": {"x": 1.0},
            "ing_b": {"y": 1.0},
        },
        ingredients={
            "ing_original_a": {
                "ingredient_id": "ing_original_a",
                "display_name": "Original A",
                "aliases": [],
                "default_roles": ["aromatic"],
            },
            "ing_original_b": {
                "ingredient_id": "ing_original_b",
                "display_name": "Original B",
                "aliases": [],
                "default_roles": ["aromatic"],
            },
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [
            {"ingredient_id": "ing_original_a"},
            {"ingredient_id": "ing_original_b"},
        ],
        "instructions": [],
    }

    result = score_joint_plan(
        [
            {"candidate_id": "ing_a", "score": 0.8},
            {"candidate_id": "ing_b", "score": 0.6},
        ],
        catalog,
        recipe,
        ["ing_original_a", "ing_original_b"],
    )

    assert result["valid"] is True
    assert result["component_scores"]["J"] == 0.0
    assert result["pair_details"][0]["source"] == "context_cosine"
    
    


def test_independent_baseline_selects_individual_best_candidates():
    candidate_lists = {
        "target_a": [
            {"candidate_id": "candidate_a1", "score": 0.9},
            {"candidate_id": "candidate_a2", "score": 0.7},
        ],
        "target_b": [
            {"candidate_id": "candidate_b1", "score": 0.8},
            {"candidate_id": "candidate_b2", "score": 0.6},
        ],
    }

    result = generate_independent_baseline(candidate_lists)

    assert result["replacement_ids"] == [
        "candidate_a1",
        "candidate_b1",
    ]
    assert abs(result["score"] - 0.85) < 1e-9
    assert result["valid"] is True
    assert result["violations"] == []


def test_independent_baseline_reports_duplicate_replacements():
    candidate_lists = {
        "target_a": [
            {"candidate_id": "shared_candidate", "score": 0.9},
            {"candidate_id": "alternative_a", "score": 0.7},
        ],
        "target_b": [
            {"candidate_id": "shared_candidate", "score": 0.8},
            {"candidate_id": "alternative_b", "score": 0.6},
        ],
    }

    result = generate_independent_baseline(candidate_lists)

    assert result["replacement_ids"] == [
        "shared_candidate",
        "shared_candidate",
    ]
    assert result["valid"] is False
    assert "Duplicate replacement IDs selected." in result["violations"]




def test_joint_planner_can_choose_different_candidates_than_baseline():
    catalog = SimpleNamespace(
        pair_compatibility=[],
        vectors={
            "candidate_a1": {"x": 1.0},
            "candidate_a2": {"y": 1.0},
            "candidate_b1": {"y": 1.0},
            "candidate_b2": {"x": 1.0},
        },
        ingredients={
            "target_a": {
                "ingredient_id": "target_a",
                "display_name": "Target A",
                "aliases": [],
                "default_roles": ["texture"],
            },
            "target_b": {
                "ingredient_id": "target_b",
                "display_name": "Target B",
                "aliases": [],
                "default_roles": ["texture"],
            },
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [
            {"ingredient_id": "target_a"},
            {"ingredient_id": "target_b"},
        ],
        "instructions": [],
    }

    candidate_lists = {
        "target_a": [
            {"candidate_id": "candidate_a1", "score": 0.95},
            {"candidate_id": "candidate_a2", "score": 0.85},
        ],
        "target_b": [
            {"candidate_id": "candidate_b1", "score": 0.95},
            {"candidate_id": "candidate_b2", "score": 0.70},
        ],
    }

    baseline = generate_independent_baseline(candidate_lists)
    joint_plans = generate_joint_plans(
        candidate_lists,
        catalog,
        recipe,
    )

    assert baseline["replacement_ids"] == [
        "candidate_a1",
        "candidate_b1",
    ]

    assert joint_plans

    # The joint planner chooses a more compatible combination.
    assert joint_plans[0]["replacement_ids"] == [
        "candidate_a2",
        "candidate_b1",
    ]

    assert joint_plans[0]["score"] > 0.76



def test_joint_planner_matches_exhaustive_maximum():
    catalog = SimpleNamespace(
        pair_compatibility=[],
        vectors={
            "a1": {"x": 1.0},
            "a2": {"y": 1.0},
            "b1": {"x": 1.0},
            "b2": {"y": 1.0},
        },
        ingredients={
            "target_a": {
                "ingredient_id": "target_a",
                "display_name": "Target A",
                "aliases": [],
                "default_roles": ["texture"],
            },
            "target_b": {
                "ingredient_id": "target_b",
                "display_name": "Target B",
                "aliases": [],
                "default_roles": ["texture"],
            },
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [
            {"ingredient_id": "target_a"},
            {"ingredient_id": "target_b"},
        ],
        "instructions": [],
    }

    candidate_lists = {
        "target_a": [
            {"candidate_id": "a1", "score": 0.9},
            {"candidate_id": "a2", "score": 0.7},
        ],
        "target_b": [
            {"candidate_id": "b1", "score": 0.8},
            {"candidate_id": "b2", "score": 0.6},
        ],
    }

    target_ids = list(candidate_lists)
    
    if len(target_ids) > MAX_TARGETS:
        return []

    if len(set(target_ids)) != len(target_ids):
        return []

    exhaustive_scores = []

    for selected in product(
        *[candidate_lists[target] for target in target_ids]
    ):
        if len({
            candidate["candidate_id"]
            for candidate in selected
        }) != len(selected):
            continue

        result = score_joint_plan(
            selected,
            catalog,
            recipe,
            target_ids,
        )

        if result["valid"]:
            exhaustive_scores.append(result["score"])

    plans = generate_joint_plans(
        candidate_lists,
        catalog,
        recipe,
    )

    assert plans
    assert exhaustive_scores

    assert abs(
        plans[0]["score"] - max(exhaustive_scores)
    ) < 1e-9




def test_joint_planner_rejects_more_than_three_targets():
    candidate_lists = {
        "target_a": [{"candidate_id": "a1", "score": 0.9}],
        "target_b": [{"candidate_id": "b1", "score": 0.8}],
        "target_c": [{"candidate_id": "c1", "score": 0.7}],
        "target_d": [{"candidate_id": "d1", "score": 0.6}],
    }

    result = generate_joint_plans(
        candidate_lists,
        SimpleNamespace(),
        {},
    )

    assert result == []


def test_joint_planner_rejects_empty_candidate_group():
    candidate_lists = {
        "target_a": [{"candidate_id": "a1", "score": 0.9}],
        "target_b": [],
    }

    result = generate_joint_plans(
        candidate_lists,
        SimpleNamespace(),
        {},
    )

    assert result == []



def test_joint_planner_uses_at_most_five_candidates_per_target():
    catalog, recipe, targets, _, _ = make_validator_fixture()
    # An artificially high sixth candidate must never enter the search.
    ids = ["ing_carrot", "ing_broccoli", "ing_celery", "ing_cauliflower", "ing_zucchini"]
    candidates = [{"candidate_id": key, "score": 0.5} for key in ids]
    candidates.append({"candidate_id": "ing_paneer", "score": 1.0})
    plans = generate_joint_plans({targets[0]: candidates}, catalog, recipe)
    assert len(plans) == 3
    assert all(p["score"] == 0.5 and p["replacement_ids"][0] in ids for p in plans)


def make_validator_fixture():
    from kitchencompass.catalog import Catalog
    from kitchencompass.schemas import Constraints

    catalog = Catalog()

    recipe = next(
        recipe for recipe in catalog.recipes.values()
        if recipe["recipe_id"] == "rec_aloo_and_mung_curry"
    )

    target_ids = ["ing_potato"]

    plan = {
        "target_ids": ["ing_potato"],
        "replacement_ids": ["ing_carrot"],
    }

    constraints = Constraints()

    return catalog, recipe, target_ids, plan, constraints



def test_validate_plan_accepts_valid_plan():
    from kitchencompass.adapt import validate_plan

    catalog, recipe, target_ids, plan, constraints = (
        make_validator_fixture()
    )

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is True
    assert result["errors"] == []
    assert "ing_carrot" in result["final_ingredient_ids"]
    assert "ing_potato" not in result["final_ingredient_ids"]
    
    

def test_validate_plan_rejects_unknown_replacement():
    from kitchencompass.adapt import validate_plan

    catalog, recipe, target_ids, plan, constraints = (
        make_validator_fixture()
    )

    plan["replacement_ids"] = ["ing_does_not_exist"]

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "Unknown replacement ingredient" in error
        for error in result["errors"]
    )
    
    
def test_validate_plan_rejects_duplicate_replacements():
    from kitchencompass.adapt import validate_plan

    catalog, recipe, target_ids, plan, constraints = (
        make_validator_fixture()
    )

    plan["target_ids"] = ["ing_potato", "ing_cooked_mung_bean"]
    plan["replacement_ids"] = ["ing_carrot", "ing_carrot"]

    target_ids = ["ing_potato", "ing_cooked_mung_bean"]

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "Duplicate replacement ingredients" in error
        for error in result["errors"]
    )
    
    
def test_validate_plan_rejects_excluded_replacement():
    from kitchencompass.adapt import validate_plan
    from kitchencompass.schemas import Constraints

    catalog, recipe, target_ids, plan, constraints = (
        make_validator_fixture()
    )

    constraints = Constraints(
        excluded_ids=["ing_carrot"]
    )

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "excluded ingredient" in error.lower()
        for error in result["errors"]
    )
    
    
def test_validate_plan_rejects_replacement_outside_pantry():
    from kitchencompass.adapt import validate_plan
    from kitchencompass.schemas import Constraints

    catalog, recipe, target_ids, plan, constraints = (
        make_validator_fixture()
    )

    constraints = Constraints(
        pantry_only=True,
        pantry_ids=["ing_potato"],
    )

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "outside the available pantry" in error
        for error in result["errors"]
    )
    
def test_validate_plan_rejects_incomplete_target_coverage():
    from kitchencompass.adapt import validate_plan

    catalog, recipe, target_ids, plan, constraints = (
        make_validator_fixture()
    )

    # The requested target is potato, but the plan omits it.
    plan["target_ids"] = []

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "not covered exactly once" in error
        for error in result["errors"]
    )
    
def test_validate_plan_rejects_more_than_three_targets():
    from kitchencompass.adapt import validate_plan

    catalog, recipe, _, _, constraints = make_validator_fixture()

    target_ids = [
        "ing_potato",
        "ing_cooked_mung_bean",
        "ing_tomato",
        "ing_ginger",
    ]

    plan = {
        "target_ids": target_ids,
        "replacement_ids": [
            "ing_carrot",
            "ing_pumpkin",
            "ing_sweet_potato",
            "ing_all_purpose_flour",
        ],
    }

    result = validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "At most three replacement targets" in error
        for error in result["errors"]
    )
    
    
def test_validate_plan_rejects_blocked_replacement_pair(monkeypatch):
    import kitchencompass.adapt as adapt

    catalog, recipe, _, _, constraints = make_validator_fixture()

    target_ids = [
        "ing_potato",
        "ing_cooked_mung_bean",
    ]

    plan = {
        "target_ids": target_ids,
        "replacement_ids": [
            "ing_carrot",
            "ing_pumpkin",
        ],
    }

    def fake_blocked_pair(*args, **kwargs):
        return {
            "score": None,
            "blocked": True,
            "source": "synthetic_test",
            "warning": None,
        }

    monkeypatch.setattr(
        adapt,
        "pair_compatibility_score",
        fake_blocked_pair,
    )

    result = adapt.validate_plan(
        recipe,
        target_ids,
        plan,
        constraints,
        catalog,
    )

    assert result["valid"] is False
    assert any(
        "Blocked replacement pair" in error
        for error in result["errors"]
    )


def test_joint_score_rejects_score_above_one():
    from kitchencompass.adapt import score_joint_plan

    catalog = SimpleNamespace(
        ingredients={},
        rules=[],
        pair_compatibility=[],
        vectors={},
    )

    candidates = [
        {"candidate_id": "ing_a", "score": 1.5}
    ]

    result = score_joint_plan(
        candidates,
        catalog,
        {},
        ["ing_target"],
    )

    assert result["valid"] is False
    assert "between 0 and 1" in result["reason"]



def test_joint_score_rejects_nan_score():
    from math import nan
    from kitchencompass.adapt import score_joint_plan

    catalog = SimpleNamespace(
        ingredients={},
        rules=[],
        pair_compatibility=[],
        vectors={},
    )

    candidates = [
        {"candidate_id": "ing_a", "score": nan}
    ]

    result = score_joint_plan(
        candidates,
        catalog,
        {},
        ["ing_target"],
    )

    assert result["valid"] is False
    assert "finite numbers" in result["reason"]



def test_joint_score_rejects_duplicate_replacement_ids():
    from kitchencompass.adapt import score_joint_plan

    catalog = SimpleNamespace(
        ingredients={},
        rules=[],
        pair_compatibility=[],
        vectors={},
    )

    candidates = [
        {"candidate_id": "ing_a", "score": 0.8},
        {"candidate_id": "ing_a", "score": 0.9},
    ]

    result = score_joint_plan(
        candidates,
        catalog,
        {},
        ["target_a", "target_b"],
    )

    assert result["valid"] is False
    assert "Duplicate replacement ingredient IDs" in result["reason"]



def test_joint_score_rejects_target_as_replacement():
    from kitchencompass.adapt import score_joint_plan

    catalog = SimpleNamespace(
        ingredients={},
        rules=[],
        pair_compatibility=[],
        vectors={},
    )

    candidates = [
        {"candidate_id": "ing_potato", "score": 0.8}
    ]

    result = score_joint_plan(
        candidates,
        catalog,
        {},
        ["ing_potato"],
    )

    assert result["valid"] is False
    assert "cannot be its own replacement" in result["reason"]



def test_independent_baseline_rejects_more_than_three_targets():
    candidate_lists = {
        "target_a": [{"candidate_id": "a", "score": 0.9}],
        "target_b": [{"candidate_id": "b", "score": 0.8}],
        "target_c": [{"candidate_id": "c", "score": 0.7}],
        "target_d": [{"candidate_id": "d", "score": 0.6}],
    }

    result = generate_independent_baseline(candidate_lists)

    assert result["valid"] is False
    assert any("three replacement targets" in item for item in result["violations"])



def test_independent_baseline_rejects_score_above_one():
    candidate_lists = {
        "target_a": [{"candidate_id": "a", "score": 1.5}]
    }

    result = generate_independent_baseline(candidate_lists)

    assert result["valid"] is False
    assert any("Invalid candidate score" in item for item in result["violations"])



def test_independent_baseline_rejects_nan_score():
    candidate_lists = {
        "target_a": [{"candidate_id": "a", "score": float("nan")}]
    }

    result = generate_independent_baseline(candidate_lists)

    assert result["valid"] is False
    assert any("Invalid candidate score" in item for item in result["violations"])



def test_independent_baseline_rejects_missing_candidate_id():
    candidate_lists = {
        "target_a": [{"score": 0.9}]
    }

    result = generate_independent_baseline(candidate_lists)

    assert result["valid"] is False
    assert any("Invalid candidate ID" in item for item in result["violations"])



def test_independent_baseline_reports_blocked_pair_without_repairing():
    from kitchencompass.adapt import generate_independent_baseline

    catalog = SimpleNamespace(
        pair_compatibility=[make_rule(blocked=True)],
        vectors={},
        ingredients={
            "target_a": {
                "ingredient_id": "target_a",
                "display_name": "Target A",
                "aliases": [],
                "default_roles": ["texture"],
            },
            "target_b": {
                "ingredient_id": "target_b",
                "display_name": "Target B",
                "aliases": [],
                "default_roles": ["texture"],
            },
        },
        policy={"shorthand": {}},
        rules=[],
    )

    recipe = {
        "ingredients": [
            {"ingredient_id": "target_a"},
            {"ingredient_id": "target_b"},
        ],
        "instructions": [],
    }

    candidate_lists = {
        "target_a": [{"candidate_id": "ing_a", "score": 0.9}],
        "target_b": [{"candidate_id": "ing_b", "score": 0.8}],
    }

    result = generate_independent_baseline(
        candidate_lists, catalog=catalog, recipe=recipe
    )

    assert result["replacement_ids"] == ["ing_a", "ing_b"]
    assert result["valid"] is False
    assert any("Blocked replacement pair" in item for item in result["violations"])



def test_validate_targets_accepts_valid_targets():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={"target_a": {}, "target_b": {}})
    recipe = {"ingredients": [
        {"ingredient_id": "target_a"},
        {"ingredient_id": "target_b"},
    ]}

    result = validate_targets(recipe, ["target_a", "target_b"], catalog)

    assert result is None



def test_validate_targets_rejects_empty_targets_with_needs_input():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={"target_a": {}})
    recipe = {"ingredients": [{"ingredient_id": "target_a"}]}

    result = validate_targets(recipe, [], catalog)

    assert result.status == "NEEDS_INPUT"
    assert result.items == []



def test_validate_targets_rejects_duplicate_targets():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={"target_a": {}})
    recipe = {"ingredients": [{"ingredient_id": "target_a"}]}

    result = validate_targets(recipe, ["target_a", "target_a"], catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_validate_targets_rejects_more_than_three_targets():
    from kitchencompass.adapt import validate_targets

    ids = ["target_a", "target_b", "target_c", "target_d"]
    catalog = SimpleNamespace(ingredients={item: {} for item in ids})
    recipe = {"ingredients": [{"ingredient_id": item} for item in ids]}

    result = validate_targets(recipe, ids, catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_validate_targets_rejects_target_missing_from_recipe():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={"target_a": {}, "target_b": {}})
    recipe = {"ingredients": [{"ingredient_id": "target_a"}]}

    result = validate_targets(recipe, ["target_b"], catalog)

    assert result.status == "NEEDS_INPUT"
    assert result.items == []



def test_validate_targets_rejects_unknown_catalogue_target():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={})
    recipe = {"ingredients": [{"ingredient_id": "unknown_target"}]}

    result = validate_targets(recipe, ["unknown_target"], catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_validate_targets_rejects_string_instead_of_list():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={"target_a": {}})
    recipe = {"ingredients": [{"ingredient_id": "target_a"}]}

    result = validate_targets(recipe, "target_a", catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_validate_targets_rejects_non_string_target_id():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={})
    recipe = {"ingredients": []}

    result = validate_targets(recipe, [123], catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_validate_targets_rejects_empty_string_target_id():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={})
    recipe = {"ingredients": []}

    result = validate_targets(recipe, [""] , catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_validate_targets_rejects_whitespace_target_id():
    from kitchencompass.adapt import validate_targets

    catalog = SimpleNamespace(ingredients={})
    recipe = {"ingredients": []}

    result = validate_targets(recipe, ["   "], catalog)

    assert result.status == "UNSUPPORTED_INPUT"
    assert result.items == []



def test_joint_planner_rejects_non_dictionary_candidate():
    result = generate_joint_plans({"target_a": [None]}, None, None)
    assert result == []


def test_joint_planner_rejects_missing_candidate_id():
    result = generate_joint_plans(
        {"target_a": [{"score": 0.5}]}, None, None
    )
    assert result == []


def test_joint_planner_rejects_non_numeric_candidate_score():
    result = generate_joint_plans(
        {"target_a": [{"candidate_id": "replacement_a", "score": "high"}]},
        None,
        None,
    )
    assert result == []



def test_joint_planner_rejects_score_above_one():
    result = generate_joint_plans(
        {"target_a": [{"candidate_id": "replacement_a", "score": 1.5}]},
        None, None,
    )
    assert result == []


def test_joint_planner_rejects_negative_score():
    result = generate_joint_plans(
        {"target_a": [{"candidate_id": "replacement_a", "score": -0.1}]},
        None, None,
    )
    assert result == []


def test_joint_planner_rejects_nan_score():
    result = generate_joint_plans(
        {"target_a": [{"candidate_id": "replacement_a", "score": float("nan")}]},
        None, None,
    )
    assert result == []



def test_validate_plan_rejects_unhashable_target_id():
    from kitchencompass.adapt import validate_plan
    catalog, recipe, target_ids, plan, constraints = make_validator_fixture()
    result = validate_plan(recipe, [{}], plan, constraints, catalog)
    assert result["valid"] is False


def test_validate_plan_rejects_unhashable_plan_target_id():
    from kitchencompass.adapt import validate_plan
    catalog, recipe, target_ids, plan, constraints = make_validator_fixture()
    plan["target_ids"] = [{}]
    result = validate_plan(recipe, target_ids, plan, constraints, catalog)
    assert result["valid"] is False


def test_validate_plan_rejects_unhashable_replacement_id():
    from kitchencompass.adapt import validate_plan
    catalog, recipe, target_ids, plan, constraints = make_validator_fixture()
    plan["replacement_ids"] = [{}]
    result = validate_plan(recipe, target_ids, plan, constraints, catalog)
    assert result["valid"] is False

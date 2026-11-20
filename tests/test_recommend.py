import pytest

from kitchencompass.recommend import recommend_recipes
from kitchencompass.schemas import Constraints
from kitchencompass.service import recommend_recipes as service_recommend


def test_overlap_and_weighted_sort_on_distinct_ids_with_expected_scores():
    keys = ["a", "b", "c", "d"]
    ingredients = [{"ingredient_id": key, "display_name": key} for key in keys]
    def row(key, entries):
        return {"recipe_id": key, "title": key, "ingredients": [{"ingredient_id": i, "essential": e} for i,e in entries]}
    recipes = [row("one", [("a", False), ("b", True)]), row("two", [("a", True), ("a", False), ("c", False)])]
    baseline = recommend_recipes(recipes, ingredients, ["a"], mode="overlap")["items"]
    weighted = recommend_recipes(recipes, ingredients, ["a"], mode="weighted")["items"]
    assert [x["recipe_id"] for x in baseline] == ["one", "two"]
    assert [x["score"] for x in baseline] == [.5, .5]
    assert [x["recipe_id"] for x in weighted] == ["two", "one"]
    assert weighted[0]["score"] == pytest.approx(.8 * (2 / 3) + .1)


def test_discovery_allows_missing_items_with_pantry_only_and_versions():
    c = Constraints(pantry_ids=["ing_potato"], pantry_only=True, excluded_ids=["ing_milk"])
    for mode in ("weighted", "overlap"):
        r = service_recommend(c.pantry_ids, c, top_k=20, mode=mode)
        assert len(r.items) == 5 and r.config_version == "0.4.0"
        assert all(x["missing_ids"] and not set(x["excluded_ids"]) & set(x["available_ids"] + x["missing_ids"]) for x in r.items)

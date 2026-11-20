from streamlit.testing.v1 import AppTest

from kitchencompass.custom_recipes import export_custom_recipe
from kitchencompass.data_io import ROOT, sha256
from kitchencompass.schemas import Constraints
from kitchencompass.service import get_catalog, rank_substitutes, recommend_for_pantry


def click(app, label):
    next(x for x in app.button if x.label == label).click().run()
    assert not app.exception


def start():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=10).run()
    assert not app.exception
    return app


def test_pantry_show_more_preserves_rank_and_resets_for_new_search():
    app = start()
    app.text_input[1].set_value("milk")
    expected = recommend_for_pantry(["potato", "tomato", "onion", "water"], ["milk"], limit=None)
    titles = [f"{index}. {row['title']}" for index, row in enumerate(expected.items, 1)]

    click(app, "Find recipes")
    assert app.subheader.values == titles[:5]
    click(app, "Show 5 more")
    assert app.subheader.values == titles[:10]
    click(app, "Show 5 more")
    assert app.subheader.values == titles[:15]

    click(app, "Find recipes")
    assert app.subheader.values == titles[:5]
    app.text_input[1].set_value("egg").run()
    assert not app.subheader and all(not b.label.startswith("Show ") for b in app.button)


def test_view_recipe_opens_selected_result_and_preserves_expanded_search():
    app = start()
    click(app, "Find recipes")
    click(app, "Show 5 more")
    titles = app.subheader.values
    for position in (8, 3):
        button = [b for b in app.button if b.key and b.key.startswith("view_")][position]
        recipe = get_catalog().recipes[button.key.removeprefix("view_")]
        assert titles[position] == f"{position + 1}. {recipe['title']}"
        button.click().run()
        assert not app.exception and app.sidebar.radio[0].value == "Pantry search"
        assert app.text.values == [entry["original_phrase"] for entry in recipe["ingredients"]]
        for number, step in enumerate(recipe["instructions"], 1):
            assert f"{number}. {step}" in app.markdown.values
        assert app.subheader.values == titles
    click(app, "Hide recipe")
    assert not app.text and app.subheader.values == titles


def test_substitution_show_more_uses_ranked_eligible_candidates_and_handles_last_batch():
    app = start()
    app.sidebar.radio[0].set_value("Substitutions").run()
    click(app, "Paneer masala")
    app.checkbox(key="sub_pantry_only").uncheck().run()
    constraints = Constraints(pantry_ids=["ing_firm_tofu", "ing_silken_tofu", "ing_cheddar"], excluded_ids=["ing_milk"])
    expected = rank_substitutes("rec_capsicum_and_paneer_masala", "ing_paneer", constraints, top_k=None)
    names = [f"{index}. {row['name']}" for index, row in enumerate(expected.items, 1)]

    click(app, "Find substitutes")
    assert app.subheader.values[1:] == names[:5]
    assert len(names) > 10
    for shown in range(5, len(names), 5):
        click(app, f"Show {min(5, len(names) - shown)} more")
        assert app.subheader.values[1:] == names[:shown + 5]
    assert app.subheader.values[1:] == names
    assert all(not b.label.startswith("Show ") for b in app.button)

    app.checkbox(key="sub_pantry_only").check().run()
    assert not app.subheader
    click(app, "Find substitutes")
    assert app.subheader.values[1:] == ["1. firm tofu", "2. silken tofu"]
    assert all(not b.label.startswith("Show ") for b in app.button)


def test_demo_examples_method_switch_and_stale_results():
    app = start()
    app.text_input[1].set_value("milk")
    click(app, "Find recipes")
    assert len(app.subheader) == 5
    click(app, "Open for substitution")
    assert app.sidebar.radio[0].value == "Substitutions"
    assert app.multiselect(key="sub_excluded").value == ["ing_milk"]
    assert "ing_potato" in app.multiselect(key="sub_pantry").value
    click(app, "Paneer masala")
    click(app, "Find substitutes")
    assert "1. firm tofu" in app.subheader.values and not any("cheddar" in x for x in app.subheader.values)
    click(app, "Flavor comparison")
    assert "1. firm tofu" not in app.subheader.values
    click(app, "Find substitutes")
    assert app.subheader.values[-1] == "1. onion"
    app.selectbox(key="sub_mode").set_value("flavor_only").run()
    assert "1. onion" not in app.subheader.values
    click(app, "Find substitutes")
    assert app.subheader.values[-3:] == ["1. onion", "2. potato", "3. tomato"]
    click(app, "Instruction match")
    click(app, "Find substitutes")
    assert "1. cornstarch" in app.subheader.values
    assert any("roux_thickener" in element.value for element in app.markdown)
    click(app, "Impossible pantry")
    click(app, "Find substitutes")
    assert any("No candidate" in w for w in app.warning.values) and len(app.subheader) == 1


def test_custom_confirmation_session_isolation_export_and_ui_import():
    path = ROOT / "data/processed/recipes.jsonl"
    before = sha256(path)
    app = start()
    app.sidebar.radio[0].set_value("Custom recipes").run()
    app.text_input[0].set_value("My onion and potato soup")
    app.text_area[0].set_value("finely sliced onion | 1 small\naloo | 1")
    app.text_area[1].set_value("Soften the onion.\nAdd potato and simmer.")
    click(app, "Review ingredients")
    click(app, "Save custom recipe")
    assert not app.session_state["custom_recipes"]
    app.selectbox[0].set_value("ing_onion").run()
    click(app, "Save custom recipe")
    saved, = app.session_state["custom_recipes"].values()
    assert saved.ingredients[0].quantity_text == "1 small" and saved.ingredients[0].ingredient_id == "ing_onion"
    assert app.get("download_button")
    click(app, "Use this recipe for substitution")
    assert app.selectbox(key="sub_recipe").value == str(saved.recipe_id)
    app.multiselect(key="sub_pantry").set_value(["ing_garlic"]).run()
    app.checkbox(key="sub_pantry_only").check().run()
    click(app, "Find substitutes")
    assert "1. garlic" in app.subheader.values
    other = start()
    assert not other.session_state["custom_recipes"]
    other.sidebar.radio[0].set_value("Custom recipes").run()
    other.file_uploader[0].upload("recipe.json", export_custom_recipe(saved).encode(), "application/json").run()
    click(other, "Review imported recipe")
    click(other, "Save custom recipe")
    assert other.session_state["custom_recipes"][str(saved.recipe_id)] == saved
    assert sha256(path) == before

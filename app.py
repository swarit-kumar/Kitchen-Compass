"""KitchenCompass local Streamlit application."""
import streamlit as st

from kitchencompass.custom_recipes import create_custom_recipe, export_custom_recipe, import_custom_recipe
from kitchencompass.data_io import ROOT, sha256
from kitchencompass.schemas import Constraints
from kitchencompass.service import confirm_custom_recipe, get_catalog, normalize_inputs, rank_substitutes, recommend_for_pantry


st.set_page_config(page_title="KitchenCompass", page_icon="🍲", layout="centered")
catalog = get_catalog(sha256(ROOT / "artifacts/manifest.json"))
state = st.session_state
state.setdefault("custom_recipes", {})
names = {key: item["display_name"] for key, item in catalog.ingredients.items()}
ingredient_options = sorted(names, key=names.get)
LABELS = {"full": "Context + role + flavor", "flavor_only": "Flavor only",
          "without_context": "Without recipe context", "without_roles": "Without cooking roles"}
REASONS = {"original_or_retained": "Target or already in the recipe", "outside_pantry": "Outside this pantry",
           "excluded_ingredient": "Excluded directly or through a component", "blocked_pair": "Blocked by a preparation rule",
           "incompatible_or_missing_role": "Incompatible or unknown role", "below_threshold": "Below minimum score",
           "missing_evidence": "Insufficient evidence", "retained_exclusions": "Retained ingredients in conflict"}

RESULTS_PER_BATCH = 5


def notices(result):
    for message in result.warnings:
        if result.status == "OK":
            st.caption(message)
        else:
            st.warning(message)
    if result.reason_counts:
        with st.expander("Why candidates were filtered"):
            for reason, count in result.reason_counts.items():
                st.write(f"{REASONS.get(reason, reason)} · {count}")


def show_more(count_key, total):
    if total == 0:
        return
    shown = min(state[count_key], total)
    st.caption(f"Showing {shown} of {total}")
    if shown < total:
        next_count = min(RESULTS_PER_BATCH, total - shown)
        st.button(f"Show {next_count} more", key=f"{count_key}_more",
                  on_click=state.update, kwargs={count_key: shown + next_count})


def recipe_details(entries, steps, *, separate_quantities=False):
    st.markdown("**Ingredients**")
    for entry in entries:
        line = entry["original_phrase"]
        if separate_quantities and entry["quantity_text"]:
            line += " · " + entry["quantity_text"]
        st.text(line)
    st.markdown("**Cooking instructions**")
    if steps:
        for number, step in enumerate(steps, 1):
            st.write(f"{number}. {step}")
    else:
        st.caption("Instructions were omitted. Catalogue roles will be used.")


def pantry_page():
    st.header("Find a recipe")
    st.write("Enter the ingredients you have. Each match shows what you can use and what you still need.")
    pantry = st.text_input("Pantry ingredients", value="potato, tomato, onion, water", help="Separate names or aliases with commas.")
    excluded = st.text_input("Ingredients to exclude", placeholder="e.g. milk")
    mode = st.radio("Recipe ranking", ["weighted", "overlap"], horizontal=True,
                    format_func=lambda k: {"weighted": "Weighted match", "overlap": "Simple overlap"}[k])
    st.caption("Weighted match favors essential ingredients and fewer missing items. Simple overlap counts each distinct ingredient once.")
    query = (pantry, excluded, mode)
    if st.button("Find recipes", type="primary"):
        pantry_names = [v.strip() for v in pantry.split(",") if v.strip()]
        excluded_names = [v.strip() for v in excluded.split(",") if v.strip()]
        result = recommend_for_pantry(pantry_names, excluded_names, limit=None, mode=mode, catalog=catalog)
        pantry_ids = normalize_inputs(pantry_names, catalog)["resolved_ids"]
        excluded_ids = normalize_inputs(excluded_names, catalog)["resolved_ids"]
        state["pantry_search"] = (query, result, pantry_ids, excluded_ids)
        state["pantry_count"] = RESULTS_PER_BATCH
        state.pop("viewed_recipe", None)

    search = state.get("pantry_search")
    if search is None or search[0] != query:
        state.pop("pantry_search", None)
        return

    _, result, pantry_ids, excluded_ids = search
    notices(result)
    for index, row in enumerate(result.items[:state["pantry_count"]], 1):
        with st.container(border=True):
            st.subheader(f"{index}. {row['title']}")
            st.write(f"Score {row['score']:.3f} · {row['coverage']:.0%} in pantry · {row['missing_count']} missing")
            st.write("Have: " + (", ".join(item["name"] for item in row["matches"]) or "none"))
            st.write("Need: " + (", ".join(item["name"] + (" (essential)" if item["essential"] else "") for item in row["missing"]) or "nothing"))
            recipe_id = row["recipe_id"]
            expanded = state.get("viewed_recipe") == recipe_id
            view, substitute = st.columns(2)
            view.button("Hide recipe" if expanded else "View recipe", key="view_" + recipe_id,
                        on_click=state.update, kwargs={"viewed_recipe": None if expanded else recipe_id})
            substitute.button("Open for substitution", key="open_" + recipe_id, on_click=open_recipe,
                              args=(recipe_id, pantry_ids, excluded_ids))
            if expanded:
                recipe = catalog.recipes[recipe_id]
                recipe_details(recipe["ingredients"], recipe["instructions"])
    show_more("pantry_count", len(result.items))


def open_recipe(recipe_id, pantry=None, excluded=None):
    state["workspace"] = "Substitutions"
    state["sub_recipe"] = recipe_id
    state.pop("sub_target", None)
    state.pop("sub_search", None)
    if pantry is not None:
        state.update(sub_pantry=pantry, sub_excluded=excluded, sub_pantry_only=False, sub_mode="full")


PRESETS = {
    "Paneer masala": ("rec_capsicum_and_paneer_masala", "ing_paneer", ["ing_firm_tofu", "ing_silken_tofu", "ing_cheddar"], ["ing_milk"]),
    "Flavor comparison": ("rec_lemon_coriander_soup", "ing_garlic", ["ing_onion", "ing_potato", "ing_tomato"], []),
    "Instruction match": ("rec_broccoli_cheddar_soup", "ing_all_purpose_flour", ["ing_cornstarch"], []),
    "Impossible pantry": ("rec_capsicum_and_paneer_masala", "ing_paneer", ["ing_cheddar"], ["ing_milk"]),
}


def load_example(label):
    recipe, target, pantry, excluded = PRESETS[label]
    state.pop("sub_search", None)
    state.update(sub_recipe=recipe, sub_target=target, sub_pantry=pantry, sub_excluded=excluded,
                 sub_pantry_only=True, sub_mode="full")


def substitute_page():
    st.header("Replace one ingredient")
    st.write("Choose a recipe and a target. Restrict candidates to your pantry or include ingredients you would need to buy.")
    st.caption("Load a demo example")
    columns = st.columns(2)
    for index, label in enumerate(PRESETS):
        columns[index % 2].button(label, on_click=load_example, args=(label,), use_container_width=True)

    recipes = {key: row["title"] for key, row in catalog.recipes.items()}
    custom = state["custom_recipes"]
    recipes.update({key: f"{row.title} (your recipe)" for key, row in custom.items()})
    recipe_id = st.selectbox("Recipe", sorted(recipes, key=recipes.get), format_func=recipes.get, key="sub_recipe")
    if recipe_id in custom:
        recipe = custom[recipe_id]
        entries = [e.model_dump() for e in recipe.ingredients]
        steps = recipe.instructions
    else:
        recipe = recipe_id
        entries = catalog.recipes[recipe_id]["ingredients"]
        steps = catalog.recipes[recipe_id]["instructions"]
    with st.expander("Recipe ingredients and instructions"):
        recipe_details(entries, steps, separate_quantities=recipe_id in custom)

    options = list(dict.fromkeys(entry["ingredient_id"] for entry in entries))
    if state.get("sub_target") not in options:
        state["sub_target"] = options[0]
    target = st.selectbox("Ingredient to replace", options, format_func=names.get, key="sub_target")
    pantry = st.multiselect("Available replacements in your pantry", ingredient_options, format_func=names.get, key="sub_pantry")
    excluded = st.multiselect("Exclude these ingredients and their known derivatives", ingredient_options, format_func=names.get, key="sub_excluded")
    only = st.checkbox("Only suggest ingredients in my pantry", key="sub_pantry_only")
    method = st.selectbox("Substitution method", list(LABELS), format_func=LABELS.get, key="sub_mode")
    query = (recipe_id, target, tuple(pantry), tuple(excluded), only, method)
    if st.button("Find substitutes", type="primary"):
        result = rank_substitutes(recipe, target, Constraints(pantry_ids=pantry, excluded_ids=excluded, pantry_only=only),
                                  top_k=None, mode=method, catalog=catalog)
        state["sub_search"] = (query, result)
        state["sub_count"] = RESULTS_PER_BATCH

    search = state.get("sub_search")
    if search is None or search[0] != query:
        state.pop("sub_search", None)
        return

    _, result = search
    st.subheader(f"Replacements for {names[target]}")
    if not result.items:
        st.write("No substitutions to show.")
    notices(result)
    for number, item in enumerate(result.items[:state["sub_count"]], 1):
        with st.container(border=True):
            st.subheader(f"{number}. {item['name']}")
            st.write(("Purchase required" if item["purchase_required"] else "In your pantry") + f" · Score {item['score']:.3f}")
            for detail in item["reasons"]:
                st.write(detail)
            for clause in item["role_evidence"]["clauses"]:
                st.caption(f"Matched instruction: {clause}")
            if item["partial_evidence"]:
                st.caption("The score uses the available signals with rescaled weights.")
            if item["flavor_sources"]:
                st.caption("Molecular sources: " + ", ".join(item["flavor_sources"]))
    show_more("sub_count", len(result.items))


def custom_page():
    st.header("Your custom recipes")
    st.write("Recipes stay in this browser session. Download a JSON copy to keep one after the session ends.")
    with st.form("custom_input"):
        title = st.text_input("Recipe title")
        lines = st.text_area("Ingredients (one per line)", placeholder="potato | 200 g\ntomato | 2 medium",
                             help="Use a vertical bar before an optional quantity.")
        steps = st.text_area("Instructions (one step per line)")
        omitted = st.checkbox("Instructions not provided")
        create = st.form_submit_button("Review ingredients")
    if create:
        state.pop("draft_recipe", None)
        try:
            entries = []
            for line in lines.splitlines():
                if line.strip():
                    phrase, _, quantity = line.partition("|")
                    entries.append({"original_phrase": phrase.strip(), "quantity_text": quantity.strip() or None})
            state["draft_recipe"] = create_custom_recipe(title, entries, [s.strip() for s in steps.splitlines() if s.strip()], omitted)
        except ValueError as error:
            st.error(str(error))

    upload = st.file_uploader("Import a KitchenCompass JSON recipe", type="json")
    if st.button("Review imported recipe", disabled=upload is None):
        state.pop("draft_recipe", None)
        try:
            imported = import_custom_recipe(upload.getvalue())
            if str(imported.recipe_id) in state["custom_recipes"]:
                raise ValueError("This recipe ID already exists in this session.")
            state["draft_recipe"] = imported
        except ValueError as error:
            st.error(str(error))

    draft = state.get("draft_recipe")
    if draft:
        st.subheader(f"Confirm ingredients for {draft.title}")
        confirmations = {}
        entries = []
        for i, entry in enumerate(draft.ingredients):
            widget_id = f"{draft.recipe_id}_{i}"
            match = catalog.normalizer.resolve(entry.original_phrase)
            if match["ingredient_id"]:
                st.write(f"{i + 1}. {entry.original_phrase} → {names[match['ingredient_id']]}")
            else:
                suggestions = match["suggestions"]
                choices = suggestions if match["status"] == "AMBIGUOUS" else list(dict.fromkeys(suggestions + ingredient_options))
                default = choices.index(entry.ingredient_id) if entry.ingredient_id in choices else None
                selected = st.selectbox(f"Match line {i + 1}: {entry.original_phrase}", choices, index=default,
                                        placeholder="Choose the ingredient you meant", format_func=names.get, key="map_" + widget_id)
                if selected:
                    confirmations[i] = selected
            essential = st.checkbox(f"Essential ingredient on line {i + 1}", value=entry.essential, key="essential_" + widget_id)
            entries.append(entry.model_copy(update={"essential": essential}))
        if st.button("Save custom recipe", type="primary"):
            try:
                confirmed = confirm_custom_recipe(draft.model_copy(update={"ingredients": entries}), catalog, confirmations)
                state["custom_recipes"][str(confirmed.recipe_id)] = confirmed
                del state["draft_recipe"]
                st.success(f"Saved {confirmed.title} in this session.")
            except ValueError as error:
                st.error(str(error))
    for key, saved in state["custom_recipes"].items():
        with st.container(border=True):
            st.subheader(saved.title)
            st.caption(f"{len(saved.ingredients)} ingredient entries · {len(saved.instructions)} instruction steps")
            st.button("Use this recipe for substitution", key="use_" + key, on_click=open_recipe, args=(key,))
            st.download_button("Download recipe JSON", export_custom_recipe(saved), file_name=f"recipe-{key}.json",
                               mime="application/json", key="download_" + key)


st.title("KitchenCompass")
page = st.sidebar.radio("Workspace", ["Pantry search", "Substitutions", "Custom recipes"], key="workspace")
st.sidebar.caption(f"{len(catalog.recipes)} recipes · {len(names)} ingredients")
st.sidebar.caption(f"Data {catalog.config['data_version']} · Model {catalog.config['config_version']}")
if page == "Pantry search":
    pantry_page()
elif page == "Substitutions":
    substitute_page()
else:
    custom_page()

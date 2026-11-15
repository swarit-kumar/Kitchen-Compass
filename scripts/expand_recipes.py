"""Reproduce the Phase 1 v2 authored recipe snapshot and curation."""
import argparse
from collections import Counter
from itertools import chain
from pathlib import Path
import re

from kitchencompass.data_io import ROOT, read_json, sha256, write_json

ORIGINAL = Path("data/raw/KitchenCompass_Recipes_v1.json")
ORIGINAL_CURATION = Path("data/curation/catalogue_v1.json")
EXPANSION = Path("data/curation/recipe_expansion_v2.txt")
SOURCE_ID = "src_kc_generated_recipes_v2"

DEFAULT_AMOUNTS = {
    "butter": "1 tbsp", "coconut oil": "1 tbsp", "ghee": "1 tbsp",
    "olive oil": "1 tbsp", "sesame oil": "1 tsp", "vegetable oil": "1 tbsp",
    "onion": "1 small, chopped", "garlic": "2 cloves, minced", "ginger": "1 tsp grated",
    "scallion": "2 sliced", "leek": "1 small leek, sliced", "celery": "1 stalk, sliced",
    "cilantro": "2 tbsp chopped", "parsley": "2 tbsp chopped", "basil": "2 tbsp torn",
    "thai basil": "2 tbsp torn", "mint": "1 tbsp chopped", "dill": "1 tbsp chopped",
    "thyme": "1 tsp fresh leaves", "curry leaf": "8 leaves", "makrut lime leaf": "3 leaves, torn",
    "lemongrass": "1 stalk, bruised", "galangal": "4 thin slices",
    "black peppercorn": "1/2 tsp crushed", "dried red chili": "1 dried chili, broken",
    "dried ancho chili": "1 small chili, stemmed and minced",
    "clove": "2 whole cloves", "green cardamom": "2 crushed pods",
    "thai chili": "1 small chili, sliced", "white pepper": "1/4 tsp ground",
    "black pepper": "1/4 tsp ground", "ground cinnamon": "1/4 tsp",
    "ground red chili": "1/4 tsp", "turmeric": "1/2 tsp",
    "tamarind paste": "1 tbsp", "lemon juice": "1 tbsp", "lime juice": "1 tbsp",
    "rice vinegar": "1 tbsp", "palm sugar": "1 tsp",
    "dried fenugreek leaf": "1 tsp crumbled", "salt": "to taste",
    "rasam powder": "1 tsp", "sambar powder": "1 1/2 tsp",
    "green curry paste": "1 1/2 tbsp", "red curry paste": "1 1/2 tbsp",
    "massaman curry paste": "1 1/2 tbsp", "curry powder": "2 tsp",
    "jamaican curry powder": "2 tsp",
    **dict.fromkeys(("cumin seed", "mustard seed", "ground cumin", "ground coriander",
                     "ground fennel", "ground ginger", "garam masala", "paprika"), "1/2 tsp"),
}

NEW_INGREDIENTS = {
    "beetroot": ("produce", ["bulk"]),
    "butternut squash": ("produce", ["bulk"]),
    "cherry tomato": ("produce", ["bulk"]),
    "cooked black bean": ("legume", ["bulk", "protein"]),
    "cooked black chickpea": ("legume", ["bulk", "protein"]),
    "cooked black eyed pea": ("legume", ["bulk", "protein"]),
    "cooked brown lentil": ("legume", ["bulk", "protein"]),
    "cooked mung bean": ("legume", ["bulk", "protein"]),
    "cooked pigeon pea": ("legume", ["bulk", "protein"]),
    "cooked turkey": ("meat", ["protein"]),
    "drumstick pod": ("produce", ["bulk"]),
    "egg noodles": ("grain", ["bulk"]),
    "fenugreek leaf": ("produce", ["aromatic", "bulk"]),
    "fenugreek seed": ("spice", ["aromatic"]),
    "green bell pepper": ("produce", ["bulk"]),
    "kale": ("produce", ["bulk"]),
    "kombu": ("seaweed", ["aromatic"]),
    "kombu stock": ("liquid", ["liquid"]),
    "leek": ("produce", ["aromatic", "bulk"]),
    "maize flour": ("grain", ["thickener"]),
    "mint": ("produce", ["aromatic"]),
    "mustard greens": ("produce", ["bulk"]),
    "okra": ("produce", ["bulk", "thickener"]),
    "pearl barley": ("grain", ["bulk"]),
    "pineapple": ("fruit", ["bulk", "sweetener"]),
    "pork shoulder": ("meat", ["protein"]),
    "radish": ("produce", ["bulk"]),
    "split chickpea": ("legume", ["bulk", "protein"]),
    "split mung bean": ("legume", ["bulk", "protein"]),
    "sweet potato": ("produce", ["bulk"]),
    "watermelon": ("fruit", ["bulk", "sweetener"]),
    "white wine vinegar": ("liquid", ["acid"]),
}

HOUSE_COMPONENTS = {
    "cherry tomato": ["tomato"],
    "cooked black chickpea": ["chickpea"],
    "cooked pigeon pea": ["split pigeon pea"],
    "egg noodles": ["egg", "water", "wheat flour"],
    "green curry paste": ["coriander seed", "garlic", "ginger", "lemongrass", "thai chili"],
    "jamaican curry powder": ["ground coriander", "ground cumin", "ground ginger", "ground red chili", "turmeric"],
    "japanese curry roux": ["curry powder", "vegetable oil", "wheat flour"],
    "kombu stock": ["kombu", "water"],
    "maize flour": ["maize"],
    "massaman curry paste": ["dried red chili", "garlic", "ground cinnamon", "ground cumin", "lemongrass"],
    "miso paste": ["salt", "soybean", "water"],
    "red curry paste": ["dried red chili", "garlic", "ginger", "lemongrass", "ground coriander"],
    "split chickpea": ["chickpea"],
}

BRAISE = {"beef chuck", "pork shoulder"}
DAL = {"red lentil", "split chickpea", "split mung bean", "split pigeon pea"}
SLOW_VEGETABLES = {"beetroot", "butternut squash", "carrot", "potato", "pumpkin", "sweet potato",
                   "pearl barley", "short grain rice", "radish", "drumstick pod"}
QUICK = {"baguette", "cheddar", "cooked black bean", "cooked black chickpea", "cooked black eyed pea",
         "cooked brown lentil", "cooked cannellini bean", "cooked chicken", "cooked chickpea",
         "cooked kidney bean", "cooked mung bean", "cooked pigeon pea", "cooked turkey",
         "dried wakame", "egg", "firm tofu", "green pea", "silken tofu", "spinach", "shrimp",
         "white fish fillet"}


def name_list(text):
    return [part.strip() for part in text.split(";") if part.strip()]


def entries(text):
    result = []
    for spec in name_list(text):
        name, sep, amount = spec.partition("=")
        result.append((name, amount if sep else DEFAULT_AMOUNTS[name]))
    return result


def recipe_id(title):
    return "rec_" + re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")


def join(names):
    if len(names) < 3:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def without(names, *excluded):
    return [name for name in names if name not in excluded]


def cook_mains(names):
    phases = []
    for group, condition in [
        (BRAISE, "until fork-tender"),
        (DAL, "until the pulses are tender"),
        (SLOW_VEGETABLES, "until tender"),
    ]:
        batch = [n for n in names if n in group]
        if batch:
            phases.append(f"Add {join(batch)} and simmer {condition}.")
    regular = [n for n in names if n not in BRAISE | DAL | SLOW_VEGETABLES | QUICK]
    if regular:
        phases.append(f"Add {join(regular)} and cook until tender.")
    quick = [n for n in names if n in QUICK and n != "egg"]
    if quick:
        phases.append(f"Add {join(quick)} toward the end and simmer gently until cooked and hot throughout.")
    if "egg" in names:
        phases.append("Add the peeled hard-boiled eggs near the end and heat through.")
    return phases


def season(finishes):
    return f"Stir in {join(finishes)} just before serving." if finishes else None


def instructions(technique, fat, aromatics, liquids, mains, finishes):
    """Assemble steps from the authored preparation and its ingredient stages."""
    seasonings = season(finishes)
    saute = f"Heat {fat} in a saucepan. Stir in {join(aromatics)} and cook gently until fragrant."
    simmer = f"Add {join(liquids)} and bring to a gentle simmer."
    normal_cook = cook_mains(mains)
    if "cheddar" in mains:
        normal_cook = cook_mains(without(mains, "cheddar"))
        normal_cook.append("Turn the heat off and stir in the grated cheddar until melted.")
    if technique == "cold":
        body = without(mains, "egg")
        steps = [f"Blend {join(body)} with {join(aromatics)} and {join(liquids)} until smooth.",
                 f"Blend in {fat} and the salt, then refrigerate the soup until cold.",
                 "Ladle into cold bowls." if "egg" not in mains else "Serve cold, topped with the chopped hard-boiled egg."]
        seasonings = season(without(finishes, "salt"))
    elif technique == "dal":
        steps = [f"Rinse any dried pulses, then simmer {join(mains)} with {join(liquids)} until tender.",
                 f"Heat {fat} separately and fry {join(aromatics)} until fragrant.",
                 "Stir the tempering into the dal and simmer briefly."]
    elif technique == "sambar":
        pulse, *veg = mains
        steps = [f"Simmer the rinsed {pulse} in the water until tender, then mash lightly.",
                 f"Add {join(veg)} and simmer until tender. Stir in the tamarind paste and sambar powder.",
                 f"Heat {fat} and fry {join(aromatics)}, then stir the tempering into the sambar."]
    elif technique == "rasam":
        steps = [f"Simmer {join(mains)} in {join(liquids)} until the aromatics in the rasam powder infuse the broth.",
                 f"Heat {fat} separately and briefly fry {join(aromatics)}.",
                 "Pour the tempering over the rasam and simmer briefly."]
    elif technique == "yogurt":
        steps = [f"Whisk {join(liquids)} until smooth.",
                 saute, "Pour in the yogurt mixture while stirring and bring it to a gentle simmer.",
                 f"Add {join(mains)} and cook on low heat until tender and the kadhi lightly coats a spoon."]
    elif technique == "saag":
        greens = [n for n in mains if n in {"spinach", "mustard greens", "fenugreek leaf"}]
        rest = [n for n in mains if n not in greens]
        steps = [saute, f"Add {join(greens)} and {join(liquids)}. Cover and simmer until the greens are tender.",
                 *cook_mains(rest)]
        if "maize flour" in finishes:
            steps.append("Mash the greens, then whisk in the maize flour and simmer until the mixture thickens.")
            seasonings = season(without(finishes, "maize flour"))
    elif technique in {"butter", "korma"}:
        creamy_base = [n for n in liquids if n not in {"water", "plain yogurt"}]
        steps = [saute, f"Simmer {join(creamy_base)} with the water until the cashews soften, then blend the base smooth."]
        if "plain yogurt" in liquids:
            steps.append("Return the base to low heat and whisk in the plain yogurt without boiling.")
        steps += normal_cook
    elif technique == "mustard":
        steps = [f"Grind {join(aromatics)} with some of the water to form a paste.",
                 f"Heat {fat}, fry the paste briefly and add the remaining water.",
                 *normal_cook]
    elif technique == "japanese":
        steps = [saute, "Add the vegetable stock and simmer.", *normal_cook,
                 "Turn the heat low, dissolve the curry roux in the hot broth and stir until the sauce thickens."]
    elif technique == "miso":
        steps = [saute, "Add the kombu stock and bring to a gentle simmer.", *normal_cook,
                 "Dissolve the miso paste in a ladleful of hot broth, stir it back in and turn off the heat."]
    elif technique == "chowder":
        steps = [saute, "Stir in the flour for a minute, then gradually whisk in the milk and vegetable stock.",
                 *normal_cook]
    elif technique == "slurry":
        steps = [saute, "Add the vegetable stock, reserving a few cold spoonfuls for the slurry.",
                 *normal_cook,
                 "Mix the cornstarch with the reserved stock and stir it into the simmering soup until lightly thickened."]
        if "egg" in finishes:
            steps.append("Drizzle in the beaten egg while stirring and simmer until the egg is set.")
            seasonings = season(without(finishes, "egg"))
    elif technique == "covered":
        steps = [saute, f"Add {join(mains)} and {join(liquids)}. Cover and cook over low heat until tender.",
                 "Uncover and stir over low heat until the liquid has mostly evaporated."]
    else:
        steps = [saute, simmer, *normal_cook]
        if technique == "puree":
            steps.append("Blend the cooked soup until smooth and return it to low heat.")
        if technique in {"thai", "thai_soup"}:
            fibrous = [n for n in aromatics if n in {"lemongrass", "galangal", "makrut lime leaf"}]
            if fibrous:
                steps.append(f"Remove the large pieces of {join(fibrous)} before serving.")
    if "boneless chicken thigh" in mains:
        steps.append("Check that the chicken reaches 74°C (165°F) in its thickest piece.")
    if "white fish fillet" in mains:
        steps.append("Cook the fish to 63°C (145°F) at its thickest point.")
    if "shrimp" in mains:
        steps.append("Check that the shrimp is opaque throughout before serving.")
    if seasonings:
        steps.append(seasonings)
    return steps


def add_group_rows(raw, curation, file_path):
    for name, (category, roles) in NEW_INGREDIENTS.items():
        curation["ingredient_metadata"][name] = {"category": category, "roles": roles}
    for name, values in HOUSE_COMPONENTS.items():
        curation["component_definitions"][name] = sorted(values)
    for name, aliases in {"beetroot": ["beet", "beets"], "egg noodles": ["egg noodle"],
                          "drumstick pod": ["moringa pod"], "radish": ["mooli"]}.items():
        curation["alias_overrides"][name] = sorted(aliases)

    known_recipe_ids = {row["recipe_id"] for row in raw["recipes"]}
    original_titles = {row["title"]: row["recipe_id"] for row in raw["recipes"]}
    groups = {}
    for number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            group_id, cuisine, family, method, fat, aromatic, liquid, finish, links = line[1:].split("|")
            if group_id in groups:
                raise ValueError(f"Duplicate group on line {number}")
            group = [original_titles[title] for title in name_list(links)]
            groups[group_id] = group
            continue
        title, main, extra_finish, essentials = line.split("|")
        key = recipe_id(title)
        if key in known_recipe_ids:
            raise ValueError(f"Duplicate recipe ID at line {number}: {key}")
        known_recipe_ids.add(key)
        group.append(key)
        quantities = {}
        for name, amount in chain.from_iterable(map(entries, (fat, aromatic, liquid, main, finish, extra_finish))):
            if name not in curation["ingredient_metadata"]:
                raise ValueError(f"No metadata for {name!r} on line {number}")
            if name not in quantities:
                quantities[name] = amount
            else:
                quantities[name] += f" + {amount}"
        selected = name_list(essentials)
        if not selected or set(selected) - quantities.keys():
            raise ValueError(f"Unknown or missing essential ingredient at line {number}")
        stages = [[name for name, _ in entries(stage)] for stage in (aromatic, liquid, main, finish, extra_finish)]
        aromatics, liquids, mains, finishes, extra = stages
        if method != "cold":
            cooked_extras = [
                name for name in extra
                if name in {"ginger", "garlic"} or curation["ingredient_metadata"][name]["category"] == "spice"
            ]
            aromatics = list(dict.fromkeys(aromatics + cooked_extras))
            extra = without(extra, *cooked_extras)
        if method in {"dal", "sambar"} and "tomato" in extra:
            mains.append("tomato")
            extra = without(extra, "tomato")
        steps = instructions(method, entries(fat)[0][0], aromatics, liquids, mains, list(dict.fromkeys(finishes + extra)))
        raw["recipes"].append({
            "recipe_id": key, "title": title, "cuisine_label": cuisine, "dish_family": family,
            "ingredients": [
                {"original_phrase": f"{name} ({amount})", "ingredient_name_hint": name,
                 "quantity_text": amount, "compound_review_required": name in HOUSE_COMPONENTS}
                for name, amount in quantities.items()
            ],
            "instructions": steps, "source_ref": SOURCE_ID,
        })
        curation["essential_by_recipe"][key] = {
            name: "Defines the named ingredient, base or preparation style." for name in selected
        }
    curation["recipe_groups"].extend(groups.values())
    return len(groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare the reconstructed snapshots without writing")
    args = parser.parse_args()
    raw = read_json(ROOT / ORIGINAL)
    curation = read_json(ROOT / ORIGINAL_CURATION)
    old_total = len(raw["recipes"])
    groups = add_group_rows(raw, curation, ROOT / EXPANSION)
    source = raw.pop("source")
    source["local_filename"] = ORIGINAL.as_posix()
    source["locator"] = "Original recipes array, copied without edits into the v2 snapshot"
    raw.update(data_version="2.0", sources=[source, {
        "source_id": SOURCE_ID, "title": "KitchenCompass authored expansion",
        "local_filename": EXPANSION.as_posix(), "locator": "Recipe variants and grouped preparation templates",
        "origin": "AI-assisted recipe drafts created for the course project",
        "independent_source_reviewed": False, "cooking_tested": False,
    }], parent_snapshot={"filename": ORIGINAL.as_posix(), "sha256": sha256(ROOT / ORIGINAL)})
    raw["coverage"] = {
        "original_records": old_total,
        "added_records": len(raw["recipes"]) - old_total,
        "authored_style_groups": groups,
        "raw_by_family": dict(Counter(r["dish_family"] for r in raw["recipes"])),
    }
    raw["usage_notes"] = [
        "This catalogue combines AI-assisted recipe drafts and named variants.",
        "It is a development corpus, and recipe frequencies are not observational culinary data.",
        "Keep related variants together for evaluation and verify ingredient formulations before team sign-off.",
    ]
    outputs = {
        ROOT / "data/raw/KitchenCompass_Recipes_v2.json": raw,
        ROOT / "data/curation/catalogue.json": curation,
    }
    if not args.check and any(path.exists() for path in outputs):
        raise SystemExit("An output already exists; use --check for the immutable release snapshots.")
    for path, payload in outputs.items():
        if args.check:
            if read_json(path) != payload:
                raise SystemExit(f"{path.relative_to(ROOT)} differs from the authored snapshot")
        else:
            write_json(path, payload)
    print(f"Recipe expansion: {len(raw['recipes']) - old_total} authored variants in {groups} style groups")


if __name__ == "__main__":
    main()

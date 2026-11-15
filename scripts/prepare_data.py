"""Build canonical recipes, ingredients, evidence, audit and grouped splits."""
import argparse

from kitchencompass.data_io import ROOT, read_json
from kitchencompass.prepare import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/settings.json")
    args = parser.parse_args()
    audit = prepare(read_json(ROOT / args.config))
    print(f"Active catalogue: {audit['active_recipes']} recipes, {audit['active_ingredients']} ingredients")
    print(f"FlavorDB profiles: {audit['flavor_profiles_available']} available")
    print(f"Recipe splits: {audit['split_recipe_counts']}")


if __name__ == "__main__":
    main()

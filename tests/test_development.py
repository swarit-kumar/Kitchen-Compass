from kitchencompass.catalog import load_jsonl
from kitchencompass.data_io import ROOT, read_json
from kitchencompass.service import get_catalog
from scripts.evaluate import evaluate, summarize


def test_published_development_runs_reproduce_without_grades():
    cat = get_catalog()
    cases = load_jsonl(ROOT / "data/benchmark/dev_cases.jsonl")
    splits = read_json(ROOT / "data/benchmark/splits.json")
    pantry, subs = evaluate(cat, cases, set(splits["recipes"]["dev"]))
    assert pantry == read_json(ROOT / "results/development_pantry.json")
    assert subs == read_json(ROOT / "results/development_substitution.json")
    assert len(pantry["cases"]) == 5 and len(subs["cases"]) == 6
    for mode in subs["summaries"]["all_evidence"].values():
        assert mode["hard_constraint_violations"] == 0
        assert mode["hit_at_3"] is None
    assert all(case["recipe_id"] in splits["recipes"]["dev"] for case in subs["cases"])


def test_quality_metrics_include_eligible_abstentions_as_zero():
    def fixture(ids):
        return {"grades": {"a": 1, "b": 2}, "audit": {"candidate_ids": ["a", "b"]},
                "independent_allowed_ids": ["a", "b"], "all_evidence": {"full": {"items": [{"candidate_id": k} for k in ids]}}}
    result = summarize([fixture(["a", "b"]), fixture([])], "full", "all_evidence")
    assert result["hit_at_3"] == .5 and result["mrr_at_5"] == .25
    assert result["abstention_rate"] == .5 and result["candidate_generation_recall"] == 1

"""Regression checks for the frozen experiment and grading workflow."""
import csv
from copy import deepcopy
from unittest.mock import patch

import pytest

from kitchencompass.annotations import freeze_labels, inspect_reviews, make_worksheets, verified_labels
from kitchencompass.benchmark import BASE, CASE_FILES, csv_text, validate_cases, verify_protocol
from kitchencompass.catalog import Catalog, load_jsonl
from kitchencompass.data_io import ROOT, read_json, write_json, write_text
from kitchencompass.experiments import option_key
from kitchencompass.experiment_metrics import dcg, group_interval, measure_case
from scripts.evaluate import publish


@pytest.fixture(scope="module")
def catalog():
    return Catalog()


def all_cases():
    return [c for f in CASE_FILES for c in load_jsonl(BASE/f)]


def test_frozen_design_and_no_group_leakage(catalog):
    rows = all_cases()
    verify_protocol()
    validate_cases(rows, catalog)
    assert len(rows) == 150
    assert sum(len(r["reviewers"]) == 2 for r in rows) >= 45
    groups = {s: {r["duplicate_group_id"] for r in rows if r["split"] == s} for s in ("test","dev")}
    train = read_json(ROOT/"data/benchmark/splits.json")["groups"]["train"]
    assert not groups["dev"].intersection(groups["test"]) and not set(train) & (groups["dev"] | groups["test"])
    changed = deepcopy(rows)
    changed[75]["duplicate_group_id"] = changed[0]["duplicate_group_id"]
    with pytest.raises(ValueError, match="mismatch"):
        validate_cases(changed, catalog)


def test_reproducible_published_dev(tmp_path):
    publish("dev", output=tmp_path)
    for name in ("per_case.jsonl", "summary.csv", "metrics.json"):
        assert (tmp_path/name).read_bytes() == (ROOT/"results"/name).read_bytes()
    report = read_json(tmp_path/"metrics.json")
    assert report["accepted_output_violations"] == 0


def test_label_gate_precedes_any_test_ranking(tmp_path):
    if (BASE/"labels_lock.json").exists():
        pytest.skip("Release already has frozen human grades.")
    with patch("scripts.evaluate.run_case", side_effect=AssertionError("Premature test evaluation")):
        with pytest.raises(ValueError, match="human grades"):
            publish("test", output=tmp_path)
    assert not list(tmp_path.iterdir())


def test_changed_frozen_inputs_are_rejected(tmp_path):
    for name in CASE_FILES:
        (tmp_path/name).write_bytes((BASE/name).read_bytes())
    (tmp_path/"protocol_lock.json").write_bytes((BASE/"protocol_lock.json").read_bytes())
    (tmp_path/CASE_FILES[0]).write_text("changed")
    with pytest.raises(ValueError, match="Frozen inputs"):
        verify_protocol(tmp_path)


def put_grade(path, grade):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    rows[0].update(grade=str(grade), rationale="Synthetic grade to exercise software", evidence_ref="fixture line 1",
                   evidence_type="recipe_practicality")
    write_text(path, csv_text(list(rows[0]), rows))


def test_review_reconcile_freeze_and_tamper(tmp_path, catalog):
    # Isolated software fixture. These synthetic grades never enter the project benchmark.
    row = deepcopy(all_cases()[0])
    row.update(case_id="fixture_only", reviewers=["Vibhu","Swarit"], exclusions=[], candidate_options=[
        {"candidate_id": "o01", "recipe_id": row["recipe_id"]}])
    rows = [row]
    write_json(tmp_path/"protocol_lock.json", {"fixture":True})
    make_worksheets(rows, catalog, tmp_path)
    folder = tmp_path/"reviews"
    put_grade(folder/"Vibhu.csv", 2)
    with pytest.raises(ValueError, match="incomplete"):
        freeze_labels(rows,catalog,tmp_path)
    put_grade(folder/"Swarit.csv", 1)
    progress, _ = inspect_reviews(rows,catalog,tmp_path,reconcile=True)
    assert progress["unresolved_disagreements"] == 1 and progress["agreement_before_reconciliation"] == 0
    put_grade(folder/"reconciliation.csv", 2)
    sealed = freeze_labels(rows,catalog,tmp_path)
    assert verified_labels(rows,catalog,tmp_path) == sealed
    assert sealed["cases"]["fixture_only"][row["recipe_id"]]["judgment"]["grade"] == 2
    put_grade(folder/"reconciliation.csv", 1)
    with pytest.raises(ValueError, match="existing label freeze"):
        verified_labels(rows,catalog,tmp_path)


def test_positive_grade_for_excluded_option_rejected(tmp_path,catalog):
    row = deepcopy(all_cases()[0])
    row["reviewers"] = ["Vibhu"]
    row["exclusions"] = [catalog.recipes[row["recipe_id"]]["ingredients"][0]["ingredient_id"]]
    row["candidate_options"] = [{"candidate_id":"o01", "recipe_id":row["recipe_id"]}]
    make_worksheets([row],catalog,tmp_path)
    put_grade(tmp_path/"reviews/Vibhu.csv", 1)
    with pytest.raises(ValueError, match="constraint violation"):
        inspect_reviews([row],catalog,tmp_path)


def scored(task, keys, grades, population="all", audit=None):
    def option(key):
        return {"recipe_id":key} if task=="pantry" else {"replacements":{"t":key}}
    labels = {option_key(option(k)):{"judgment":{"grade":g}} for k,g in grades.items()}
    m = {"method":"weighted" if task=="pantry" else "full", "population":population,
         "items":[{"option":option(k), "missing_count":2, "errors":[]} for k in keys]}
    row = {"case_id":"fixture", "methods":[m],"audit":audit or {}, "task_type":task,"targets":["t"]}
    return measure_case(row,labels)["methods"][0]["measures"]


def test_true_ndcg_uses_pooled_ideal():
    assert scored("pantry",["b","a"],{"a":2,"b":1,"c":2})["ndcg_at_5"] == pytest.approx(dcg([1,2])/dcg([2,2,1]))
    assert scored("pantry",[],{"a":2})["ndcg_at_5"] == 0
    assert scored("pantry",[],{"a":0})["ndcg_at_5"] is None


def test_single_quality_abstentions_partial_pool_and_missing_grades():
    audit = {"candidate_ids":["a","b"], "complete_evidence_ids":[]}
    m = scored("single",["b","a"],{"a":2,"b":1,"c":2},audit=audit)
    assert (m["hit_at_3"],m["mrr_at_5"],m["top3_mean_grade"],m["candidate_generation_recall"]) == (1,.5,1.5,.5)
    assert scored("single",[],{"a":2},audit=audit)["mrr_at_5"] == 0
    assert not scored("single",[],{"a":2},"complete_evidence",audit)["included"]
    with pytest.raises(ValueError, match="outside frozen"):
        scored("single",["unknown"],{"a":2},audit=audit)


def test_bootstrap_resamples_whole_groups():
    assert group_interval([("same",1)]*10) is None
    values = [(str(i),0.5) for i in range(6)]
    assert group_interval(values) == [0.5,0.5]
    values.append(("0",0))
    assert group_interval(values) == group_interval(values)


def test_joint_human_hit_rejects_invalid_independent_choice():
    target = {"replacements":{"t":"a","u":"b"}}
    duplicate = {"replacements":{"t":"a","u":"a"}}
    labels = {option_key(target):{"judgment":{"grade":2}}, option_key(duplicate):{"judgment":{"grade":0}}}
    row = {"case_id":"fixture","audit":{},"task_type":"joint","targets":["t","u"],"methods":[
        {"method":"joint","population":"all","items":[{"option":target,"score":0.7,"errors":[]}]},
        {"method":"independent","population":"all","items":[{"option":duplicate,"score":None,
         "duplicate_replacement":True,"errors":["Duplicate"]}]}]}
    a,b = measure_case(row,labels)["methods"]
    assert a["measures"]["grade2_hit_at_3"] == 1 and a["measures"]["joint_score_difference"] is None
    assert b["measures"]["grade2_hit_at_3"] == 0 and b["measures"]["violations"] == 1

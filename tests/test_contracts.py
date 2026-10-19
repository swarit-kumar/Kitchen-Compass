
from kitchencompass.schemas import Result


def test_result_contract():
    result = Result(status="OK", items=[], schema_version="1.0")
    assert result.status == "OK"
    assert result.items == []
    assert result.schema_version == "1.0"


def test_empty_pantry_status_can_be_represented():
    result = Result(status="NEEDS_INPUT")
    assert result.status == "NEEDS_INPUT"


def test_impossible_request_status_can_be_represented():
    result = Result(status="NO_FEASIBLE_RESULT")
    assert result.items == []
    assert result.status == "NO_FEASIBLE_RESULT"

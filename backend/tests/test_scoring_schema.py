import pytest
from pydantic import ValidationError

from services.scoring_schema import ScoringConfig

VALID_CONFIG = {
    "id": "test",
    "version": "1",
    "name": "Test Framework",
    "scale": {"min": 1, "max": 10},
    "dimensions": [
        {
            "id": "dim_a",
            "name": "Dimension A",
            "description": "Tests A.",
            "weight": 2,
            "rubric": [{"min_score": 1, "max_score": 10, "label": "Any", "description": "Any score."}],
            "rag_thresholds": {"red_max": 4, "amber_max": 7},
        },
        {
            "id": "dim_b",
            "name": "Dimension B",
            "description": "Tests B.",
            "weight": 1,
            "rubric": [{"min_score": 1, "max_score": 10, "label": "Any", "description": "Any score."}],
            "rag_thresholds": {"red_max": 4, "amber_max": 7},
        },
    ],
    "cta_text": "Talk to us.",
}


def test_valid_config_parses():
    config = ScoringConfig.model_validate(VALID_CONFIG)
    assert config.id == "test"
    assert len(config.dimensions) == 2


def test_duplicate_dimension_ids_rejected():
    bad = {**VALID_CONFIG, "dimensions": [VALID_CONFIG["dimensions"][0], VALID_CONFIG["dimensions"][0]]}
    with pytest.raises(ValidationError):
        ScoringConfig.model_validate(bad)


def test_empty_dimensions_rejected():
    bad = {**VALID_CONFIG, "dimensions": []}
    with pytest.raises(ValidationError):
        ScoringConfig.model_validate(bad)


def test_overall_score_weighted_average():
    config = ScoringConfig.model_validate(VALID_CONFIG)
    # dim_a weight 2, score 10; dim_b weight 1, score 1 -> weighted avg = (20+1)/3 = 7
    # normalised to 0-100 over scale 1-10: (7-1)/9*100 = 66.7
    overall = config.overall_score({"dim_a": 10, "dim_b": 1})
    assert overall == 66.7


def test_overall_score_all_max_is_100():
    config = ScoringConfig.model_validate(VALID_CONFIG)
    assert config.overall_score({"dim_a": 10, "dim_b": 10}) == 100.0


def test_overall_score_all_min_is_0():
    config = ScoringConfig.model_validate(VALID_CONFIG)
    assert config.overall_score({"dim_a": 1, "dim_b": 1}) == 0.0


@pytest.mark.parametrize("score,expected", [(1, "red"), (4, "red"), (5, "amber"), (7, "amber"), (8, "green"), (10, "green")])
def test_rag_band_thresholds(score, expected):
    config = ScoringConfig.model_validate(VALID_CONFIG)
    assert config.rag_band("dim_a", score) == expected

import pytest

from services.client_config import list_frameworks, load_report_template, load_scoring_config


def test_demo_config_loads_and_validates():
    config = load_scoring_config("demo", "demo")
    assert config.id == "demo"
    assert {d.id for d in config.dimensions} == {"business_fundamentals", "investment_case", "investor_presentation"}


def test_fg_placeholder_config_loads_and_validates():
    # Scaffold only — placeholder dimensions, per the brief. This just proves the
    # scaffold is structurally valid, not that its content is real.
    config = load_scoring_config("fg", "4t")
    assert config.id == "4t"
    assert len(config.dimensions) == 4


def test_list_frameworks():
    assert list_frameworks("demo") == ["demo"]
    assert list_frameworks("fg") == ["4t"]


def test_list_frameworks_unknown_client_returns_empty():
    assert list_frameworks("nonexistent-client") == []


def test_load_scoring_config_requires_explicit_framework_for_unknown_id():
    with pytest.raises(ValueError):
        load_scoring_config("demo", "not-a-real-framework")


def test_demo_report_template_exists():
    html = load_report_template("demo")
    assert "{{ company_name }}" in html


def test_fg_report_template_not_yet_scaffolded():
    with pytest.raises(FileNotFoundError):
        load_report_template("fg")

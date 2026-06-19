from dataclasses import dataclass

from app.gui.mining.scan_id_helpers import (
    format_scan_match_summary,
    match_scan_values,
    parse_scan_query,
    query_has_filters,
    scan_signature_matches,
)


@dataclass(frozen=True)
class ScanSignatureStub:
    resource: str
    values: tuple[int, ...]


def parse_int(value):
    try:
        return int(value.replace(",", ""))
    except (AttributeError, TypeError, ValueError):
        return None


def format_values(values):
    return " | ".join(f"{value:,}" for value in values)


def test_parse_scan_query_supports_resources_and_numeric_ranges():
    query = parse_scan_query("Gold, 5200, ~5000, 8000-9000", parse_int)

    assert query["resource_terms"] == ("gold",)
    assert query["numeric_ranges"] == (
        (5200, 5200),
        (4500, 5500),
        (8000, 9000),
    )
    assert query_has_filters(query)


def test_scan_signature_matches_resource_names_without_numeric_values():
    query = parse_scan_query("gold", parse_int)
    signature = ScanSignatureStub("Gold", (4380, 5200, 8875))

    name_match, numeric_matches = scan_signature_matches(signature, query)

    assert name_match is True
    assert numeric_matches == []


def test_scan_signature_matches_mixed_resource_and_value_terms():
    query = parse_scan_query("Taranite, 5200", parse_int)
    signature = ScanSignatureStub("Gold", (4380, 5200, 8875))

    name_match, numeric_matches = scan_signature_matches(signature, query)

    assert name_match is False
    assert numeric_matches == [5200]
    assert format_scan_match_summary(name_match, numeric_matches, format_values) == "5,200"


def test_scan_signature_summary_combines_resource_and_value_matches():
    query = parse_scan_query("Gold, 5200", parse_int)
    signature = ScanSignatureStub("Gold", (4380, 5200, 8875))

    name_match, numeric_matches = scan_signature_matches(signature, query)

    assert format_scan_match_summary(name_match, numeric_matches, format_values) == "Resource match | 5,200"


def test_scan_value_matches_are_deduplicated_across_overlapping_ranges():
    query = parse_scan_query("5000-5500, ~5200, 5200", parse_int)

    assert match_scan_values((5200, 5300, 7000), query["numeric_ranges"]) == [5200, 5300]

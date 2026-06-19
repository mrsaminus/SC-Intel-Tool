from app.gui.mining.refinery_helpers import (
    calculate_refinery_yield_value,
    canonical_refinery_material,
    format_refinery_duration,
    is_material_in_choices,
    parse_refinery_duration_seconds,
    refinery_material_code,
    refinery_material_value_from_price,
    refinery_option_key,
)


def parse_float(value):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def test_refinery_duration_parser_accepts_minutes_and_hms():
    assert parse_refinery_duration_seconds("", parse_float) == 0
    assert parse_refinery_duration_seconds("90", parse_float) == 5400
    assert parse_refinery_duration_seconds("1.5", parse_float) == 90
    assert parse_refinery_duration_seconds("05:30", parse_float) == 330
    assert parse_refinery_duration_seconds("01:02:03", parse_float) == 3723
    assert parse_refinery_duration_seconds("bad", parse_float) == 0
    assert parse_refinery_duration_seconds("bad:input:value:extra", parse_float) == 0
    assert format_refinery_duration(3723) == "01:02:03"
    assert format_refinery_duration("") == "00:00:00"


def test_refinery_material_helpers_preserve_existing_aliases_and_keys():
    choices = (("CTRS", "Construction Pieces"),)

    assert refinery_material_code("Construction Pieces", choices) == "CTRS"
    assert refinery_material_code("Quantanium", choices) == "QUAN"
    assert canonical_refinery_material("Quantanium") == "Quantainium"
    assert refinery_option_key("ARC-L1: Wide Forest") == "arc l1 wide forest"
    assert is_material_in_choices("Construction Pieces", choices) is True
    assert is_material_in_choices("Diamond", choices) is False


def test_refinery_value_and_yield_helpers_match_existing_math():
    assert refinery_material_value_from_price("250", "1000", parse_float) == 2500.0
    assert calculate_refinery_yield_value(1000, 0.2, station_bonus=0.1, salvage_multiplier=0.5) == 110.0
    assert calculate_refinery_yield_value(0, 0.2) == 0.0
    assert calculate_refinery_yield_value(1000, 0) == 0.0

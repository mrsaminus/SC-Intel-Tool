from dataclasses import dataclass

from app.gui.bp_overview.reward_scanner_matching import (
    match_blueprint_text,
    normalize_match_text,
    scan_region_for_blueprint_text,
    token_overlap_score,
)


@dataclass(frozen=True)
class BlueprintStub:
    key: str
    blueprint_name: str


def test_normalize_match_text_removes_ocr_noise():
    assert normalize_match_text("  Field-Recon: Helmet!! ") == "field recon helmet"


def test_reward_scanner_prefers_exact_blueprint_match():
    blueprints = [
        BlueprintStub("field-recon-helmet", "Field Recon Helmet"),
        BlueprintStub("field-recon-core", "Field Recon Core"),
    ]

    matches = match_blueprint_text("Reward unlocked: Field Recon Helmet", blueprints)

    assert matches[0]["blueprint"].key == "field-recon-helmet"
    assert matches[0]["match_type"] == "exact"
    assert matches[0]["confidence"] == 1.0


def test_reward_scanner_keeps_token_overlap_below_confirmation_for_weak_matches():
    assert token_overlap_score("field recon helmet", "field recon") < 0.75


def test_reward_scanner_handles_blank_ocr_text_without_matches():
    blueprints = [BlueprintStub("field-recon-helmet", "Field Recon Helmet")]

    assert match_blueprint_text(" \n\t ", blueprints) == []


def test_reward_scanner_limits_and_orders_ambiguous_matches():
    blueprints = [
        BlueprintStub("field-recon-core", "Field Recon Core"),
        BlueprintStub("field-recon-helmet", "Field Recon Helmet"),
        BlueprintStub("field-recon-arms", "Field Recon Arms"),
    ]

    matches = match_blueprint_text("Field Recon", blueprints, limit=2)

    assert len(matches) == 2
    assert [match["blueprint"].blueprint_name for match in matches] == [
        "Field Recon Arms",
        "Field Recon Core",
    ]


def test_scan_region_for_blueprint_text_uses_injected_capture_and_ocr():
    blueprints = [BlueprintStub("field-recon-helmet", "Field Recon Helmet")]
    captured_regions = []

    def capture(region):
        captured_regions.append(region)
        return object()

    result = scan_region_for_blueprint_text(
        (10, 20, 300, 120),
        blueprints,
        capture_function=capture,
        ocr_function=lambda image: "Reward: Field Recon Helmet",
    )

    assert captured_regions == [(10, 20, 300, 120)]
    assert result["status"] == "ok"
    assert result["blueprint_count"] == 1
    assert result["text"] == "Reward: Field Recon Helmet"
    assert result["matches"][0]["blueprint"].key == "field-recon-helmet"


def test_scan_region_for_blueprint_text_reports_capture_error():
    def capture(region):
        raise RuntimeError("screen unavailable")

    result = scan_region_for_blueprint_text(
        (10, 20, 300, 120),
        [BlueprintStub("field-recon-helmet", "Field Recon Helmet")],
        capture_function=capture,
        ocr_function=lambda image: "unused",
    )

    assert result["status"] == "capture_error"
    assert "screen unavailable" in result["message"]
    assert result["matches"] == []


def test_scan_region_for_blueprint_text_reports_ocr_error():
    def ocr(image):
        raise RuntimeError("ocr unavailable")

    result = scan_region_for_blueprint_text(
        (10, 20, 300, 120),
        [BlueprintStub("field-recon-helmet", "Field Recon Helmet")],
        capture_function=lambda region: object(),
        ocr_function=ocr,
    )

    assert result["status"] == "ocr_error"
    assert "ocr unavailable" in result["message"]
    assert result["matches"] == []

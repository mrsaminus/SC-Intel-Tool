from app.wikelo_client import parse_wikelo_sheet, sheet_updated


def ships_47_special_rows():
    return [
        ["", "Wikelo Sheet: Ships 4.7 Updated: 2026-03-26: 4.7"],
        ["", "", "Idris-P", "#", "Component", "", "Class", "", "", "Idris Costs Continued:"],
        ["", "", "", "", "", "", "", "", "", "50x MG Scrip\n50x Ace Interceptor Helmet\n5x RCMBNT-PWL-1"],
        [
            "",
            "Credit: Camera",
            "Reputation: Very Best Customer (999 Reputation) thanks Oshida\n"
            "Cost:\n"
            "50x Wikelo Favor\n"
            "50x Polaris Bit\n"
            "50x DCHS-05 Orbital Positioning Comp-Board\n"
            "50x Carinite\n"
            "50x Irradiated Valakkar Fang (Apex)\n"
            "Continued",
        ],
        ["", "Mission: Now make Polaris. Short Time Deal."],
        ["", "", "", "", "", "", "", "", "", "The Wikelo Polaris has a unique tan/gold skin"],
        ["", "Mission Turn-In Materials/Items"],
        ["", "50x Wikelo Favors", "", "15x UEE 6th Platoon Medal (Pristine)", "", "", "", "", "", "1x RCMBNT-XTL-3"],
        ["", "15x Polaris Bits", "", "15x Carinite (Pure)", "", "", "", "", "", "1x RCMBNT-PWL-1"],
        ["", "10x DCHS-05 Comp-Board", "", "15x ASD Secure Drive", "", "", "", "", "", "1x RCMBNT-RGL-1"],
        ["", "Where to Source Materials"],
    ]


def test_wikelo_ships_special_layout_includes_idris_and_polaris():
    items = parse_wikelo_sheet("Ships 4.7", ships_47_special_rows())
    by_name = {item.item_name: item for item in items}

    assert set(by_name) == {"Idris-P", "Polaris"}
    assert by_name["Idris-P"].mission_name == "Very Best Customer (999 Reputation) thanks Oshida"
    assert by_name["Idris-P"].updated == "2026-03-26 / 4.7"
    assert "Polaris Bit" in {requirement.name for requirement in by_name["Idris-P"].requirements}
    assert "MG Scrip" in {requirement.name for requirement in by_name["Idris-P"].requirements}

    assert by_name["Polaris"].mission_name == "Now make Polaris. Short Time Deal."
    assert by_name["Polaris"].updated == "2026-03-26 / 4.7"
    polaris_requirements = {requirement.name for requirement in by_name["Polaris"].requirements}
    assert "Polaris Bits" in polaris_requirements
    assert "RCMBNT-XTL-3" in polaris_requirements


def test_wikelo_sheet_updated_reads_date_and_patch():
    assert sheet_updated(ships_47_special_rows()) == "2026-03-26 / 4.7"

from app.blueprints_client import parse_mission
from app.gui.bp_overview.shared import format_mission_context_line, mission_context_parts


def test_parse_mission_preserves_real_context_fields():
    mission = parse_mission({
        "name": "Supply Requisition",
        "drop_chance": "12%",
        "contractor": {"name": "Covalex"},
        "reputation": {"displayName": "Covalex Shipping"},
        "reputation_rank": "Junior Contractor",
        "location": {"name": "Area18"},
        "system": "Stanton",
    })

    assert mission.name == "Supply Requisition"
    assert mission.drop_chance == "12%"
    assert mission.contractor == "Covalex"
    assert mission.reputation_giver == "Covalex Shipping"
    assert mission.reputation_rank == "Junior Contractor"
    assert mission.location == "Area18"
    assert mission.system == "Stanton"

    parts = mission_context_parts(mission)
    assert "Contractor: Covalex" in parts
    assert "Reputation: Covalex Shipping (Junior Contractor)" in parts
    assert "Location: Area18" in parts
    assert "System: Stanton" in parts
    assert "Drop chance: 12%" in parts


def test_mission_context_does_not_invent_missing_fields():
    mission = parse_mission({
        "name": "Claim Blueprint",
        "drop_chance": "5%",
    })

    assert mission_context_parts(mission) == ["Drop chance: 5%"]
    assert format_mission_context_line(mission) == "- Claim Blueprint | Drop chance: 5%"


def test_mission_context_line_stays_minimal_without_context():
    mission = parse_mission({"name": "Claim Blueprint"})

    assert mission_context_parts(mission) == []
    assert format_mission_context_line(mission) == "- Claim Blueprint"

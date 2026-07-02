from app.hauling import (
    CONTRACT_STATE_DELIVERED,
    CONTRACT_STATE_LOADED,
    CONTRACT_STATE_PLANNED,
    HaulingContract,
    build_manifest,
    capacity_remaining,
    completion_percentage,
    delivered_scu,
    group_by_destination,
    group_by_pickup,
    group_by_route,
    group_summary,
    loaded_scu,
    parse_hauling_contracts,
    remaining_capacity,
    remaining_deliveries,
    remaining_pickups,
    ship_capacity_scu,
    sort_contracts,
    toggle_delivered_state,
    toggle_loaded_state,
    total_scu,
    validate_capacity,
    with_contract_state,
)
from app.hauling.parser import HaulingContractParser


SIMPLE_CONTRACT_TEXT = """
Pick up:
Checkmate

Deliver to:
Teasa Spaceport

Commodity:
Construction Materials

Quantity:
32 SCU

Reward:
12,000 aUEC
"""


def test_parse_simple_hauling_contract_text():
    contracts = parse_hauling_contracts(SIMPLE_CONTRACT_TEXT)

    assert len(contracts) == 1
    contract = contracts[0]
    assert contract.pickup == "Checkmate"
    assert contract.delivery == "Teasa Spaceport"
    assert contract.commodity == "Construction Materials"
    assert contract.scu == 32
    assert contract.reward == 12000
    assert contract.status == "parsed"
    assert contract.state == CONTRACT_STATE_PLANNED
    assert contract.confidence == 1.0


def test_parse_compact_hauling_contract_text():
    contracts = parse_hauling_contracts(
        "Pick up: Checkmate Deliver to: Teasa Spaceport Commodity: Agricium Quantity: 8 SCU"
    )

    assert len(contracts) == 1
    assert contracts[0].pickup == "Checkmate"
    assert contracts[0].delivery == "Teasa Spaceport"
    assert contracts[0].commodity == "Agricium"
    assert contracts[0].scu == 8


def test_parse_multiple_hauling_contracts():
    contracts = parse_hauling_contracts(
        """
        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU

        Pick up: Seraphim Station
        Deliver to: Orison
        Commodity: Medical Supplies
        Quantity: 12 SCU
        """
    )

    assert len(contracts) == 2
    assert [contract.pickup for contract in contracts] == ["Checkmate", "Seraphim Station"]
    assert total_scu(contracts) == 44


def test_parse_duplicate_hauling_contract_blocks_get_unique_ids():
    contracts = parse_hauling_contracts(
        """
        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU

        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU
        """
    )

    assert len(contracts) == 2
    assert contracts[0].id != contracts[1].id
    assert [contract.scu for contract in contracts] == [32, 32]


def test_parse_missing_pickup_warns_and_keeps_candidate():
    contracts = parse_hauling_contracts(
        """
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU
        """
    )

    assert len(contracts) == 1
    assert contracts[0].pickup == ""
    assert contracts[0].status == "needs_review"
    assert "Missing pickup." in contracts[0].warnings
    assert contracts[0].confidence < 1.0


def test_parse_missing_delivery_warns_and_keeps_candidate():
    contracts = parse_hauling_contracts(
        """
        Pick up: Checkmate
        Commodity: Construction Materials
        Quantity: 32 SCU
        """
    )

    assert len(contracts) == 1
    assert contracts[0].delivery == ""
    assert "Missing delivery." in contracts[0].warnings


def test_parse_missing_scu_warns_and_does_not_use_reward_as_quantity():
    contracts = parse_hauling_contracts(
        """
        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Reward:
        12000
        """
    )

    assert len(contracts) == 1
    assert contracts[0].scu == 0
    assert contracts[0].reward == 12000
    assert "Missing SCU." in contracts[0].warnings


def test_parse_malformed_text_returns_global_warning():
    result = HaulingContractParser().parse("Not a contract, just noisy OCR text.")

    assert result.contracts == ()
    assert result.confidence == 0.0
    assert "No hauling contract fields detected." in result.warnings


def test_manifest_totals_remaining_and_capacity_warnings():
    contracts = (
        HaulingContract(id="a", pickup="A", delivery="B", commodity="Food", scu=40, confidence=1.0, status="parsed"),
        HaulingContract(id="b", pickup="A", delivery="C", commodity="Ore", scu=25, confidence=1.0, status="parsed"),
    )

    assert total_scu(contracts) == 65
    assert remaining_capacity(contracts, 70) == 70
    assert "Planned manifest exceeds ship capacity" in validate_capacity(contracts, 50)[0]

    loaded_contracts, changed = toggle_loaded_state(contracts, contracts[0].id)
    assert changed.state == CONTRACT_STATE_LOADED
    assert loaded_scu(loaded_contracts) == 40
    assert remaining_capacity(loaded_contracts, 70) == 30
    assert validate_capacity(contracts, 70) == ()


def test_cargo_state_transitions_and_progress_helpers():
    contracts = (
        HaulingContract(id="a", pickup="A", delivery="B", commodity="Food", scu=40),
        HaulingContract(id="b", pickup="A", delivery="C", commodity="Ore", scu=20),
    )

    loaded, changed = toggle_loaded_state(contracts, "a")
    assert changed.state == CONTRACT_STATE_LOADED
    assert loaded_scu(loaded) == 40
    assert delivered_scu(loaded) == 0
    assert capacity_remaining(loaded, 70) == 30
    assert len(remaining_pickups(loaded)) == 1
    assert len(remaining_deliveries(loaded)) == 2

    delivered, changed = toggle_delivered_state(loaded, "a")
    assert changed.state == CONTRACT_STATE_DELIVERED
    assert loaded_scu(delivered) == 40
    assert delivered_scu(delivered) == 40
    assert capacity_remaining(delivered, 70) == 30
    assert completion_percentage(delivered) == 66.67
    assert len(remaining_deliveries(delivered)) == 1

    back_to_loaded, changed = toggle_delivered_state(delivered, "a")
    assert changed.state == CONTRACT_STATE_LOADED
    assert delivered_scu(back_to_loaded) == 0

    unchanged, changed = toggle_loaded_state(delivered, "a")
    assert changed.state == CONTRACT_STATE_DELIVERED
    assert unchanged[0].state == CONTRACT_STATE_DELIVERED


def test_group_summary_tracks_remaining_and_delivered_scu():
    contracts = (
        with_contract_state(HaulingContract(id="a", pickup="A", delivery="B", commodity="Food", scu=40), "delivered"),
        HaulingContract(id="b", pickup="A", delivery="B", commodity="Ore", scu=20),
    )

    summary = group_summary(contracts)

    assert summary["total_scu"] == 60
    assert summary["remaining_scu"] == 20
    assert summary["delivered_scu"] == 40
    assert summary["remaining_contracts"] == 1
    assert summary["completed_contracts"] == 1


def test_manifest_grouping_helpers():
    contracts = (
        HaulingContract(pickup="Checkmate", delivery="Teasa Spaceport", commodity="A", scu=32),
        HaulingContract(pickup="Checkmate", delivery="Lorville", commodity="B", scu=10),
        HaulingContract(pickup="Seraphim", delivery="Teasa Spaceport", commodity="C", scu=4),
    )

    by_pickup = group_by_pickup(contracts)
    by_destination = group_by_destination(contracts)
    by_route = group_by_route(contracts)

    assert len(by_pickup["Checkmate"]) == 2
    assert len(by_destination["Teasa Spaceport"]) == 2
    assert len(by_route[("Checkmate", "Teasa Spaceport")]) == 1


def test_build_manifest_groups_stops_and_ship_capacity():
    contracts = (
        HaulingContract(pickup="Checkmate", delivery="Teasa Spaceport", commodity="A", scu=32),
        HaulingContract(pickup="Checkmate", delivery="Lorville", commodity="B", scu=10),
    )

    manifest = build_manifest(contracts, selected_ship="Railen")

    assert manifest.selected_ship == "Railen"
    assert manifest.ship_capacity_scu == 640
    assert manifest.total_scu == 42
    assert manifest.loaded_scu == 0
    assert manifest.delivered_scu == 0
    assert manifest.remaining_scu == 640
    assert manifest.planned_contracts == 2
    assert manifest.loaded_contracts == 0
    assert manifest.delivered_contracts == 0
    assert manifest.completion_percentage == 0
    assert manifest.pickups[0].location == "Checkmate"
    assert manifest.pickups[0].total_pickup_scu == 42


def test_sort_contracts_orders_by_route_and_commodity():
    contracts = (
        HaulingContract(pickup="B", delivery="A", commodity="Z", scu=1),
        HaulingContract(pickup="A", delivery="B", commodity="A", scu=1),
    )

    assert [contract.pickup for contract in sort_contracts(contracts)] == ["A", "B"]


def test_ship_capacity_lookup_reuses_trading_metadata():
    assert ship_capacity_scu("Railen") == 640
    assert ship_capacity_scu("C2 Hercules") == 696
    assert ship_capacity_scu("Hull C") == 4608
    assert ship_capacity_scu("Caterpillar") == 576
    assert ship_capacity_scu("Starlancer MAX") == 224

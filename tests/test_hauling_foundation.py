from app.hauling import (
    HaulingContract,
    build_manifest,
    group_by_destination,
    group_by_pickup,
    group_by_route,
    parse_hauling_contracts,
    remaining_capacity,
    ship_capacity_scu,
    sort_contracts,
    total_scu,
    validate_capacity,
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
        HaulingContract(pickup="A", delivery="B", commodity="Food", scu=40, confidence=1.0, status="parsed"),
        HaulingContract(pickup="A", delivery="C", commodity="Ore", scu=25, confidence=1.0, status="parsed"),
    )

    assert total_scu(contracts) == 65
    assert remaining_capacity(contracts, 70) == 5
    assert validate_capacity(contracts, 70) == ()
    assert "exceeds ship capacity" in validate_capacity(contracts, 50)[0]


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
    assert manifest.remaining_scu == 598
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

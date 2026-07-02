from collections import defaultdict

from app.trading_ship_cargo import trading_ship_cargo_scu

from .models import HaulingContract, HaulingManifest, HaulingStop


def total_scu(contracts):
    return sum(max(0.0, float(contract.scu or 0.0)) for contract in contracts or ())


def ship_capacity_scu(ship_name):
    return trading_ship_cargo_scu(ship_name)


def remaining_capacity(contracts, ship_capacity):
    if ship_capacity is None:
        return None
    return float(ship_capacity) - total_scu(contracts)


def group_by_pickup(contracts):
    grouped = defaultdict(list)
    for contract in contracts or ():
        if contract.pickup:
            grouped[contract.pickup].append(contract)
    return {
        location: tuple(sort_contracts(items))
        for location, items in sorted(grouped.items(), key=lambda item: item[0].lower())
    }


def group_by_destination(contracts):
    grouped = defaultdict(list)
    for contract in contracts or ():
        if contract.delivery:
            grouped[contract.delivery].append(contract)
    return {
        location: tuple(sort_contracts(items))
        for location, items in sorted(grouped.items(), key=lambda item: item[0].lower())
    }


def group_by_route(contracts):
    grouped = defaultdict(list)
    for contract in contracts or ():
        if contract.pickup or contract.delivery:
            grouped[(contract.pickup, contract.delivery)].append(contract)
    return {
        route: tuple(sort_contracts(items))
        for route, items in sorted(
            grouped.items(),
            key=lambda item: ((item[0][0] or "").lower(), (item[0][1] or "").lower()),
        )
    }


def sort_contracts(contracts):
    return sorted(
        tuple(contracts or ()),
        key=lambda contract: (
            (contract.pickup or "").lower(),
            (contract.delivery or "").lower(),
            (contract.commodity or "").lower(),
            contract.scu,
            contract.id,
        ),
    )


def validate_capacity(contracts, ship_capacity):
    if ship_capacity is None:
        return ("No ship cargo capacity selected.",)
    remaining = remaining_capacity(contracts, ship_capacity)
    if remaining is None:
        return ("No ship cargo capacity selected.",)
    if remaining < 0:
        return (f"Manifest exceeds ship capacity by {abs(remaining):g} SCU.",)
    return ()


def build_manifest(contracts, selected_ship="", ship_capacity=None):
    contracts = tuple(sort_contracts(contracts))
    if ship_capacity is None and selected_ship:
        ship_capacity = ship_capacity_scu(selected_ship)

    total = total_scu(contracts)
    remaining = remaining_capacity(contracts, ship_capacity)
    warnings = list(validate_capacity(contracts, ship_capacity))
    incomplete = [contract for contract in contracts if not contract.is_complete]
    if incomplete:
        warnings.append(f"{len(incomplete)} contract candidate(s) need review.")

    return HaulingManifest(
        contracts=contracts,
        selected_ship=selected_ship,
        ship_capacity_scu=ship_capacity,
        total_scu=total,
        remaining_scu=remaining,
        pickups=tuple(_build_stops(contracts, group_by_pickup(contracts), "pickup")),
        destinations=tuple(_build_stops(contracts, group_by_destination(contracts), "delivery")),
        warnings=tuple(warnings),
    )


def _build_stops(contracts, grouped, mode):
    contracts = tuple(contracts or ())
    for location, grouped_contracts in grouped.items():
        pickup_contracts = grouped_contracts if mode == "pickup" else tuple(
            contract for contract in contracts if contract.pickup == location
        )
        delivery_contracts = grouped_contracts if mode == "delivery" else tuple(
            contract for contract in contracts if contract.delivery == location
        )
        yield HaulingStop(
            location=location,
            pickup_contracts=tuple(pickup_contracts),
            delivery_contracts=tuple(delivery_contracts),
            total_pickup_scu=total_scu(pickup_contracts),
            total_delivery_scu=total_scu(delivery_contracts),
        )

from collections import defaultdict
from dataclasses import replace

from app.trading_ship_cargo import trading_ship_cargo_scu

from .models import (
    CONTRACT_STATE_CANCELLED,
    CONTRACT_STATE_DELIVERED,
    CONTRACT_STATE_FAILED,
    CONTRACT_STATE_LOADED,
    CONTRACT_STATE_PLANNED,
    CONTRACT_STATES,
    HaulingContract,
    HaulingManifest,
    HaulingStop,
)


def total_scu(contracts):
    return sum(max(0.0, float(contract.scu or 0.0)) for contract in contracts or ())


def normalize_contract_state(state):
    state = str(state or "").strip().lower()
    return state if state in CONTRACT_STATES else CONTRACT_STATE_PLANNED


def is_loaded_state(state):
    return normalize_contract_state(state) in (CONTRACT_STATE_LOADED, CONTRACT_STATE_DELIVERED)


def is_delivered_state(state):
    return normalize_contract_state(state) == CONTRACT_STATE_DELIVERED


def with_contract_state(contract, state):
    state = normalize_contract_state(state)
    if state == CONTRACT_STATE_DELIVERED:
        return replace(contract, state=CONTRACT_STATE_DELIVERED)
    if state == CONTRACT_STATE_LOADED:
        return replace(contract, state=CONTRACT_STATE_LOADED)
    if state == CONTRACT_STATE_FAILED:
        return replace(contract, state=CONTRACT_STATE_FAILED)
    if state == CONTRACT_STATE_CANCELLED:
        return replace(contract, state=CONTRACT_STATE_CANCELLED)
    return replace(contract, state=CONTRACT_STATE_PLANNED)


def loaded_scu(contracts):
    return sum(
        max(0.0, float(contract.scu or 0.0))
        for contract in contracts or ()
        if is_loaded_state(contract.state)
    )


def delivered_scu(contracts):
    return sum(
        max(0.0, float(contract.scu or 0.0))
        for contract in contracts or ()
        if is_delivered_state(contract.state)
    )


def planned_contract_count(contracts):
    return sum(1 for contract in contracts or () if normalize_contract_state(contract.state) == CONTRACT_STATE_PLANNED)


def loaded_contract_count(contracts):
    return sum(1 for contract in contracts or () if normalize_contract_state(contract.state) == CONTRACT_STATE_LOADED)


def delivered_contract_count(contracts):
    return sum(1 for contract in contracts or () if is_delivered_state(contract.state))


def remaining_pickups(contracts):
    return tuple(contract for contract in contracts or () if not is_loaded_state(contract.state))


def remaining_deliveries(contracts):
    return tuple(contract for contract in contracts or () if not is_delivered_state(contract.state))


def completion_percentage(contracts):
    total = total_scu(contracts)
    if total <= 0:
        return 0.0
    return round(min(100.0, (delivered_scu(contracts) / total) * 100.0), 2)


def capacity_used(contracts):
    return loaded_scu(contracts)


def capacity_remaining(contracts, ship_capacity):
    if ship_capacity is None:
        return None
    return float(ship_capacity) - capacity_used(contracts)


def ship_capacity_scu(ship_name):
    return trading_ship_cargo_scu(ship_name)


def remaining_capacity(contracts, ship_capacity):
    return capacity_remaining(contracts, ship_capacity)


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
    loaded_remaining = capacity_remaining(contracts, ship_capacity)
    if loaded_remaining is None:
        return ("No ship cargo capacity selected.",)
    if loaded_remaining < 0:
        return (f"Loaded cargo exceeds ship capacity by {abs(loaded_remaining):g} SCU.",)

    planned_remaining = float(ship_capacity) - total_scu(contracts)
    if planned_remaining < 0:
        return (f"Planned manifest exceeds ship capacity by {abs(planned_remaining):g} SCU.",)
    return ()


def operation_warnings(contracts):
    contracts = tuple(contracts or ())
    if not contracts:
        return ()
    if delivered_contract_count(contracts) == len(contracts):
        return ("Everything delivered.",)
    if loaded_scu(contracts) <= 0:
        return ("Nothing loaded.",)
    return ()


def group_summary(contracts):
    contracts = tuple(contracts or ())
    delivered = delivered_scu(contracts)
    total = total_scu(contracts)
    completed = delivered_contract_count(contracts)
    return {
        "total_scu": total,
        "remaining_scu": max(0.0, total - delivered),
        "delivered_scu": delivered,
        "total_contracts": len(contracts),
        "remaining_contracts": max(0, len(contracts) - completed),
        "completed_contracts": completed,
    }


def update_contract_state(contracts, contract_id, state):
    return tuple(
        with_contract_state(contract, state) if contract.id == contract_id else contract
        for contract in contracts or ()
    )


def toggle_loaded_state(contracts, contract_id):
    updated = []
    changed = None
    for contract in contracts or ():
        if contract.id != contract_id:
            updated.append(contract)
            continue
        current = normalize_contract_state(contract.state)
        if current == CONTRACT_STATE_DELIVERED:
            updated.append(contract)
            changed = contract
        elif current == CONTRACT_STATE_LOADED:
            changed = with_contract_state(contract, CONTRACT_STATE_PLANNED)
            updated.append(changed)
        else:
            changed = with_contract_state(contract, CONTRACT_STATE_LOADED)
            updated.append(changed)
    return tuple(updated), changed


def toggle_delivered_state(contracts, contract_id):
    updated = []
    changed = None
    for contract in contracts or ():
        if contract.id != contract_id:
            updated.append(contract)
            continue
        current = normalize_contract_state(contract.state)
        if current == CONTRACT_STATE_DELIVERED:
            changed = with_contract_state(contract, CONTRACT_STATE_LOADED)
        else:
            changed = with_contract_state(contract, CONTRACT_STATE_DELIVERED)
        updated.append(changed)
    return tuple(updated), changed


def contract_by_id(contracts, contract_id):
    for contract in contracts or ():
        if contract.id == contract_id:
            return contract
    return None


def capacity_status_text(contracts, ship_capacity):
    if ship_capacity is None:
        return "Capacity status: Select a ship."
    remaining = capacity_remaining(contracts, ship_capacity)
    if remaining is None:
        return "Capacity status: Select a ship."
    if remaining < 0:
        return f"Capacity status: Loaded cargo exceeds ship capacity by {abs(remaining):g} SCU."
    planned_remaining = float(ship_capacity) - total_scu(contracts)
    if planned_remaining < 0:
        return f"Capacity status: Planned manifest exceeds capacity by {abs(planned_remaining):g} SCU."
    return "Capacity status: Ready."


def build_manifest(contracts, selected_ship="", ship_capacity=None):
    contracts = tuple(sort_contracts(with_contract_state(contract, contract.state) for contract in contracts or ()))
    if ship_capacity is None and selected_ship:
        ship_capacity = ship_capacity_scu(selected_ship)

    total = total_scu(contracts)
    loaded = loaded_scu(contracts)
    delivered = delivered_scu(contracts)
    remaining = capacity_remaining(contracts, ship_capacity)
    warnings = list(validate_capacity(contracts, ship_capacity))
    warnings.extend(operation_warnings(contracts))
    incomplete = [contract for contract in contracts if not contract.is_complete]
    if incomplete:
        warnings.append(f"{len(incomplete)} contract candidate(s) need review.")

    return HaulingManifest(
        contracts=contracts,
        selected_ship=selected_ship,
        ship_capacity_scu=ship_capacity,
        total_scu=total,
        loaded_scu=loaded,
        delivered_scu=delivered,
        remaining_scu=remaining,
        total_contracts=len(contracts),
        planned_contracts=planned_contract_count(contracts),
        loaded_contracts=loaded_contract_count(contracts),
        delivered_contracts=delivered_contract_count(contracts),
        completion_percentage=completion_percentage(contracts),
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

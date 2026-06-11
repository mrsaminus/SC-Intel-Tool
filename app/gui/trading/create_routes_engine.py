from dataclasses import dataclass
import re

from app.trading_data import calculate_trade_estimate, format_trade_age, is_suspicious_margin

from .route_quality import calculate_route_quality
from .route_summary import notes_from_flags


OPTIMIZATION_MODES = (
    "Balanced",
    "Highest Profit",
    "Highest Profit / SCU",
    "Lowest Risk",
    "Lowest Investment",
    "Fast Turnaround",
)

TOP_ROUTE_OPTIONS = (5, 10, 20, 50)

SYSTEM_OPTIONS = ("Stanton", "Pyro", "Nyx")
LOCATION_TYPE_OPTIONS = (
    "City",
    "Station",
    "Lagrange Point",
    "Planet Surface",
    "Outpost",
    "Hidden Location",
)
DEFAULT_SYSTEMS = ("Stanton",)
DEFAULT_LOCATION_TYPES = ("City", "Station", "Lagrange Point")

CITY_KEYWORDS = (
    "area18",
    "area 18",
    "lorville",
    "orison",
    "new babbage",
    "cloudview center",
    "teasa spaceport",
)
STATION_KEYWORDS = (
    "station",
    "gateway",
    "port ",
    "everus harbor",
    "seraphim",
    "baijini",
    "tressler",
    "grim hex",
    "grimhex",
    "galleria",
    "admin",
    "ruin station",
    "checkmate",
)
OUTPOST_KEYWORDS = (
    "mining area",
    "shubin",
    "salvage",
    "reclamation",
    "orphanage",
    "jumptown",
    "nt-999",
    "hdms-",
    "arc-corp",
    "rayari",
    "samson",
    "brios",
    "brio",
)
HIDDEN_KEYWORDS = (
    "jumptown",
    "ghost hollow",
    "orphanage",
    "brio",
    "brios",
    "nt-999",
)
CONTESTED_KEYWORDS = (
    "ruin station",
    "checkmate",
    "contested",
    "pyro",
    "rat's nest",
    "rats nest",
)
DANGEROUS_KEYWORDS = (
    "pyro",
    "ruin station",
    "checkmate",
    "jumptown",
    "ghost hollow",
    "orphanage",
    "brio",
    "brios",
)
ILLEGAL_COMMODITY_KEYWORDS = (
    "maze",
    "widow",
    "slam",
    "neon",
    "etam",
    "altruciatoxin",
    "revenant tree pollen",
    "diluthermex",
)

STANTON_LOCATION_KEYWORDS = (
    "area18",
    "area 18",
    "lorville",
    "orison",
    "new babbage",
    "arc-l",
    "cru-l",
    "hur-l",
    "mic-l",
    "hdms-",
    "shubin",
    "rayari",
    "bezdek",
    "lathan",
    "hadley",
    "thedus",
    "anderson",
    "edmond",
    "perlman",
    "ryder",
    "woodruff",
    "humboldt",
    "stanhope",
    "reclamation & disposal",
    "everus harbor",
    "baijini point",
    "seraphim station",
    "port tressler",
    "grim hex",
    "covalex",
    "samson & son",
    "samson and son",
    "tram & myers",
    "tram and myers",
)
PYRO_LOCATION_KEYWORDS = (
    "pyro",
    "ruin station",
    "checkmate",
    "rats nest",
    "rat's nest",
    "obituary station",
)
NYX_LOCATION_KEYWORDS = (
    "nyx",
    "levski",
)


@dataclass(frozen=True)
class CreateRoutesSettings:
    cargo_scu: float
    max_investment: float | None
    systems: tuple[str, ...]
    location_types: tuple[str, ...]
    avoid_dangerous: bool
    avoid_hidden: bool
    avoid_non_armistice: bool
    allow_pyro: bool
    allow_contested: bool
    include_illegal: bool
    legal_goods: bool
    stable_routes: bool
    high_profit: bool
    allow_high_volatility: bool
    include_mission_goods: bool
    optimization_mode: str
    top_count: int


@dataclass(frozen=True)
class CreateRoutesResult:
    rank: int
    opportunity: object
    estimate: object
    quality: object
    buy_system: str
    sell_system: str
    buy_location_type: str
    sell_location_type: str
    risk_score: int
    notes: tuple[str, ...]
    sort_key: tuple


def generate_create_routes(opportunities, settings):
    results = []
    seen = set()
    for opportunity in opportunities:
        route_key = normalized_key(opportunity.commodity, opportunity.buy_location, opportunity.sell_location)
        if route_key in seen:
            continue
        seen.add(route_key)

        result = evaluate_opportunity(opportunity, settings)
        if result:
            results.append(result)

    results.sort(key=lambda result: result.sort_key)
    ranked = [
        CreateRoutesResult(
            rank=index,
            opportunity=result.opportunity,
            estimate=result.estimate,
            quality=result.quality,
            buy_system=result.buy_system,
            sell_system=result.sell_system,
            buy_location_type=result.buy_location_type,
            sell_location_type=result.sell_location_type,
            risk_score=result.risk_score,
            notes=result.notes,
            sort_key=result.sort_key,
        )
        for index, result in enumerate(results[:settings.top_count], start=1)
    ]
    return ranked


def evaluate_opportunity(opportunity, settings):
    if opportunity.profit_per_scu <= 0:
        return None

    buy_system = system_from_location(opportunity.buy_location)
    sell_system = system_from_location(opportunity.sell_location)
    buy_location_type = classify_location(opportunity.buy_location)
    sell_location_type = classify_location(opportunity.sell_location)
    systems = {buy_system, sell_system}
    location_types = {buy_location_type, sell_location_type}
    combined_text = " ".join((opportunity.commodity, opportunity.buy_location, opportunity.sell_location)).lower()

    if "Pyro" in systems and not settings.allow_pyro:
        return None

    allowed_systems = set(settings.systems or DEFAULT_SYSTEMS)
    if settings.allow_pyro:
        allowed_systems.add("Pyro")
    if allowed_systems and not systems.issubset(allowed_systems):
        return None

    allowed_location_types = set(settings.location_types or DEFAULT_LOCATION_TYPES)
    if allowed_location_types and not location_types.issubset(allowed_location_types):
        return None

    hidden = contains_any(combined_text, HIDDEN_KEYWORDS) or "Hidden Location" in location_types
    contested = contains_any(combined_text, CONTESTED_KEYWORDS)
    dangerous = contains_any(combined_text, DANGEROUS_KEYWORDS)
    illegal = is_illegal_commodity(opportunity.commodity)
    suspicious = is_suspicious_margin(opportunity)
    non_armistice = not location_types.issubset({"City", "Station", "Lagrange Point"})

    if settings.avoid_hidden and hidden:
        return None
    if settings.avoid_dangerous and dangerous:
        return None
    if settings.avoid_non_armistice and non_armistice:
        return None
    if not settings.allow_contested and contested:
        return None
    if settings.legal_goods and not settings.include_illegal and illegal:
        return None
    if settings.stable_routes and suspicious and not settings.allow_high_volatility:
        return None

    estimate = calculate_trade_estimate(opportunity, settings.cargo_scu, settings.max_investment)
    if estimate.effective_cargo_scu <= 0:
        return None

    quality = calculate_route_quality(
        total_profit=estimate.estimated_total_profit,
        profit_per_scu=opportunity.profit_per_scu,
        full_cargo=not estimate.investment_limited,
        affordable=estimate.full_cargo_affordable,
        suspicious=suspicious,
    )
    notes = build_notes(
        settings,
        opportunity,
        estimate,
        buy_system,
        sell_system,
        buy_location_type,
        sell_location_type,
        hidden,
        contested,
        dangerous,
        illegal,
        suspicious,
        non_armistice,
    )
    risk_score = calculate_risk_score(
        buy_system,
        sell_system,
        hidden,
        contested,
        dangerous,
        illegal,
        suspicious,
        non_armistice,
    )
    return CreateRoutesResult(
        rank=0,
        opportunity=opportunity,
        estimate=estimate,
        quality=quality,
        buy_system=buy_system,
        sell_system=sell_system,
        buy_location_type=buy_location_type,
        sell_location_type=sell_location_type,
        risk_score=risk_score,
        notes=tuple(notes),
        sort_key=sort_key_for_mode(
            settings.optimization_mode,
            opportunity,
            estimate,
            quality,
            risk_score,
            buy_system,
            sell_system,
            buy_location_type,
            sell_location_type,
        ),
    )


def sort_key_for_mode(
    mode,
    opportunity,
    estimate,
    quality,
    risk_score,
    buy_system,
    sell_system,
    buy_location_type,
    sell_location_type,
):
    same_system = buy_system == sell_system
    accessible_score = accessibility_score(buy_location_type) + accessibility_score(sell_location_type)
    stable_tiebreaker = (
        opportunity.commodity.lower(),
        opportunity.buy_location.lower(),
        opportunity.sell_location.lower(),
    )

    if mode == "Highest Profit":
        primary = (-estimate.estimated_total_profit, -opportunity.profit_per_scu, risk_score)
    elif mode == "Highest Profit / SCU":
        primary = (-opportunity.profit_per_scu, -estimate.estimated_total_profit, risk_score)
    elif mode == "Lowest Risk":
        primary = (risk_score, -quality.sort_value, -estimate.estimated_total_profit)
    elif mode == "Lowest Investment":
        primary = (estimate.estimated_buy_cost, -opportunity.profit_per_scu, -estimate.estimated_total_profit)
    elif mode == "Fast Turnaround":
        primary = (0 if same_system else 1, -accessible_score, risk_score, -opportunity.profit_per_scu)
    else:
        primary = (-quality.sort_value, risk_score, -estimate.estimated_total_profit, -opportunity.profit_per_scu)

    return (*primary, *stable_tiebreaker)


def calculate_risk_score(
    buy_system,
    sell_system,
    hidden,
    contested,
    dangerous,
    illegal,
    suspicious,
    non_armistice,
):
    score = 0
    if "Pyro" in {buy_system, sell_system}:
        score += 3
    if buy_system != sell_system:
        score += 1
    if hidden:
        score += 3
    if contested:
        score += 2
    if dangerous:
        score += 2
    if illegal:
        score += 3
    if suspicious:
        score += 2
    if non_armistice:
        score += 1
    return score


def build_notes(
    settings,
    opportunity,
    estimate,
    buy_system,
    sell_system,
    buy_location_type,
    sell_location_type,
    hidden,
    contested,
    dangerous,
    illegal,
    suspicious,
    non_armistice,
):
    notes = []
    if estimate.investment_limited:
        notes.append("Budget-limited cargo")
    else:
        notes.append("Full cargo")

    notes.append("Same-system route" if buy_system == sell_system else "Cross-system route")
    notes.append(f"{buy_location_type} to {sell_location_type}")

    if settings.avoid_hidden and not hidden:
        notes.append("Hidden avoided")
    if settings.avoid_non_armistice and not non_armistice:
        notes.append("Armistice-focused")
    if not settings.allow_contested and not contested:
        notes.append("Contested avoided")
    if not settings.allow_pyro and "Pyro" not in {buy_system, sell_system}:
        notes.append("Pyro excluded")
    if illegal:
        notes.append("Illegal commodity allowed")
    elif settings.legal_goods:
        notes.append("Legal commodity")
    if suspicious:
        notes.append("High margin / possible outlier")
    if dangerous:
        notes.append("Danger keyword matched")
    if settings.optimization_mode == "Fast Turnaround":
        notes.append("Fast-turnaround heuristic")
    if settings.stable_routes:
        notes.append("Stable-route preference")
    if settings.high_profit:
        notes.append("High-profit preference")
    if settings.include_mission_goods:
        notes.append("Mission-good source data unavailable")
    notes.append(f"Updated: {format_trade_age(opportunity.date_modified)}")
    return notes


def system_from_location(location):
    parts = location_parts(location)
    if not parts:
        return "Unknown"
    system = parts[0].strip()
    if not system:
        return "Unknown"
    lowered = system.lower()
    if lowered == "st":
        return "Stanton"
    if lowered.startswith("stanton"):
        return "Stanton"
    if lowered.startswith("pyro"):
        return "Pyro"
    if lowered.startswith("nyx"):
        return "Nyx"
    inferred = infer_system_from_location(location)
    if inferred:
        return inferred
    if " - " not in (location or ""):
        return "Unknown"
    return system


def infer_system_from_location(location):
    text = (location or "").lower()
    if contains_any(text, PYRO_LOCATION_KEYWORDS):
        return "Pyro"
    if contains_any(text, NYX_LOCATION_KEYWORDS):
        return "Nyx"
    if contains_any(text, STANTON_LOCATION_KEYWORDS):
        return "Stanton"
    return ""


def classify_location(location):
    text = (location or "").lower()
    if contains_any(text, HIDDEN_KEYWORDS):
        return "Hidden Location"
    if contains_any(text, CITY_KEYWORDS):
        return "City"
    if re.search(r"\b[A-Z]{3}-L\d\b", location or "") or re.search(r"\b(ARC|CRU|HUR|MIC)-L\d\b", location or ""):
        return "Lagrange Point"
    if contains_any(text, STATION_KEYWORDS):
        return "Station"
    if contains_any(text, OUTPOST_KEYWORDS):
        return "Outpost"
    if " - " in (location or ""):
        return "Planet Surface"
    return "Outpost"


def location_parts(location):
    return [part.strip() for part in (location or "").split(" - ") if part.strip()]


def is_illegal_commodity(commodity):
    return contains_any((commodity or "").lower(), ILLEGAL_COMMODITY_KEYWORDS)


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def accessibility_score(location_type):
    if location_type == "City":
        return 3
    if location_type in {"Station", "Lagrange Point"}:
        return 2
    if location_type == "Outpost":
        return 1
    return 0


def normalized_key(*parts):
    return "|".join(
        re.sub(r"[^a-z0-9]+", " ", str(part or "").lower()).strip()
        for part in parts
    )


def notes_text(result):
    return notes_from_flags(result.quality.flags, result.notes)

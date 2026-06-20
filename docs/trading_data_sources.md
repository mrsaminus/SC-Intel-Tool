# Trading Data Sources

Last reviewed: 2026-06-20

This note describes the public Trading data-source strategy for SC Intel Tool.
It is documentation only and does not change app behavior.

## Current Public Source: UEX

SC Intel Tool uses public UEX commodity price rows for the visible Trading
workflows.

Active public workflows:

- `UEX Trading` loads live UEX buy/sell price rows and calculates simple
  buy/sell opportunities.
- `Create Routes` uses those UEX opportunities with local ship cargo capacity,
  budget and safety filters.
- `Trade Routes` uses UEX opportunities for commodity, origin, destination,
  cargo and investment filters.
- `Best Buyer` ranks public UEX sell locations for a selected commodity.
- `En Route` uses UEX prices for origin/destination opportunity checks.
- `Commodities` and `Shops` derive public reference rows from UEX market data.
- `Saved Routes` stores complete saved and recent route summaries locally in
  SQLite.

Strengths:

- Works without user authentication in the current public app.
- Provides broad commodity price rows with buy and sell prices.
- Supports local cargo, investment, profit and route-summary calculations.
- Keeps public Trading behavior explainable and tester-friendly.

Limitations:

- Route quality is calculated locally and remains intentionally simple.
- Best Buyer ranks sell locations only; it does not invent buy-side costs.
- Commodity type/category data is limited when UEX price rows do not expose it.
- Shops/locations are derived from market rows, so they depend on current UEX
  data availability.
- Complex route optimization remains out of scope for the current public build.

## Local Trading Metadata

Trading ship selectors use `app/trading_ship_cargo.py` for cargo capacity. The
primary source is the provided `Star_Citizen_Flight_Ready_SCU_Offisiell.xlsx`
workbook, sheet `SCU Kapasitet`. Existing `app/ship_metadata.py` values are used
only as fallback, and the spreadsheet wins if values disagree.

Trading ship selectors filter out ships without known Cargo SCU because trade
totals depend on capacity.

Saved routes, recent routes and UEX Trading presets are local-only SQLite data.
Recent routes are capped to the latest 100 entries and exact duplicates are
collapsed to avoid spam.

## Future Data-Source Research

A trading tool may be revisited later for route-quality research, but it should
not be exposed as a public dependency until the access model and tester UX are
clear. Public builds should avoid token prompts, unavailable workflow dead-ends
and functional-looking controls that cannot produce results.

Possible future path:

1. Keep UEX as the default public Trading source.
2. Improve UEX-backed filters, copy/export summaries and saved-route workflows.
3. Consider a trading tool only as optional route-quality enrichment after
   public UX and access handling are intentionally designed.
4. Treat any crowdsourced or unauthenticated secondary listings as experimental
   until outlier handling and freshness rules are reliable.

## RSI Ship Matrix Reference

The public RSI Ship Matrix exposes ship specs through:

```text
https://robertsspaceindustries.com/ship-matrix/index
```

The response includes `name`, `min_crew`, `max_crew` and `cargocapacity` fields.
The provided spreadsheet remains the primary Trading cargo source, but RSI Ship
Matrix is a documented public reference for future local cargo metadata updates.
For the current Trading UI, SC Intel Tool uses local static cargo metadata at
runtime and filters dropdowns to ships whose Cargo SCU is known.

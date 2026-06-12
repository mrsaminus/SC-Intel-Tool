# Trading Data Sources

Last reviewed: 2026-06-12

This note captures the current research spike for possible Trading tab data
sources. It is documentation only and does not change app behavior.

## Current MVP Source: UEX

SC Intel Tool currently uses UEX live commodity price data for the Trading MVP.

Strengths:

- Works without user authentication in the current app.
- Provides broad commodity price rows with buy and sell prices.
- Fits the simple Phase 1/2 workflow: local buy/sell comparison, cargo capacity,
  max investment and profit calculations.

Limitations:

- Route quality is calculated locally and is intentionally simple.
- It does not yet provide a full route-optimizer workflow in SC Intel Tool.

## SC Trade Tools API

Sources:

- Site: https://sc-trade.tools/
- Swagger/OpenAPI: https://sc-trade.tools/swagger-ui/index.html
- OpenAPI JSON: https://sc-trade.tools/v3/api-docs

The OpenAPI document identifies the API as `SC Trade Tools API` version `11.3.1`.

Current public SC Intel Tool use:

- `Commodities` uses public commodity item and item-type endpoints.
- `Shops` uses public commodity shop and location endpoints.
- `Trade Routes`, `Best Buyer` and `En Route` are advanced SC Trade Tools
  workflows that are currently unavailable in the public build.
- Public Settings does not expose advanced SC Trade Tools access fields.
- `Saved Routes` stores complete saved and recent route summaries locally in
  SQLite.
- `UEX Trading` presets store selected ship, Cargo SCU, investment and filter
  settings locally.
- Trading dropdowns use searchable/type-filterable selection fields.
- Trading reference data auto-loads public commodities, shops, locations and
  ship names in the background when the Trading module opens.
- Trading ship selectors use `app/trading_ship_cargo.py` for cargo capacity.
  The primary source is the provided `Star_Citizen_Flight_Ready_SCU_Offisiell.xlsx`
  workbook, sheet `SCU Kapasitet`. Existing `app/ship_metadata.py` values are
  used only as fallback, and the spreadsheet wins if values disagree.
- SC Trade Tools ship data can expand selectable ship names only when those
  names resolve to known Trading cargo metadata; its `maxBoxSizeInScu` field is
  not treated as cargo capacity.
- Trading ship selectors filter out ships without known Cargo SCU because trade
  totals depend on capacity.

Advanced SC Trade Tools workflows:

- The useful route, buyer and itinerary endpoints are token-restricted by SC
  Trade Tools.
- The public app currently hides advanced access controls to avoid confusing
  normal users.
- Existing internal client/helper code remains available for future design work,
  but this is not a public user workflow in alpha.8.7.

Local Trading storage:

- Saved routes, recent routes and UEX Trading presets are local-only SQLite data.
- Recent routes are capped to the latest 100 entries and exact duplicates are
  collapsed to avoid spam.
- Saved routes are only enabled when the workflow exposes complete buy/sell,
  cargo and profit fields.
- Best Buyer remains informational when buy-side/profit data is unavailable;
  SC Intel Tool does not invent missing route profit.

### Public Endpoints

These endpoints responded without authentication during the spike:

| Endpoint | Purpose | Useful fields |
| --- | --- | --- |
| `GET /api/commodity/items` | Commodity list | `name` |
| `GET /api/commodity/item-types` | Commodity type list | type metadata |
| `GET /api/commodity/shops` | Commodity shops | `name` |
| `GET /api/locations` | Known trade locations | `name`, `type` |
| `GET /api/location-types` | Location filter values | type metadata |
| `GET /api/ships` | Ship names and box support | `name`, `maxBoxSizeInScu` |
| `GET /api/factions` | Commodity shop factions | faction metadata |
| `GET /api/security-levels` | Security-level filters | security metadata |
| `GET /api/crowdsource/commodity-listings?page=0` | Paginated crowdsourced commodity listings | `location`, `transaction`, `commodity`, `price`, `quantity`, `saturation`, `boxSizesInScu`, `timestamp` |

Observed sample sizes on 2026-06-05:

- `GET /api/commodity/items`: 170 commodities.
- `GET /api/commodity/shops`: 158 shops.
- `GET /api/locations`: 201 locations.
- `GET /api/ships`: 85 ships.
- SC Trade Tools ship rows exposed `name` and `maxBoxSizeInScu`; cargo capacity
  remains local Trading metadata. Trading dropdowns filter out ships without
  known Cargo SCU metadata.
- `GET /api/crowdsource/commodity-listings?page=0`: paginated, 100 rows per page,
  7,715 total elements at review time.

Important caveat: the crowdsourced listings endpoint is documented as unfiltered
data that may contain outliers and is cached server-side for 1 hour.

### RSI Ship Matrix Reference

The public RSI Ship Matrix exposes ship specs through:

- `GET https://robertsspaceindustries.com/ship-matrix/index`

The response includes `name`, `min_crew`, `max_crew` and `cargocapacity` fields.
The provided spreadsheet remains the primary Trading cargo source, but RSI Ship
Matrix is a documented public reference for future local cargo metadata updates.
For the current Trading UI, SC Intel Tool uses local static cargo metadata at
runtime and filters dropdowns to ships whose Cargo SCU is known.

### Token-Required Endpoints

The most useful direct trading endpoints require a `token` header according to
the OpenAPI spec:

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /api/commodity/items/{name}/transactions` | Buy/sell transactions for a commodity | Returns `TransactionDto`; requires token. |
| `GET /api/commodity/shops/{name}/transactions` | Transactions for a commodity shop | Returns `TransactionDto`; requires token. |
| `GET /api/commodity/reports` | Aggregated commodity reports | Includes average profit per SCU, ROI, supply and demand; requires token. |
| `POST /api/tools/trades` | Profitable trade routes | Route optimizer; requires token. |
| `POST /api/tools/buyers` | Best buyers for a commodity | Takes commodity quantity in SCU; requires token. |
| `POST /api/tools/itinerary` | Ordered trade itinerary | Origin/destination route planning; requires token. |
| `POST /api/tools/circuits/{tradeId}` | Circular trade route | Requires token. |
| `GET /api/graphs/shop/edges/{id}/alternatives` | Alternative commodities for a trade | Requires token. |

Useful response models:

- `TradeDto`: `id`, `origin`, `destination`, `profitPerMinute`, `profit`,
  `timeInSeconds`.
- `TransactionDto`: `location`, `shop`, `securityLevel`, `faction`, `action`,
  `itemQuantityInScu`, `itemName`, `price`, `fees`, `quantityInScu`,
  `maxQuantityInScu`, `boxSizesInScu`, `isHidden`.

Useful route request fields include:

- `investment`
- `ship`
- `maxStops`
- `profitType`
- `supportedBoxSizeInScu`
- `minInventorySizeInScu`
- `minSecurityLevel`
- `allowWaitTimes`
- `useAutoLoading`
- `smartFilters`
- commodity, location, location-type and faction whitelist/blacklist filters

## Comparison With Current UEX MVP

UEX is better for the current MVP because the app can load live commodity price
rows without requiring user configuration. SC Intel Tool can then calculate simple
profit/unit, profit/SCU, cargo-limited totals and investment-limited totals
locally.

SC Trade Tools is stronger for future route quality because its restricted
tool endpoints already model trade-route concerns such as investment, ship,
box size, max stops, wait times, auto-loading, hidden locations, inventory size,
security level and route profit/time.

The public SC Trade Tools crowdsourced listing endpoint could technically be
used as a secondary raw-data source, but it needs extra validation and outlier
handling before it should drive default Trading decisions.

## Recommendation

Recommendation: **C) route-optimization source only** for now.

Keep UEX as the primary Trading MVP source. Consider SC Trade Tools later for
route optimization or advanced route quality only after public UX and access
handling are intentionally designed.

Do not replace UEX yet.

Possible future path:

1. Keep the current UEX MVP table as the default simple workflow.
2. Use public SC Trade Tools metadata for commodities, shops and locations
   where it improves reference workflows.
3. Keep Trade Routes, Best Buyer and En Route disabled in the public build until
   the workflow is clear enough for normal users.
4. Expand route tools gradually only after real access and UX testing.
5. Treat crowdsourced listings as experimental until outlier handling and data
   freshness rules are clear.

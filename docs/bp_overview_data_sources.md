# BP Overview Data Sources

Last researched: 2026-06-05

BP Overview uses public Star Citizen crafting data only. The alpha implementation
does not use account login, telemetry, cloud sync, OCR, screen-reader capture or
aggressive scraping.

## Primary Source: SC Craft Tools

Source: [SC Craft Tools](https://sc-craft.tools)

SC Craft Tools exposes a public blueprint API used by its own web app:

```text
GET https://sc-craft.tools/api/blueprints?page=1&limit=100
```

Observed behavior:

- Public endpoint, no token required.
- Pagination supports up to 100 blueprint records per page.
- On 2026-06-05 the endpoint returned 1,534 blueprint records across 16 pages.
- The app fetches pages sequentially and keeps the request count low.

Useful fields observed:

- `id`
- `blueprint_id`
- `name`
- `category`
- `craft_time_seconds`
- `version`
- `ingredients`
- `missions`
- `item_stats`
- `tiers`
- `default_owned`

Ingredient fields observed:

- `slot`
- `name`
- `quantity_scu`
- `options`
- `min_quality`
- `unit`
- `quality_effects`

Mission/source fields observed:

- `mission_id`
- `name`
- `drop_chance`

Limitations:

- The public blueprint payload does not currently expose every possible
  contractor, reputation, system or exact location field in a normalized way.
- When mission/source context is not present, SC Intel Tool displays that the
  field is unavailable instead of inventing data.
- BP Overview treats the SC Craft Tools payload as live reference data, not as
  user-owned state. Owned blueprint state is stored locally in SQLite.

Attribution:

- BP Overview labels SC Craft Tools as the data source in tables and details.
- Users can open SC Craft Tools directly from the BP Overview source panel.

## Secondary Reference: SCMDB

Source: [SCMDB](https://scmdb.net)

SCMDB is a public Star Citizen database/reference site. Its web app loads static
JSON bundles such as:

```text
https://scmdb.net/data/game-versions.json
https://scmdb.net/data/merged-4.8.1-live.11875683.json
```

Observed behavior:

- Public static JSON data, no token observed for read access.
- The merged data bundle is large, around 11 MB at the time of research.
- The bundle contains broad Star Citizen game data, including crafting-related
  and mission-related structures.

Current alpha decision:

- SCMDB is documented as a secondary/source-context reference.
- The first BP Overview alpha does not load the large SCMDB bundle at runtime.
- Future passes may use SCMDB if it helps enrich blueprint source/mission
  context without heavy startup cost or brittle parsing.

## Safety And Usage Notes

- No protected website code or assets are copied.
- No login or account integration is used.
- No user blueprint ownership data is sent to SC Craft Tools, SCMDB or the
  developer.
- Owned blueprint progress remains in the local `owned_blueprints` SQLite table.
- Future OCR/screen-reader capture is optional and remains a later roadmap item.

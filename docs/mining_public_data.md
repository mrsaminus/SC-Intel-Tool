# Mining / Salvage Public Runtime Data

This note documents how SC Intel Tool provides Mining / Salvage data in public
source and packaged builds without bundling the private/local
`reference_material/` tree.

## Runtime Data Sources

Mining / Salvage loads data through `app/mining_data.py`.

The loader first tries the maintainer reference root:

```text
reference_material/mining_warchest/
```

If that root is unavailable, packaged and public source builds use the minimal
public bundle:

```text
app/assets/mining_public/
```

The Windows build script intentionally does not bundle `reference_material/`.
It only bundles:

```text
app/assets/mining_public/
```

## Bundled Public Files

The public Mining / Salvage runtime bundle currently contains only these files:

```text
app/assets/mining_public/Calculator/rock-breaking-calculator-data.json
app/assets/mining_public/defaults/equipment_shops_cache_default.json
app/assets/mining_public/assets/Mineral Stats/Mineral_Where.txt
```

These are extracted/minimized runtime files used by the public app. Do not copy
the full `reference_material/` folder into the app or release artifacts.

## Embedded Fallback Tables

`app/mining_data.py` also embeds small fallback tables for data that must work in
public builds:

- `SALVAGE_EQUIPMENT`
- `SCAN_SIGNATURE_SPECS`
- `QUALITY_BAND_RAW_VALUES`
- `QUALITY_BAND_RAW_ALIASES`
- `QUALITY_BAND_LABELS_FALLBACK`

Refinery station and method dropdowns also use fallback lists from
`app/gui/constants.py` when the local reference workbook is not present.

## Tab Dependency Map

| Mining / Salvage area | Runtime data used | Live data dependency |
| --- | --- | --- |
| Overview | Counts from loaded minerals, locations, equipment, quality bands, scan signatures, refinery fallbacks | None for status counts; mentions UEX availability |
| Ore Finder | `Mineral_Where.txt` parsed into mineral/location rows | Optional UEX sell prices after user refresh |
| Locations | `Mineral_Where.txt` parsed into location rows | None |
| Scan ID | Embedded `SCAN_SIGNATURE_SPECS` | None |
| Quality Bands | Local reference `qualityquantization` if available, otherwise embedded fallback quality table | None |
| Refinery | Fallback station/method/material constants, optional local `Refinery.xlsx` when available | Optional UEX sell prices after user refresh |
| Rock Breaker | `rock-breaking-calculator-data.json` | None |
| Equipment | `rock-breaking-calculator-data.json`, `equipment_shops_cache_default.json`, embedded salvage equipment | None |

## Maintainer Update Flow

Use the maintainer helper script to refresh the public bundle from an approved
local reference checkout:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_mining_public_data.py
```

Optional source override:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_mining_public_data.py --source-root C:\path\to\mining_warchest
```

Validation-only check:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_mining_public_data.py --check
```

The script copies only the approved runtime files listed above. If a new public
runtime file becomes necessary, add it explicitly to `APPROVED_FILES` in the
script and document it here.

## What Must Not Be Bundled

Do not bundle:

- `reference_material/` wholesale
- local databases such as `sc_intel.db`
- cache/log/export/backup folders
- temporary build folders
- maintainer-only notes or private source files

## Release Validation

Before publishing a release that touches Mining / Salvage data:

1. Run compile validation:

   ```powershell
   .\.venv\Scripts\python.exe -m compileall main.py app
   ```

2. Run a source smoke test:

   - Mining / Salvage opens.
   - Overview shows no false missing reference-data warnings.
   - Ore Finder can find a mineral such as `Laranite`.
   - Locations can find a mineral/location query.
   - Quality Bands loads.
   - Equipment can find `Lancet`.
   - Rock Breaker loads.
   - Refinery opens and can calculate with fallback refinery choices.

3. Run a clean packaged build:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
   ```

4. Inspect the PyInstaller archive:

   ```powershell
   .\.venv\Scripts\pyi-archive_viewer.exe -l -b .\dist\SC-Intel-Tool.exe |
       Select-String -Pattern "mining_public|reference_material|sc_intel.db|cache|logs|exports|backups|temp"
   ```

   Expected:

   - `app/assets/mining_public/...` files are present.
   - `reference_material/` is absent.
   - local database/cache/log/export/temp data is absent.

5. Launch the packaged executable with a fresh or isolated data folder and check
   the Mining / Salvage tabs again.

# agol-bulk-metadata-update

Bulk-update ArcGIS Online feature service metadata (summary, tags, description, credits, terms of use) from a CSV with the ArcGIS API for Python, instead of editing item pages one at a time.

📝 **Background and walkthrough:** [read the blog post on LinkedIn](https://www.linkedin.com/pulse/hidden-challenges-updating-feature-service-metadata-arcgis-dulal-3okvc/)

---

## How it works

1. **Export.** Pull every item in a group (or matching a search) into a CSV, including its current metadata.
2. **Edit.** Fill in or change the metadata in Excel. Leave a cell blank to keep the existing value.
3. **Apply.** Read the CSV back and update each item with `Item.update()`. Use a dry run first to preview the changes.

| CSV column | ArcGIS item property | Shown in AGOL as |
|---|---|---|
| `summary` | `snippet` | Summary |
| `tags` | `tags` (comma-separated → list) | Tags |
| `description` | `description` (HTML allowed) | Description |
| `credits` | `accessInformation` | Credits (Attribution) |
| `terms_of_use` | `licenseInfo` (HTML allowed) | Terms of Use |

`item_name` and `item_type` are included for reference only and are never written back.

## Gotchas this handles

- **Empty cells become "nan".** By default pandas reads blank cells as `NaN`, which gets written to the item as the literal text `nan`. Blank cells are now skipped instead.
- **Credits aren't stored as `credits`.** The field is `accessInformation`. Updating `credits` fails silently and nothing changes.
- **Commas in titles or descriptions.** Building CSV rows with string joins and splitting on commas breaks as soon as a title contains a comma. The export uses proper CSV quoting.
- **Excel and special characters.** Files are read and written as UTF-8 with BOM, so accents and symbols survive a round trip through Excel.
- **No undo.** `--dry-run` / `DRY_RUN = True` shows exactly what would change before anything is updated. Export a copy of the current metadata first as a backup.

## Requirements

- An ArcGIS Online (or Enterprise) account with permission to edit the items: owner or admin
- `arcgis` (ArcGIS API for Python) 2.x and `pandas`. Both are preinstalled in ArcGIS Online Notebooks and ArcGIS Pro

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: ArcGIS Online Notebook (no install)

1. In ArcGIS Online, open **Notebook → New Notebook → Standard**, then upload [`notebooks/update_metadata_from_csv.ipynb`](notebooks/update_metadata_from_csv.ipynb).
2. Set `GROUP_ID` and run the cells down to the export. Download `Features.csv` from the Files pane.
3. Edit it, save it as `metadata.csv`, and upload it to `/arcgis/home/`.
4. Run the import cells with `DRY_RUN = True`, check the output, then set `DRY_RUN = False` and run again.

### Option 2: Command-line script

```bash
# 1. Export a group's items (or --query "owner:me type:\"Feature Service\"", or omit for all your items)
python update_metadata.py --profile myorg export --group 78aa453dfd244bdcb356128a62be9562 --out metadata.csv

# 2. Edit metadata.csv, then preview
python update_metadata.py --profile myorg apply --csv metadata.csv --dry-run

# 3. Apply
python update_metadata.py --profile myorg apply --csv metadata.csv
```

**Sign-in options:**
- `--profile NAME`: a saved `arcgis` profile (recommended)
- `--url https://myorg.maps.arcgis.com --username me`: prompts for your password
- Neither: uses `GIS("home")`, which works when run inside ArcGIS Pro or an AGOL notebook

| Option | Command | Description |
|---|---|---|
| `--group ID` | export | Export items shared to this group |
| `--query Q` | export | Any ArcGIS search query |
| `--type T` | export | Only items of this type, e.g. `"Feature Service"` |
| `--out FILE` | export | Output CSV (default `metadata.csv`) |
| `--csv FILE` | apply | CSV to apply |
| `--dry-run` | apply | Preview changes without updating anything |
| `--clear-blanks` | apply | Treat blank cells as "clear this field" instead of "leave unchanged" |

A sample CSV is in [`templates/metadata_template.csv`](templates/metadata_template.csv).

## Limitations

- This updates **item-level** metadata (what you see on the item page). It doesn't edit formal ISO/FGDC metadata documents or individual layer descriptions within a service.
- Thumbnails, sharing, and categories aren't changed.

## License

[MIT](LICENSE) © 2024 GeoRajesh

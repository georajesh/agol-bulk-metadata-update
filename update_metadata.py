"""
Bulk-update ArcGIS Online / Enterprise item metadata (summary, tags, description, credits,
terms of use) from a CSV file.

Two steps:

  1. export  - write the items in a group (or matching a search) to a CSV, including their
               current metadata, so you can edit it in Excel
  2. apply   - read the edited CSV and update each item

Examples:

  python update_metadata.py export --group 78aa453dfd244bdcb356128a62be9562 --out metadata.csv
  python update_metadata.py apply  --csv metadata.csv --dry-run
  python update_metadata.py apply  --csv metadata.csv

Sign-in (pick one):
  --profile NAME             a saved arcgis profile (recommended)
  --url URL --username USER  prompts for the password
  (nothing)                  GIS("home"), which works inside ArcGIS Online Notebooks / ArcGIS Pro
"""

import argparse
import getpass
import sys

import pandas as pd
from arcgis.gis import GIS

# CSV column -> ArcGIS item property
FIELDS = {
    "summary": "snippet",
    "tags": "tags",
    "description": "description",
    "credits": "accessInformation",
    "terms_of_use": "licenseInfo",
}


def connect(args):
    if args.profile:
        return GIS(profile=args.profile)
    if args.url:
        user = args.username or input("Username: ")
        return GIS(args.url, user, getpass.getpass(f"Password for {user}: "))
    return GIS("home")


def is_blank(value):
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""


def split_tags(value):
    if isinstance(value, list):
        return [t.strip() for t in value if str(t).strip()]
    return [t.strip() for t in str(value).split(",") if t.strip()]


def export_items(gis, args):
    if args.group:
        query = f"group:{args.group}"
    elif args.query:
        query = args.query
    else:
        query = f"owner:{gis.users.me.username}"

    items = gis.content.search(query=query, max_items=args.max_items)
    if args.type:
        items = [i for i in items if i.type == args.type]

    rows = []
    for item in items:
        rows.append(
            {
                "item_id": item.id,
                "item_name": item.title,
                "item_type": item.type,
                "summary": item.snippet or "",
                "tags": ", ".join(item.tags or []),
                "description": item.description or "",
                "credits": item.accessInformation or "",
                "terms_of_use": item.licenseInfo or "",
            }
        )

    # Written with pandas so titles/descriptions containing commas or quotes stay in one cell.
    pd.DataFrame(rows, columns=["item_id", "item_name", "item_type", *FIELDS]).to_csv(
        args.out, index=False, encoding="utf-8-sig"
    )
    print(f"Exported {len(rows)} item(s) to {args.out}")


def build_properties(row, clear_blanks):
    props = {}
    for column, prop in FIELDS.items():
        if column not in row:
            continue
        value = row[column]
        if is_blank(value):
            if clear_blanks:
                props[prop] = [] if prop == "tags" else ""
            continue  # blank cell = leave the existing value alone
        props[prop] = split_tags(value) if prop == "tags" else str(value)
    return props


def apply_metadata(gis, args):
    df = pd.read_csv(args.csv, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if "item_id" not in df.columns:
        sys.exit("CSV must have an 'item_id' column")

    updated = skipped = failed = 0
    for _, row in df.iterrows():
        item_id = str(row["item_id"]).strip()
        if not item_id:
            continue
        try:
            item = gis.content.get(item_id)
            if item is None:
                print(f"[!] Not found (or no access): {item_id}")
                failed += 1
                continue

            props = build_properties(row, args.clear_blanks)
            if not props:
                print(f"[-] Nothing to update: {item.title}")
                skipped += 1
                continue

            if args.dry_run:
                print(f"[dry-run] {item.title} ({item_id}): would set {', '.join(props)}")
                updated += 1
                continue

            if item.update(item_properties=props):
                print(f"[OK] {item.title} ({item_id}): {', '.join(props)}")
                updated += 1
            else:
                print(f"[X] Update returned False: {item.title} ({item_id})")
                failed += 1
        except Exception as e:  # noqa: BLE001 - one bad row shouldn't stop the batch
            print(f"[X] Error updating {item_id}: {e}")
            failed += 1

    label = "Would update" if args.dry_run else "Updated"
    print(f"\n{label}: {updated}   Skipped: {skipped}   Failed: {failed}")
    return failed


def main():
    p = argparse.ArgumentParser(description="Bulk-update ArcGIS Online item metadata from a CSV.")
    auth = p.add_argument_group("sign-in")
    auth.add_argument("--profile", help="Saved arcgis profile name")
    auth.add_argument("--url", help="Portal URL, e.g. https://www.arcgis.com or https://myorg.maps.arcgis.com")
    auth.add_argument("--username", help="Username (password is prompted)")

    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("export", help="Export items and their current metadata to CSV")
    src = e.add_mutually_exclusive_group()
    src.add_argument("--group", help="Group ID to export items from")
    src.add_argument("--query", help="Any ArcGIS search query (default: items you own)")
    e.add_argument("--type", help='Only this item type, e.g. "Feature Service"')
    e.add_argument("--max-items", type=int, default=10000)
    e.add_argument("--out", default="metadata.csv", help="Output CSV (default: metadata.csv)")

    a = sub.add_parser("apply", help="Update items from an edited CSV")
    a.add_argument("--csv", required=True, help="CSV with item_id plus any of: " + ", ".join(FIELDS))
    a.add_argument("--dry-run", action="store_true", help="Show what would change without updating anything")
    a.add_argument(
        "--clear-blanks",
        action="store_true",
        help="Treat blank cells as 'clear this field' (default: blank cells are left unchanged)",
    )

    args = p.parse_args()
    gis = connect(args)
    print(f"Signed in to {gis.url} as {gis.users.me.username if gis.users.me else 'anonymous'}\n")

    if args.command == "export":
        export_items(gis, args)
    else:
        sys.exit(1 if apply_metadata(gis, args) else 0)


if __name__ == "__main__":
    main()

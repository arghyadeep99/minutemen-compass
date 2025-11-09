"""Run a one-off prefetch from the command line and print diagnostics.

Usage (Windows cmd.exe):
  cd backend
  python run_prefetch.py --listing "https://umassamherst.campuslabs.com/engage/organizations"

This will call ToolRegistry.prefetch_events(...) and show whether
`data/events.json` and `data/events.meta.json` were created and any returned error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from tools import ToolRegistry
except Exception as e:
    print("Error importing ToolRegistry:", e)
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing", help="Listing URL to use for scraping", default=None)
    args = parser.parse_args()

    tr = ToolRegistry()
    print("Using data directory:", tr.data_dir.resolve())

    res = tr.prefetch_events(listing_url=args.listing)
    print("prefetch result:", json.dumps(res, ensure_ascii=False, indent=2))

    events_path = tr.data_dir / "events.json"
    meta_path = tr.data_dir / "events.meta.json"

    print(f"events.json exists: {events_path.exists()}")
    if events_path.exists():
        try:
            text = events_path.read_text(encoding="utf-8")
            print("events.json preview (first 2000 chars):")
            print(text[:2000])
        except Exception as e:
            print("Error reading events.json:", e)

    print(f"events.meta.json exists: {meta_path.exists()}")
    if meta_path.exists():
        try:
            print(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            print("Error reading events.meta.json:", e)


if __name__ == "__main__":
    main()

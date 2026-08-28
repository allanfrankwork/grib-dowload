#!/usr/bin/env python3
"""Download a single GRIB parameter by byte range using the .index file."""

import sys
import urllib.request

GRIB_URL = "https://dmi-opendata.s3-eu-north-1.amazonaws.com/forecastdata/HARMONIE_DINI_SF/HARMONIE_DINI_SF_2026-08-25T000000Z_2026-08-25T000000Z.grib"
INDEX_URL = GRIB_URL + ".index"
PARAM_FILTER = "TMP:2 m above ground:anl"   # must appear in the index line
OUTPUT_FILE = "TMP_2m.grib"


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def parse_index(text: str) -> list[tuple[int, str]]:
    """Return list of (byte_offset, full_line) for every record."""
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(":")
        if len(parts) < 2:
            continue
        try:
            offset = int(parts[1])
        except ValueError:
            continue
        records.append((offset, line))
    return records


def find_matches(records: list[tuple[int, str]], param: str) -> list[tuple[int, int | None, str]]:
    """Return (start_byte, end_byte_exclusive, line) for records matching param."""
    matches = []
    for i, (offset, line) in enumerate(records):
        if param in line:
            next_offset = records[i + 1][0] if i + 1 < len(records) else None
            matches.append((offset, next_offset, line))
    return matches


def download_range(url: str, start: int, end: int | None) -> bytes:
    range_header = f"bytes={start}-" if end is None else f"bytes={start}-{end - 1}"
    req = urllib.request.Request(url, headers={"Range": range_header})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def main() -> None:
    print(f"Fetching index: {INDEX_URL}")
    index_text = fetch_text(INDEX_URL)
    records = parse_index(index_text)
    print(f"  {len(records)} records found in index")

    matches = find_matches(records, PARAM_FILTER)
    if not matches:
        sys.exit(f"No records matching '{PARAM_FILTER}' found in index")

    print(f"\nMatching records for '{PARAM_FILTER}':")
    for start, end, line in matches:
        size = f"{end - start:,} bytes" if end is not None else "to EOF"
        print(f"  offset={start:,}  size={size}  {line}")

    if len(matches) > 1:
        print(f"\nMultiple matches — downloading first match only.")

    start, end, line = matches[0]
    size_desc = f"{end - start:,} bytes" if end is not None else "to EOF"
    print(f"\nDownloading {size_desc} from {GRIB_URL}")
    data = download_range(GRIB_URL, start, end)

    with open(OUTPUT_FILE, "wb") as f:
        f.write(data)
    print(f"Saved {len(data):,} bytes → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

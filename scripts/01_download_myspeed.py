"""Download the full MySpeed dataset (TRAI crowdsourced mobile data speeds) from data.gov.in.

Dataset: "Month-wise All India Crowdsourced Mobile Data Speed Measurement"
Resource id: ade6e644-91b8-4d27-97ba-e8c42c48f278 (about 54 million records, ~7.4 GB as JSON)

Why the loop is split by year (and by month for 2018):
the data.gov.in API is backed by Elasticsearch and refuses any request where
offset + limit > 10,000,000. Every year except 2018 has fewer than 10 million
records, and each month of 2018 is below that limit, so paging inside these
partitions reaches every record.

Usage:
    export DATA_GOV_API_KEY=<your free key from https://data.gov.in (My Account -> API key)>
    python3 scripts/01_download_myspeed.py                # all partitions
    python3 scripts/01_download_myspeed.py --years 2023   # one year only

Output: data/myspeed/raw/speed_<YYYY>[_<MM>]_offset_<N>.json (one file per page)
Each file is the raw API response; the rows are under the "records" key.
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

RESOURCE = "ade6e644-91b8-4d27-97ba-e8c42c48f278"
API = f"https://api.data.gov.in/resource/{RESOURCE}"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "myspeed", "raw")
WINDOW = 10_000_000  # Elasticsearch max_result_window on the API


def fetch(key, filters, limit, offset, retries=5):
    params = {"api-key": key, "format": "json", "limit": limit, "offset": offset}
    params.update({f"filters[{k}]": v for k, v in filters.items()})
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                data = json.loads(r.read())
            if data.get("status") == "error":
                raise RuntimeError(data.get("message", "API error"))
            return data
        except Exception as e:  # network hiccups and truncated JSON are common; retry
            wait = 10 * (attempt + 1)
            print(f"  retry {attempt + 1}/{retries} after error: {str(e)[:120]} (waiting {wait}s)")
            time.sleep(wait)
    raise SystemExit(f"Giving up on {filters} offset {offset}")


def partitions(years):
    for y in years:
        if y == 2018:  # 13.3M rows > 10M window, so split by month (data starts in April 2018)
            for m in range(4, 13):
                yield {"year": y, "month": m}, f"{y}_{m:02d}"
        else:
            yield {"year": y}, f"{y}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=list(range(2018, 2026)))
    ap.add_argument("--limit", type=int, default=100_000, help="rows per request (200000 worked in testing)")
    args = ap.parse_args()
    key = os.environ.get("DATA_GOV_API_KEY")
    if not key:
        sys.exit("Set DATA_GOV_API_KEY first (free key from data.gov.in).")
    os.makedirs(OUT, exist_ok=True)
    grand = 0
    for filters, tag in partitions(args.years):
        total = fetch(key, filters, 1, 0).get("total", 0)
        if total > WINDOW:
            sys.exit(f"Partition {tag} has {total} rows (> {WINDOW}); split it further.")
        print(f"{tag}: {total:,} records")
        for offset in range(0, total, args.limit):
            path = os.path.join(OUT, f"speed_{tag}_offset_{offset}.json")
            if os.path.exists(path):
                continue  # resume support
            data = fetch(key, filters, args.limit, offset)
            with open(path, "w") as f:
                json.dump(data, f)
            print(f"  {path.split(os.sep)[-1]}: {data.get('count')} rows")
        grand += total
    print(f"Done. Expected records across partitions: {grand:,}")


if __name__ == "__main__":
    main()

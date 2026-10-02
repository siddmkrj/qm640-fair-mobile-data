"""Re-download the TRAI monthly "Telecom Subscription Data" press releases listed in
data/trai_subscription/sources.csv (Apr 2018 - Mar 2025, 82 months).

The PDFs are already stored in data/trai_subscription/pdf/, so this script is only
needed to verify or refresh them. If trai.gov.in blocks scripted downloads, open the
source_url values in a browser instead.

Usage: python3 scripts/02_download_trai_pdfs.py [--force]
"""
import csv, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "data", "trai_subscription", "sources.csv")
OUT = os.path.join(HERE, "..", "data", "trai_subscription", "pdf")


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open(SRC)))
    for r in rows:
        path = os.path.join(OUT, r["file"])
        if os.path.exists(path) and not force:
            continue
        req = urllib.request.Request(r["source_url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(path, "wb") as f:
            f.write(resp.read())
        print("saved", r["file"])
    print(f"{len(rows)} months listed; files in {OUT}")


if __name__ == "__main__":
    main()

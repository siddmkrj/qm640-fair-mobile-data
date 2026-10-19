"""Convert the raw MySpeed JSON pages to Parquet, one file per page, for fast analysis with DuckDB.
Usage: python3 scripts/04_json_to_parquet.py <raw_json_dir> <parquet_out_dir>
Resumable: pages that already have a parquet file are skipped. No cleaning is done here."""
import json, os, sys, glob
import pyarrow as pa, pyarrow.parquet as pq
from multiprocessing import Pool

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SCHEMA = pa.schema([("operator", pa.string()), ("technology", pa.string()), ("download", pa.string()),
                    ("speed_kbps", pa.float64()), ("signal_strength", pa.string()), ("lsa", pa.string()),
                    ("month", pa.int16()), ("year", pa.int16()), ("src_file", pa.string())])

def conv(f):
    out = os.path.join(OUT, os.path.basename(f).replace(".json", ".parquet"))
    if os.path.exists(out): return 0
    recs = json.load(open(f))["records"]
    cols = {k: [] for k in SCHEMA.names}
    base = os.path.basename(f)
    for r in recs:
        cols["operator"].append(r.get("operator")); cols["technology"].append(r.get("technology"))
        cols["download"].append(r.get("download"))
        try: cols["speed_kbps"].append(float(r.get("speed_kbps")))
        except (TypeError, ValueError): cols["speed_kbps"].append(None)
        cols["signal_strength"].append(None if r.get("signal_strength") is None else str(r.get("signal_strength")))
        cols["lsa"].append(r.get("lsa"))
        try: cols["month"].append(int(float(r.get("month"))))
        except (TypeError, ValueError): cols["month"].append(None)
        try: cols["year"].append(int(float(r.get("year"))))
        except (TypeError, ValueError): cols["year"].append(None)
        cols["src_file"].append(base)
    pq.write_table(pa.table(cols, schema=SCHEMA), out + ".tmp", compression="zstd")
    os.replace(out + ".tmp", out)
    return len(recs)

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(SRC, "*.json")))
    with Pool(3) as p:
        n = sum(p.map(conv, files, chunksize=4))
    print("converted records:", n, "files:", len(files))

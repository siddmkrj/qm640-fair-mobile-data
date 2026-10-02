"""Profile the full MySpeed dataset downloaded by 01_download_myspeed.py.
Usage: python3 scripts/03_profile_myspeed.py speed  -> writes profiling/speed_profile.json
Reads every record (no sampling), runs per-file in parallel and merges counts."""
import json, glob, os, sys, collections, math
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "data", "myspeed")
OUT = os.path.join(HERE, "..", "profiling")

SPEC = {
 "speed": dict(glob="raw/*.json",
   cats=["operator","technology","download","lsa","month","year","signal_na"],
   nums={"speed_kbps":5000.0,"signal_strength":10.0},
   combos=[("year","month"),("year","operator"),("year","technology"),("operator","technology"),("lsa","year"),
           ("download","technology"),("lsa","operator"),("year","signal_na"),("year","lsa_na")]),
}

def bucket(x, w): return math.floor(x / w) * w

def work(args):
    kind, f = args
    sp = SPEC[kind]
    C = {c: collections.Counter() for c in sp["cats"]}
    X = {"x".join(c): collections.Counter() for c in sp["combos"]}
    N = {k: dict(n=0, s=0.0, q=0.0, mn=math.inf, mx=-math.inf, bad=0, h=collections.Counter()) for k in sp["nums"]}
    # per-group numeric sums for speed: mean/median proxies by year x tech x test type
    G = collections.defaultdict(lambda: [0, 0.0, 0.0])
    missing = collections.Counter(); keys = collections.Counter(); total = 0
    d = json.load(open(f))
    meta = {k: d.get(k) for k in ("title","desc","org","source","field","updated_date","created_date","total")}
    for r in d.get("records", []):
        total += 1
        keys["|".join(sorted(r))] += 1
        if True:
            r["signal_na"] = str(r.get("signal_strength")).strip().lower() in ("na","","none","null")
            r["lsa_na"] = str(r.get("lsa")).strip().upper() in ("NA","","NONE")
        for c in sp["cats"]:
            v = r.get(c)
            if v in (None, ""): missing[c] += 1
            C[c][str(v)] += 1
        for k, w in sp["nums"].items():
            v = r.get(k); a = N[k]
            try:
                x = float(v)
                if math.isnan(x): raise ValueError
            except (TypeError, ValueError):
                a["bad"] += 1; continue
            a["n"] += 1; a["s"] += x; a["q"] += x*x; a["mn"] = min(a["mn"], x); a["mx"] = max(a["mx"], x)
            a["h"][bucket(min(x, 300000) if k == "speed_kbps" else x, w)] += 1
        for c in sp["combos"]:
            X["x".join(c)]["|".join(str(r.get(z)) for z in c)] += 1
        if kind == "speed":
            try:
                x = float(r["speed_kbps"]); g = G[f'{r["year"]}|{r["technology"]}|{r["download"]}']
                g[0] += 1; g[1] += x; g[2] += x*x
            except (TypeError, ValueError, KeyError): pass
    return dict(total=total, meta=meta, C=C, X=X, N=N, G=dict(G), missing=missing, keys=keys)

def merge(parts):
    out = None
    for p in parts:
        if out is None: out = p; continue
        out["total"] += p["total"]
        for k in ("missing","keys"): out[k].update(p[k])
        for c in out["C"]: out["C"][c].update(p["C"][c])
        for c in out["X"]: out["X"][c].update(p["X"][c])
        for k, a in out["N"].items():
            b = p["N"][k]
            a["n"] += b["n"]; a["s"] += b["s"]; a["q"] += b["q"]; a["bad"] += b["bad"]
            a["mn"] = min(a["mn"], b["mn"]); a["mx"] = max(a["mx"], b["mx"]); a["h"].update(b["h"])
        for g, v in p["G"].items():
            t = out["G"].setdefault(g, [0, 0.0, 0.0]); t[0] += v[0]; t[1] += v[1]; t[2] += v[2]
    return out

def fin(a):
    if not a["n"]: return a
    m = a["s"] / a["n"]; sd = math.sqrt(max(a["q"] / a["n"] - m*m, 0))
    # approximate median from histogram
    half, acc, med = a["n"]/2, 0, None
    for b in sorted(a["h"]):
        acc += a["h"][b]
        if acc >= half: med = b; break
    return dict(n=a["n"], non_numeric_or_missing=a["bad"], mean=m, sd=sd, min=a["mn"], max=a["mx"],
                approx_median_bucket=med, hist={str(k): v for k, v in sorted(a["h"].items())})

def main(kind):
    files = sorted(glob.glob(os.path.join(BASE, SPEC[kind]["glob"])))
    with Pool(3) as pool:
        parts = pool.map(work, [(kind, f) for f in files], chunksize=1)
    m = merge(parts)
    res = dict(kind=kind, files=len(files), total_records=m["total"], api_metadata=m["meta"],
               key_sets=dict(m["keys"]), missing=dict(m["missing"]),
               categorical={c: dict(v.most_common()) for c, v in m["C"].items()},
               numeric={k: fin(a) for k, a in m["N"].items()},
               crosstabs={c: dict(sorted(v.items())) for c, v in m["X"].items()})
    if kind == "speed":
        res["speed_by_year_tech_test"] = {g: dict(n=v[0], mean_kbps=v[1]/v[0], sd=math.sqrt(max(v[2]/v[0]-(v[1]/v[0])**2, 0)))
                                          for g, v in sorted(m["G"].items()) if v[0]}
    json.dump(res, open(os.path.join(OUT, f"{kind}_profile.json"), "w"), indent=1, default=str)
    print("done", kind, m["total"])

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "speed")

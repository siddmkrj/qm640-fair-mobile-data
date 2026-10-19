"""Clean the MySpeed data and write EDA aggregates (interim report).
Usage: python3 scripts/05_clean_and_eda.py <parquet_dir> <out_dir>
Cleaning rules (see docs/data_schema.md): study window Apr 2018 to Dec 2024, provider merge
(IDEA/VODAFONE/Vi India -> Vi, CELLONE/BSNL -> BSNL, DOLPHIN and UNINOR dropped), TRAI circle
categories, speed cap flag at 149,999 kbps, signal 'na' -> NULL. Nothing is deleted from the raw files."""
import duckdb, sys, os
P, OUT = sys.argv[1] + "/*.parquet", sys.argv[2]
os.makedirs(OUT, exist_ok=True)
con = duckdb.connect(); con.execute("SET memory_limit='1500MB'; SET threads=3; SET preserve_insertion_order=false")
con.execute("SELECT setseed(0.42)"); con.execute("SET temp_directory='%s'" % os.path.expanduser("~/ducktmp"))

con.execute(f"""
CREATE VIEW raw AS SELECT * FROM read_parquet('{P}');
CREATE VIEW clean AS
SELECT
  CASE operator WHEN 'JIO' THEN 'Jio' WHEN 'AIRTEL' THEN 'Airtel'
       WHEN 'IDEA' THEN 'Vi' WHEN 'VODAFONE' THEN 'Vi' WHEN 'Vi India' THEN 'Vi'
       WHEN 'CELLONE' THEN 'BSNL' WHEN 'BSNL' THEN 'BSNL' END AS provider,
  operator AS operator_raw, technology, download AS test_type,
  speed_kbps, speed_kbps / 1000.0 AS speed_mbps,
  CASE WHEN speed_kbps >= 149000 THEN 1 ELSE 0 END AS speed_capped,
  TRY_CAST(signal_strength AS DOUBLE) AS signal_dbm,
  CASE WHEN lsa = 'NA' OR lsa IS NULL THEN NULL ELSE lsa END AS circle,
  CASE
    WHEN lsa IN ('Delhi','Mumbai','Kolkata','Chennai') THEN 'Metro'
    WHEN lsa IN ('Maharashtra','Gujarat','Andhra Pradesh','Karnataka','Tamil Nadu') THEN 'A'
    WHEN lsa IN ('Kerala','Punjab','Haryana','UP East','UP West','Rajasthan','Madhya Pradesh','West Bengal') THEN 'B'
    WHEN lsa IN ('Himachal Pradesh','Bihar','Orissa','Assam','North East','Jammu & Kashmir') THEN 'C'
    ELSE NULL END AS category,
  month, year, src_file
FROM raw
WHERE (year BETWEEN 2019 AND 2024 OR (year = 2018 AND month >= 4))
  AND operator NOT IN ('DOLPHIN','UNINOR');
""")

def save(name, sql):
    df = con.execute(sql).df(); df.to_csv(os.path.join(OUT, name + ".csv"), index=False); print(name, df.shape); return df

# ---- cleaning log counts
save("clean_log", """
SELECT 'raw records' AS item, count(*) AS n FROM raw
UNION ALL SELECT 'outside window (2025 Jan-Mar)', count(*) FROM raw WHERE year = 2025
UNION ALL SELECT 'DOLPHIN or UNINOR', count(*) FROM raw WHERE operator IN ('DOLPHIN','UNINOR')
UNION ALL SELECT 'in-window study records', count(*) FROM clean
UNION ALL SELECT 'circle missing (NA)', count(*) FROM clean WHERE circle IS NULL
UNION ALL SELECT 'signal missing (na)', count(*) FROM clean WHERE signal_dbm IS NULL
UNION ALL SELECT 'speed = 0 kbps', count(*) FROM clean WHERE speed_kbps = 0
UNION ALL SELECT 'speed at cap (>=149,000 kbps)', count(*) FROM clean WHERE speed_capped = 1
UNION ALL SELECT 'speed null', count(*) FROM clean WHERE speed_kbps IS NULL
UNION ALL SELECT 'signal outside -120..-40 dBm', count(*) FROM clean WHERE signal_dbm IS NOT NULL AND (signal_dbm < -120 OR signal_dbm > -40)
UNION ALL SELECT '2G tests', count(*) FROM clean WHERE technology = '2G'
UNION ALL SELECT '4G download tests', count(*) FROM clean WHERE technology = '4G' AND test_type = 'download'
UNION ALL SELECT '4G download with circle', count(*) FROM clean WHERE technology = '4G' AND test_type = 'download' AND circle IS NOT NULL
UNION ALL SELECT '4G download with circle and signal', count(*) FROM clean WHERE technology = '4G' AND test_type = 'download' AND circle IS NOT NULL AND signal_dbm IS NOT NULL
""")
# exact duplicate rows (all 8 raw fields identical), computed year by year to limit memory
import pandas as pd
rows = []
for y in range(2018, 2025):
    r = con.execute(f"""SELECT {y} AS year, (SELECT count(*) FROM clean WHERE year={y}) AS total_rows, count(*) AS distinct_rows FROM
        (SELECT DISTINCT operator_raw, technology, test_type, speed_kbps, signal_dbm, circle, month FROM clean WHERE year={y})""").fetchone()
    rows.append(r); print("dup", r)
d = pd.DataFrame(rows, columns=["year", "total_rows", "distinct_rows"]); d["exact_duplicate_rows"] = d.total_rows - d.distinct_rows
d.to_csv(os.path.join(OUT, "duplicates.csv"), index=False)
# ---- EDA aggregates
save("tests_by_year_provider", "SELECT year, provider, count(*) n FROM clean GROUP BY 1,2 ORDER BY 1,2")
save("tests_by_year_tech_type", "SELECT year, technology, test_type, count(*) n FROM clean GROUP BY 1,2,3 ORDER BY 1,2,3")
save("missing_by_year", """
SELECT year, count(*) n, avg(CASE WHEN circle IS NULL THEN 1 ELSE 0 END) circle_missing_rate,
       avg(CASE WHEN signal_dbm IS NULL THEN 1 ELSE 0 END) signal_missing_rate FROM clean GROUP BY 1 ORDER BY 1""")
save("missing_by_year_provider", """
SELECT year, provider, count(*) n, avg(CASE WHEN circle IS NULL THEN 1 ELSE 0 END) circle_missing_rate,
       avg(CASE WHEN signal_dbm IS NULL THEN 1 ELSE 0 END) signal_missing_rate FROM clean GROUP BY 1,2 ORDER BY 1,2""")
save("speed_by_category_year", """
SELECT category, year, count(*) n, avg(speed_mbps) mean_mbps, median(speed_mbps) median_mbps,
       quantile_cont(speed_mbps, 0.2) p20_mbps, quantile_cont(speed_mbps, 0.8) p80_mbps,
       avg(ln(1 + speed_mbps)) mean_log, stddev_samp(speed_mbps) sd_mbps
FROM clean WHERE technology='4G' AND test_type='download' AND category IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
save("speed_by_category_provider", """
SELECT category, provider, count(*) n, avg(speed_mbps) mean_mbps, median(speed_mbps) median_mbps, avg(ln(1 + speed_mbps)) mean_log
FROM clean WHERE technology='4G' AND test_type='download' AND category IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
save("speed_by_category_provider_year", """
SELECT category, provider, year, count(*) n, median(speed_mbps) median_mbps, avg(ln(1 + speed_mbps)) mean_log
FROM clean WHERE technology='4G' AND test_type='download' AND category IS NOT NULL GROUP BY 1,2,3 ORDER BY 1,2,3""")
save("speed_by_circle", """
SELECT circle, category, count(*) n, median(speed_mbps) median_mbps, avg(speed_mbps) mean_mbps, avg(signal_dbm) mean_signal
FROM clean WHERE technology='4G' AND test_type='download' AND circle IS NOT NULL GROUP BY 1,2 ORDER BY 2,1""")
save("speed_by_signal_bin", """
SELECT technology, test_type, floor(signal_dbm/10)*10 AS signal_bin, count(*) n, median(speed_mbps) median_mbps, avg(speed_mbps) mean_mbps
FROM clean WHERE signal_dbm IS NOT NULL AND technology IN ('3G','4G') GROUP BY 1,2,3 ORDER BY 1,2,3""")
save("speed_hist_4g_download", """
SELECT least(floor(speed_mbps/5)*5, 150) AS mbps_bin, count(*) n FROM clean WHERE technology='4G' AND test_type='download' GROUP BY 1 ORDER BY 1""")
save("tests_by_circle_provider", """
SELECT circle, category, provider, count(*) n FROM clean WHERE circle IS NOT NULL GROUP BY 1,2,3 ORDER BY 1,3""")
save("tests_by_circle_provider_year", """
SELECT circle, category, provider, year, count(*) n FROM clean WHERE circle IS NOT NULL GROUP BY 1,2,3,4 ORDER BY 1,3,4""")
save("signal_by_category", """
SELECT category, provider, count(*) n, avg(signal_dbm) mean_signal, median(signal_dbm) median_signal
FROM clean WHERE technology='4G' AND signal_dbm IS NOT NULL AND category IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
save("capped_by_year", "SELECT year, avg(speed_capped) cap_rate, count(*) n FROM clean WHERE technology='4G' AND test_type='download' GROUP BY 1 ORDER BY 1")
save("p20_by_year_4g_download", """
SELECT year, quantile_cont(speed_mbps,0.2) p20 FROM clean WHERE technology='4G' AND test_type='download' AND circle IS NOT NULL GROUP BY 1 ORDER BY 1""")

# ---- stratified analysis sample: 4G download, circle known, up to 15,000 per provider x category cell
con.execute("""
COPY (
  SELECT provider, category, circle, year, month, speed_mbps, speed_capped, signal_dbm, technology, test_type
  FROM (SELECT *, row_number() OVER (PARTITION BY provider, category ORDER BY random()) rn
        FROM clean WHERE technology='4G' AND test_type='download' AND circle IS NOT NULL)
  WHERE rn <= 15000
) TO '%s' (HEADER, DELIMITER ',')
""" % os.path.join(OUT, "analysis_sample_4g_download.csv"))
print("sample rows:", con.execute("SELECT count(*) FROM read_csv_auto('%s')" % os.path.join(OUT, "analysis_sample_4g_download.csv")).fetchone())

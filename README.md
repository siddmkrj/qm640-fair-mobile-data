# Fair Mobile Data Service in India

QM 640 Data Analytics Capstone, Walsh College. Siddhartha Mukherjee; mentor Mr Rishabh Pandey.
Uses only public Indian government data, with no personal information (nothing finer than a telecom circle).

## Research questions

| RQ | Question |
|---|---|
| RQ1 | Is 4G download speed lower in Category C circles, before and after controlling for signal and load, and is the gap closing (2018–2024)? |
| RQ2 | Does that gap differ by provider (Jio, Airtel, Vi, BSNL)? |
| RQ3 | Do provider test shares match subscriber shares, and does re-weighting change rankings and the gap? |
| RQ4 | Does a poor-speed classifier err more for some circles or providers, does re-weighting help, and does fairness hold on 2023–24 data? |
| RQ5 | Is the crowd data unevenly incomplete, and are poorer circles under-measured? |

## Layout

```
data/data_dictionary.csv          variables: type, units, meaning, role
data/myspeed/myspeed_sample.csv   55,400-row CSV sample, raw 8 columns (quick look)
data/myspeed/sample_parquet/      1% random sample, 539,187 rows, Parquet by year, 3.5 MB (runs the full pipeline)
data/eda/                         cleaning counts, EDA tables, parsed TRAI tables, model outputs, 221,217-row analysis sample
data/trai_subscription/           82 monthly TRAI PDFs + sources.csv (official URLs)
scripts/01_download_myspeed.py    download all MySpeed records (data.gov.in API)
scripts/02_download_trai_pdfs.py  re-download / verify the TRAI PDFs
scripts/03_profile_myspeed.py     profile every record
scripts/04_json_to_parquet.py     convert downloaded JSON to Parquet
scripts/05_clean_and_eda.py       cleaning log, EDA tables, stratified analysis sample
scripts/06_parse_trai_subscribers.py  parse TRAI Annexure II/III PDFs
scripts/07_rq3_rq5_representation.py  representation ratios, chi-squared, coverage
scripts/08_models_rq1_rq2_rq4.py  mixed models and classifiers
scripts/09_figures.py             report figures (10_paired_figures.py: two-panel variant)
profiling/speed_profile.json      profile of all 54,006,839 records
docs/data_schema.md               quality flags, provider and circle grouping
```

## Reproduce

```bash
pip install -r requirements.txt
export DATA_GOV_API_KEY=your_key            # free key from data.gov.in
python3 scripts/01_download_myspeed.py      # 54,006,839 records, 2–4 h, resumes if stopped
python3 scripts/03_profile_myspeed.py speed
```

The full download is 7.2 GB and takes 2 to 4 hours. For a quick view, use the 1% sample instead. It has the same columns as the full Parquet files, so every script from 05 onwards runs on it (seed 640, Bernoulli sampling, about 5 minutes end to end):

```bash
python3 scripts/05_clean_and_eda.py data/myspeed/sample_parquet data/eda_sample
python3 scripts/06_parse_trai_subscribers.py data/trai_subscription/pdf/*.pdf > data/eda_sample/trai_subscribers_by_circle_operator.csv
python3 scripts/07_rq3_rq5_representation.py data/eda_sample tables_sample
python3 scripts/08_models_rq1_rq2_rq4.py data/eda_sample tables_sample
python3 scripts/09_figures.py data/eda_sample tables_sample fig_sample
```

Numbers from the sample differ a little from the report, which uses all 54 million records. `data/myspeed/myspeed_sample.csv` is a smaller CSV for a quick look at the raw fields. The TRAI PDFs are already included.

## Data

| | MySpeed speed tests | TRAI subscription data |
|---|---|---|
| Source | [data.gov.in](https://www.data.gov.in/resource/month-wise-all-india-crowdsourced-mobile-data-speed-measurement) (TRAI/DoT) | [trai.gov.in](https://www.trai.gov.in/release-publication/reports/telecom-subscriptions-reports) monthly press releases |
| Content | 54,006,839 tests, 8 fields | Subscribers and active (VLR) % by provider × circle |
| Period | Apr 2018 – Mar 2025 (study: to Dec 2024) | Apr 2018 – Mar 2025 |
| Gaps | Circle missing 19.9% (68% in 2022); signal missing 9.5%; no 5G label; speed capped at 150 Mbps | Aug 2020 and Dec 2021 not online; Sep–Oct 2020 scanned |

## Licence

Data: [Government Open Data License – India](https://data.gov.in/government-open-data-license-india) (TRAI, DoT). Code: academic use.

# Fair Mobile Data Service in India

QM 640 Data Analytics Capstone, Walsh College. Siddhartha Mukherjee; mentor Ms Sanhita Karmakar.
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
data/myspeed/myspeed_sample.csv   55,400-row sample (full data → data/myspeed/raw/, not in git)
data/trai_subscription/           82 monthly TRAI PDFs + sources.csv (official URLs)
scripts/01_download_myspeed.py    download all MySpeed records (data.gov.in API)
scripts/02_download_trai_pdfs.py  re-download / verify the TRAI PDFs
scripts/03_profile_myspeed.py     profile every record
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

The TRAI PDFs are already included. For a quick start, use the sample CSV (same 8 columns as the full data).

## Data

| | MySpeed speed tests | TRAI subscription data |
|---|---|---|
| Source | [data.gov.in](https://www.data.gov.in/resource/month-wise-all-india-crowdsourced-mobile-data-speed-measurement) (TRAI/DoT) | [trai.gov.in](https://www.trai.gov.in/release-publication/reports/telecom-subscriptions-reports) monthly press releases |
| Content | 54,006,839 tests, 8 fields | Subscribers and active (VLR) % by provider × circle |
| Period | Apr 2018 – Mar 2025 (study: to Dec 2024) | Apr 2018 – Mar 2025 |
| Gaps | Circle missing 19.9% (68% in 2022); signal missing 9.5%; no 5G label; speed capped at 150 Mbps | Aug 2020 and Dec 2021 not online; Sep–Oct 2020 scanned |

## Licence

Data: [Government Open Data License – India](https://data.gov.in/government-open-data-license-india) (TRAI, DoT). Code: academic use.

# MySpeed data notes

Profiled on all 54,006,839 records (Apr 2018 – Mar 2025). One row = one speed test.

| Field | Values / notes |
|---|---|
| operator | JIO 57%, AIRTEL 27%, IDEA 4.8%, VODAFONE 4.6%, Vi India 4.0%, CELLONE 2.2%, BSNL 13k, DOLPHIN 774, UNINOR 68 |
| technology | 4G 95.7%, 3G 4.3%, 2G 1,239; no 5G label |
| download | download / upload, 50% each |
| speed_kbps | 0 – 149,999 (capped at 150 Mbps); skewed, so use log or median |
| signal_strength | −112 to −50 dBm; "na" in 9.5% |
| lsa | 23 circles + NA (20% overall, 68% in 2022, 0% in 2024–25) |
| month, year | 2018 13.3M rows … 2024 4.2M, 2025 0.3M |

**Quality flags:** circle is the finest geography; no 5G label (the 2024 speed jump may include 5G); speed cap; every API file is titled "March, 2018" (platform metadata error). Still to check: zero speeds, duplicates, Haryana over-sampling.

## Provider mapping

| Raw | Final |
|---|---|
| JIO | Jio |
| AIRTEL | Airtel |
| IDEA, VODAFONE, Vi India | Vi |
| CELLONE, BSNL | BSNL |
| DOLPHIN (MTNL), UNINOR | excluded |

## Circle categories (TRAI; Jha & Saha, 2019)

- Metro: Delhi, Mumbai, Kolkata, Chennai
- A: Maharashtra, Gujarat, Andhra Pradesh, Karnataka, Tamil Nadu
- B: Kerala, Punjab, Haryana, UP East, UP West, Rajasthan, Madhya Pradesh, West Bengal
- C: Himachal Pradesh, Bihar, Orissa, Assam, North East, Jammu & Kashmir

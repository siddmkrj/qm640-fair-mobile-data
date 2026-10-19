"""RQ3 and RQ5 interim analysis: test share vs subscriber share per circle, representation ratios,
chi-squared goodness of fit, Cramer's V, and tests per 1,000 active subscribers.
Usage: python3 scripts/07_rq3_rq5_representation.py <eda_dir> <out_dir>"""
import pandas as pd, numpy as np, sys, os
from scipy.stats import chi2
EDA, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
CAT = {'Delhi':'Metro','Mumbai':'Metro','Kolkata':'Metro','Chennai':'Metro','Maharashtra':'A','Gujarat':'A','Andhra Pradesh':'A','Karnataka':'A','Tamil Nadu':'A',
       'Kerala':'B','Punjab':'B','Haryana':'B','UP East':'B','UP West':'B','Rajasthan':'B','Madhya Pradesh':'B','West Bengal':'B',
       'Himachal Pradesh':'C','Bihar':'C','Orissa':'C','Assam':'C','North East':'C','Jammu & Kashmir':'C'}
sub = pd.read_csv(os.path.join(EDA, 'trai_subscribers_by_circle_operator.csv'))
sub['year'] = sub.month.str[:4].astype(int)
sub['vlr_pct'] = pd.to_numeric(sub.vlr_pct, errors='coerce')
sub['active'] = sub.subscribers * sub.vlr_pct.fillna(sub.vlr_pct.median()) / 100
tests = pd.read_csv(os.path.join(EDA, 'tests_by_circle_provider.csv'))
tests_y = pd.read_csv(os.path.join(EDA, 'tests_by_circle_provider_year.csv'))
# MySpeed has Chennai separately; TRAI folds Chennai into Tamil Nadu. Merge Chennai tests into Tamil Nadu for RQ3.
def fold(df):
    df = df.copy(); df.loc[df.circle == 'Chennai', 'circle'] = 'Tamil Nadu'
    keys = [c for c in df.columns if c not in ('n', 'category')]
    df = df.groupby(keys, as_index=False).n.sum(); df['category'] = df.circle.map(CAT); return df
tests, tests_y = fold(tests), fold(tests_y)

# ---- pooled 2018-2024: mean monthly subscribers per circle x operator
msub = sub.groupby(['circle', 'operator'], as_index=False).agg(subscribers=('subscribers', 'mean'), active=('active', 'mean'), months=('month', 'nunique'))
rows = []
for c, g in tests.groupby('circle'):
    s = msub[msub.circle == c].set_index('operator').subscribers
    t = g.set_index('provider').n
    ops = [o for o in ['Jio', 'Airtel', 'Vi', 'BSNL'] if o in s.index and s[o] > 0]
    t = t.reindex(ops).fillna(0); s = s.reindex(ops)
    N = t.sum(); exp = s / s.sum() * N
    chi = ((t - exp) ** 2 / exp).sum(); k = len(ops); p = 1 - chi2.cdf(chi, k - 1); V = np.sqrt(chi / (N * (k - 1)))
    for o in ops:
        rows.append(dict(circle=c, category=CAT[c], provider=o, tests=int(t[o]), test_share=t[o] / N, subscriber_share=s[o] / s.sum(),
                         representation_ratio=(t[o] / N) / (s[o] / s.sum()), weight=(s[o] / s.sum()) / (t[o] / N) if t[o] > 0 else np.nan,
                         chi2=chi, df=k - 1, p_value=p, cramers_v=V, n_tests_circle=int(N)))
rep = pd.DataFrame(rows); rep.to_csv(os.path.join(OUT, 'rq3_representation_by_circle.csv'), index=False)
circ = rep.groupby(['circle', 'category'], as_index=False).agg(n_tests=('n_tests_circle', 'first'), chi2=('chi2', 'first'), df=('df', 'first'), p_value=('p_value', 'first'), cramers_v=('cramers_v', 'first'))
circ.to_csv(os.path.join(OUT, 'rq3_chi2_by_circle.csv'), index=False)
# national summary per provider
nat = rep.groupby('provider').apply(lambda g: pd.Series(dict(tests=g.tests.sum(), test_share=g.tests.sum() / rep.tests.sum(),
      subscriber_share=(g.subscriber_share * g.n_tests_circle).sum() / g.n_tests_circle.sum()))).reset_index()
natsub = msub.groupby('operator').subscribers.sum(); nat['subscriber_share_national'] = nat.provider.map(natsub / natsub.sum())
nat['representation_ratio'] = nat.test_share / nat.subscriber_share_national
nat.to_csv(os.path.join(OUT, 'rq3_national_summary.csv'), index=False)
# by category
cat = rep.groupby(['category', 'provider'], as_index=False).agg(tests=('tests', 'sum'))
csub = msub.assign(category=msub.circle.map(CAT)).groupby(['category', 'operator']).subscribers.sum().reset_index().rename(columns={'operator': 'provider'})
cat = cat.merge(csub, on=['category', 'provider']); cat['test_share'] = cat.tests / cat.groupby('category').tests.transform('sum')
cat['subscriber_share'] = cat.subscribers / cat.groupby('category').subscribers.transform('sum'); cat['representation_ratio'] = cat.test_share / cat.subscriber_share
cat.to_csv(os.path.join(OUT, 'rq3_representation_by_category.csv'), index=False)

# ---- by year (RQ3 trend and RQ5 coverage)
ysub = sub.groupby(['year', 'circle', 'operator'], as_index=False).agg(subscribers=('subscribers', 'mean'), active=('active', 'mean'))
ty = tests_y.merge(ysub, left_on=['year', 'circle', 'provider'], right_on=['year', 'circle', 'operator'], how='left')
ty['test_share'] = ty.n / ty.groupby(['year', 'circle']).n.transform('sum')
ty['subscriber_share'] = ty.subscribers / ty.groupby(['year', 'circle']).subscribers.transform('sum')
ty['representation_ratio'] = ty.test_share / ty.subscriber_share
ty.to_csv(os.path.join(OUT, 'rq3_representation_by_circle_year.csv'), index=False)
yr = ty.groupby(['year', 'provider'], as_index=False).agg(tests=('n', 'sum'), subscribers=('subscribers', 'sum'))
yr['test_share'] = yr.tests / yr.groupby('year').tests.transform('sum'); yr['subscriber_share'] = yr.subscribers / yr.groupby('year').subscribers.transform('sum')
yr['representation_ratio'] = yr.test_share / yr.subscriber_share; yr.to_csv(os.path.join(OUT, 'rq3_representation_by_year.csv'), index=False)

# ---- RQ5: tests per 1,000 active subscribers per circle category and year (all providers)
cov = ty.groupby(['year', 'category'], as_index=False).agg(tests=('n', 'sum'), active=('active', 'sum'))
cov['tests_per_1000_active'] = cov.tests / cov.active * 1000
cov.to_csv(os.path.join(OUT, 'rq5_tests_per_1000_active_by_category_year.csv'), index=False)
covc = ty.groupby(['circle', 'category'], as_index=False).agg(tests=('n', 'sum'), active=('active', 'mean'))
# mean active across years x providers: recompute properly
act = ysub.groupby('circle').active.mean() * 0 + ysub.groupby(['circle']).apply(lambda g: g.groupby('year').active.sum().mean())
covc = tests.groupby(['circle', 'category'], as_index=False).n.sum().merge(act.rename('active_mean').reset_index(), on='circle')
covc['tests_per_1000_active_per_year'] = covc.n / 7 / covc.active_mean * 1000
covc.to_csv(os.path.join(OUT, 'rq5_tests_per_1000_active_by_circle.csv'), index=False)
catcov = covc.groupby('category').apply(lambda g: pd.Series(dict(tests=g.n.sum(), active=g.active_mean.sum(), tests_per_1000_active_per_year=g.n.sum() / 7 / g.active_mean.sum() * 1000))).reset_index()
catcov.to_csv(os.path.join(OUT, 'rq5_tests_per_1000_active_by_category.csv'), index=False)
print(nat.round(3)); print(cat.round(3)); print(catcov.round(2)); print(circ.sort_values('cramers_v').round(3).to_string())

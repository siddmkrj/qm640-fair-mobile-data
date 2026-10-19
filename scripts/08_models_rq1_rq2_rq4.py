"""Preliminary models on the stratified 4G download sample (interim report).
RQ1: Welch ANOVA, mixed-effects Model A (category + year, circle random intercept) and Model B (+ signal, + log active subscribers).
RQ2: Model B + provider + provider x category.
RQ4: poor_speed classifiers (logistic baseline, random forest, LightGBM), temporal split, group fairness metrics.
Usage: python3 scripts/08_models_rq1_rq2_rq4.py <eda_dir> <out_dir>"""
import pandas as pd, numpy as np, sys, os, json, warnings
warnings.filterwarnings('ignore')
import statsmodels.formula.api as smf, statsmodels.api as sm
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, f1_score, recall_score, precision_score, accuracy_score, confusion_matrix
import lightgbm as lgb
EDA, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
np.random.seed(42)
df = pd.read_csv(os.path.join(EDA, 'analysis_sample_4g_download.csv'))
df['log_speed'] = np.log1p(df.speed_mbps)
df['category'] = pd.Categorical(df.category, ['Metro', 'A', 'B', 'C'])
df['provider'] = pd.Categorical(df.provider, ['Jio', 'Airtel', 'Vi', 'BSNL'])
# active subscribers per provider x circle x year from the TRAI tables (Chennai uses Tamil Nadu)
sub = pd.read_csv(os.path.join(EDA, 'trai_subscribers_by_circle_operator.csv'))
sub['year'] = sub.month.str[:4].astype(int); sub['vlr_pct'] = pd.to_numeric(sub.vlr_pct, errors='coerce')
sub['active'] = sub.subscribers * sub.vlr_pct.fillna(sub.vlr_pct.median()) / 100
act = sub.groupby(['year', 'circle', 'operator'], as_index=False).active.mean().rename(columns={'operator': 'provider'})
df['circle_trai'] = df.circle.replace({'Chennai': 'Tamil Nadu'})
df = df.merge(act, left_on=['year', 'circle_trai', 'provider'], right_on=['year', 'circle', 'provider'], how='left', suffixes=('', '_t')).drop(columns=['circle_t'])
df['log_active'] = np.log(df.active / 1e6)
print('rows', len(df), 'signal missing', df.signal_dbm.isna().mean().round(3), 'active missing', df.active.isna().mean().round(3))
summary = {}
# ---------------- RQ1
desc = df.groupby('category').log_speed.agg(['count', 'mean', 'std']); desc['median_mbps'] = df.groupby('category').speed_mbps.median()
desc.to_csv(os.path.join(OUT, 'rq1_descriptives_sample.csv'))
groups = [g.log_speed.values for _, g in df.groupby('category')]
w = stats.alexandergovern(*groups) if hasattr(stats, 'alexandergovern') else None
f, p = stats.f_oneway(*groups)
# Welch ANOVA via statsmodels oneway
from statsmodels.stats.oneway import anova_oneway
welch = anova_oneway(groups, use_var='unequal', welch_correction=True)
# eta squared from classic one-way
ss_b = sum(len(g) * (g.mean() - df.log_speed.mean()) ** 2 for g in groups); ss_t = ((df.log_speed - df.log_speed.mean()) ** 2).sum()
summary['rq1_welch'] = dict(F=float(welch.statistic), df1=float(welch.df_num), df2=float(welch.df_denom), p=float(welch.pvalue), eta2=float(ss_b / ss_t))
d_sig = df.dropna(subset=['signal_dbm', 'log_active']).copy()
mA = smf.mixedlm('log_speed ~ C(category) + C(year)', d_sig, groups=d_sig['circle']).fit(reml=False)
mB = smf.mixedlm('log_speed ~ C(category) + C(year) + signal_dbm + log_active', d_sig, groups=d_sig['circle']).fit(reml=False)
def tidy(m, name):
    t = pd.DataFrame(dict(term=m.params.index, coef=m.params.values, se=m.bse.values, p=m.pvalues.values)); t['model'] = name; return t
tab = pd.concat([tidy(mA, 'Model A (total gap)'), tidy(mB, 'Model B (with controls)')]); tab.to_csv(os.path.join(OUT, 'rq1_mixed_models.csv'), index=False)
icc = lambda m: float(m.cov_re.iloc[0, 0] / (m.cov_re.iloc[0, 0] + m.scale))
summary['rq1_models'] = dict(n=int(len(d_sig)), circles=int(d_sig.circle.nunique()),
    A=dict(catC=float(mA.params['C(category)[T.C]']), catC_se=float(mA.bse['C(category)[T.C]']), catC_p=float(mA.pvalues['C(category)[T.C]']),
           catA=float(mA.params['C(category)[T.A]']), catB=float(mA.params['C(category)[T.B]']), icc=icc(mA), aic=float(mA.aic), llf=float(mA.llf)),
    B=dict(catC=float(mB.params['C(category)[T.C]']), catC_se=float(mB.bse['C(category)[T.C]']), catC_p=float(mB.pvalues['C(category)[T.C]']),
           catA=float(mB.params['C(category)[T.A]']), catB=float(mB.params['C(category)[T.B]']), signal=float(mB.params['signal_dbm']), signal_p=float(mB.pvalues['signal_dbm']),
           log_active=float(mB.params['log_active']), log_active_p=float(mB.pvalues['log_active']), icc=icc(mB), aic=float(mB.aic), llf=float(mB.llf)))
# trend: category x year interaction (Model A + interaction), test C x year slope with year numeric
mT = smf.mixedlm('log_speed ~ C(category) * yr', d_sig.assign(yr=d_sig.year - 2018), groups=d_sig['circle']).fit(reml=False)
summary['rq1_trend'] = {k: float(v) for k, v in mT.params.items() if 'yr' in k}
summary['rq1_trend_p'] = {k: float(v) for k, v in mT.pvalues.items() if 'yr' in k}
# ---------------- RQ2
m2 = smf.mixedlm('log_speed ~ C(category) * C(provider) + C(year) + signal_dbm + log_active', d_sig, groups=d_sig['circle']).fit(reml=False)
tidy(m2, 'RQ2 interaction model').to_csv(os.path.join(OUT, 'rq2_mixed_model.csv'), index=False)
# likelihood-ratio test for the interaction
m2b = smf.mixedlm('log_speed ~ C(category) + C(provider) + C(year) + signal_dbm + log_active', d_sig, groups=d_sig['circle']).fit(reml=False)
lr = 2 * (m2.llf - m2b.llf); summary['rq2_lrt'] = dict(lr=float(lr), df=9, p=float(1 - stats.chi2.cdf(lr, 9)))
# adjusted Category C gap per provider = catC + catC:provider
cc = m2.params
gap = {prov: float(cc['C(category)[T.C]'] + (cc.get(f'C(category)[T.C]:C(provider)[T.{prov}]', 0.0))) for prov in ['Jio', 'Airtel', 'Vi', 'BSNL']}
summary['rq2_adjusted_C_gap_by_provider'] = gap
cell = df.groupby(['category', 'provider']).agg(n=('speed_mbps', 'size'), median_mbps=('speed_mbps', 'median'), mean_log=('log_speed', 'mean')).reset_index()
cell.to_csv(os.path.join(OUT, 'rq2_cells_sample.csv'), index=False)
# ---------------- RQ4
train = df[df.year <= 2022].copy(); test = df[df.year >= 2023].copy()
thr = train.speed_mbps.quantile(0.20); summary['rq4_threshold_mbps'] = float(thr)
for d in (train, test): d['poor'] = (d.speed_mbps < thr).astype(int)
feats_cat = ['provider', 'category', 'circle']; feats_num = ['signal_dbm', 'log_active', 'month']
def prep(d):
    X = d[feats_cat + feats_num].copy(); X['signal_dbm'] = X.signal_dbm.fillna(train.signal_dbm.median()); X['signal_missing'] = d.signal_dbm.isna().astype(int)
    X['log_active'] = X.log_active.fillna(train.log_active.median()); return X
Xtr, Xte, ytr, yte = prep(train), prep(test), train.poor.values, test.poor.values
num = feats_num + ['signal_missing']
ct = ColumnTransformer([('cat', OneHotEncoder(handle_unknown='ignore'), feats_cat), ('num', StandardScaler(), num)])
models = {
 'Logistic regression (baseline)': Pipeline([('ct', ct), ('m', LogisticRegression(max_iter=2000, class_weight='balanced'))]),
 'Random forest': Pipeline([('ct', ct), ('m', RandomForestClassifier(n_estimators=300, min_samples_leaf=50, class_weight='balanced', n_jobs=-1, random_state=42))]),
 'LightGBM': Pipeline([('ct', ct), ('m', lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, class_weight='balanced', random_state=42, verbose=-1))]),
}
perf, fair = [], []
def group_metrics(d, yhat, prob, model, split):
    out = []
    for gcol in ['category', 'provider']:
        for g, idx in d.groupby(gcol).indices.items():
            y = d.poor.values[idx]; h = yhat[idx]
            tn, fp, fn, tp = confusion_matrix(y, h, labels=[0, 1]).ravel()
            out.append(dict(model=model, split=split, group_var=gcol, group=g, n=int(len(idx)), positives=int(y.sum()), recall=tp / max(tp + fn, 1), fnr=fn / max(tp + fn, 1),
                            fpr=fp / max(fp + tn, 1), selection_rate=h.mean(), auc=roc_auc_score(y, prob[idx]) if 0 < y.mean() < 1 else np.nan))
    return out
for name, pipe in models.items():
    pipe.fit(Xtr, ytr)
    for split, X, y, d in [('validation 2018-2022 (train)', Xtr, ytr, train), ('hold-out 2023-2024', Xte, yte, test)]:
        prob = pipe.predict_proba(X)[:, 1]; yhat = (prob >= 0.5).astype(int)
        perf.append(dict(model=name, split=split, n=int(len(y)), positive_rate=float(y.mean()), accuracy=accuracy_score(y, yhat), precision=precision_score(y, yhat),
                         recall=recall_score(y, yhat), f1=f1_score(y, yhat), auc=roc_auc_score(y, prob)))
        fair += group_metrics(d, yhat, prob, name, split)
perf = pd.DataFrame(perf); perf.to_csv(os.path.join(OUT, 'rq4_model_performance.csv'), index=False)
fair = pd.DataFrame(fair); fair.to_csv(os.path.join(OUT, 'rq4_group_metrics.csv'), index=False)
# fairness summary: equal-opportunity difference (max recall gap) and four-fifths ratio per model/split/group_var
fs = []
for (m, s, gv), g in fair.groupby(['model', 'split', 'group_var']):
    fs.append(dict(model=m, split=s, group_var=gv, max_fnr=g.fnr.max(), min_fnr=g.fnr.min(), equal_opportunity_diff=g.recall.max() - g.recall.min(),
                   equalized_odds_diff=max(g.recall.max() - g.recall.min(), g.fpr.max() - g.fpr.min()), four_fifths_ratio=g.selection_rate.min() / g.selection_rate.max(),
                   worst_group=g.loc[g.fnr.idxmax(), 'group'], best_group=g.loc[g.fnr.idxmin(), 'group']))
pd.DataFrame(fs).to_csv(os.path.join(OUT, 'rq4_fairness_summary.csv'), index=False)
# feature importance from LightGBM
lg = models['LightGBM']; names = lg.named_steps['ct'].get_feature_names_out(); imp = pd.Series(lg.named_steps['m'].feature_importances_, index=names).sort_values(ascending=False)
imp.head(20).to_csv(os.path.join(OUT, 'rq4_lightgbm_importance.csv'))
json.dump(summary, open(os.path.join(OUT, 'model_summary.json'), 'w'), indent=1, default=float)
print(json.dumps(summary, indent=1, default=float)); print(perf.round(3).to_string()); print(pd.DataFrame(fs).round(3).to_string())

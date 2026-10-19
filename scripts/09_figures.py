"""Figures for the interim report. Usage: python3 scripts/09_figures.py <eda_dir> <tables_dir> <fig_dir>"""
import pandas as pd, numpy as np, sys, os, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
EDA, TAB, FIG = sys.argv[1:4]; os.makedirs(FIG, exist_ok=True)
PROV = ['Jio', 'Airtel', 'Vi', 'BSNL']; PC = {'Jio': '#2B6CB0', 'Airtel': '#E05A3A', 'Vi': '#2E9E6B', 'BSNL': '#D9A400'}
CATS = ['Metro', 'A', 'B', 'C']; CC = {'Metro': '#1F3A5F', 'A': '#3F7CAC', 'B': '#7FB2D9', 'C': '#C8102E'}
plt.rcParams.update({'font.family': 'serif', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': .25, 'grid.linewidth': .5, 'axes.axisbelow': True})
def save(fig, name): fig.tight_layout(); fig.savefig(os.path.join(FIG, name), dpi=200, facecolor='white'); plt.close(fig)

# F1 tests per year by provider (millions)
t = pd.read_csv(os.path.join(EDA, 'tests_by_year_provider.csv')); p = t.pivot(index='year', columns='provider', values='n').reindex(columns=PROV) / 1e6
fig, ax = plt.subplots(figsize=(7.2, 3.4)); x = np.arange(len(p)); w = .2
for i, pr in enumerate(PROV): ax.bar(x + (i - 1.5) * w, p[pr], w, color=PC[pr], label=pr, linewidth=0)
ax.set_xticks(x); ax.set_xticklabels([str(y) + ('*' if y == 2018 else '') for y in p.index]); ax.set_ylabel('Tests (millions)'); ax.legend(ncol=4, frameon=False, loc='upper right')
ax.text(0, -0.17, '* 2018 covers April to December only', transform=ax.transAxes, fontsize=8, color='#555'); save(fig, 'f01_tests_year_provider.png')

# F2 missing rates by year
m = pd.read_csv(os.path.join(EDA, 'missing_by_year.csv'))
fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.plot(m.year, m.circle_missing_rate * 100, marker='o', color='#C8102E', lw=2, label='Circle missing'); ax.plot(m.year, m.signal_missing_rate * 100, marker='s', color='#3F7CAC', lw=2, label='Signal missing')
for _, r in m.iterrows(): ax.annotate(f"{r.circle_missing_rate*100:.0f}%", (r.year, r.circle_missing_rate * 100), textcoords='offset points', xytext=(0, 6), ha='center', fontsize=8, color='#C8102E')
ax.set_ylabel('Share of tests (%)'); ax.set_ylim(0, 80); ax.legend(frameon=False); save(fig, 'f02_missing_by_year.png')

# F3 median 4G download speed by category and year
s = pd.read_csv(os.path.join(EDA, 'speed_by_category_year.csv')); pv = s.pivot(index='year', columns='category', values='median_mbps')[CATS]
fig, ax = plt.subplots(figsize=(7.2, 3.4))
for c in CATS: ax.plot(pv.index, pv[c], marker='o', color=CC[c], lw=2, label=c); ax.annotate(f"{c} {pv[c].iloc[-1]:.0f}", (pv.index[-1], pv[c].iloc[-1]), textcoords='offset points', xytext=(6, 0), va='center', fontsize=8, color=CC[c])
ax.set_ylabel('Median 4G download speed (Mbps)'); ax.set_xlim(2017.8, 2024.9); ax.legend(frameon=False, ncol=4, loc='upper left', title='Circle category'); save(fig, 'f03_median_speed_category_year.png')

# F4 speed vs signal bin (4G download)
b = pd.read_csv(os.path.join(EDA, 'speed_by_signal_bin.csv')); b = b[(b.technology == '4G') & (b.test_type == 'download')]
fig, ax = plt.subplots(figsize=(7.2, 3.0)); lab = [f"{int(v)} to {int(v)+9}" for v in b.signal_bin]
ax.bar(range(len(b)), b.median_mbps, color='#3F7CAC', width=.6, linewidth=0)
for i, (v, n) in enumerate(zip(b.median_mbps, b.n)): ax.text(i, v + 1, f"{v:.0f}", ha='center', fontsize=8)
ax.set_xticks(range(len(b))); ax.set_xticklabels(lab, fontsize=8); ax.set_xlabel('Signal strength bin (dBm)'); ax.set_ylabel('Median download speed (Mbps)'); save(fig, 'f04_speed_vs_signal.png')

# F5 representation ratio by category and provider
r = pd.read_csv(os.path.join(TAB, 'rq3_representation_by_category.csv')); pv = r.pivot(index='category', columns='provider', values='representation_ratio').reindex(CATS)[PROV]
fig, ax = plt.subplots(figsize=(7.2, 3.4)); x = np.arange(len(CATS)); w = .2
for i, pr in enumerate(PROV):
    ax.bar(x + (i - 1.5) * w, pv[pr], w, color=PC[pr], label=pr, linewidth=0)
    for xi, v in zip(x + (i - 1.5) * w, pv[pr]): ax.text(xi, v + .03, f"{v:.2f}", ha='center', fontsize=7)
ax.axhline(1, color='#333', lw=1, ls='--'); ax.text(3.45, 1.03, 'parity = 1.0', fontsize=8, ha='right')
ax.set_xticks(x); ax.set_xticklabels(CATS); ax.set_xlabel('Circle category'); ax.set_ylabel('Test share ÷ subscriber share'); ax.legend(ncol=4, frameon=False, loc='upper left'); ax.set_ylim(0, 2.2); save(fig, 'f05_representation_ratio.png')

# F6 tests per 1,000 active subscribers per year by category
c = pd.read_csv(os.path.join(TAB, 'rq5_tests_per_1000_active_by_category.csv')).set_index('category').reindex(CATS)
fig, ax = plt.subplots(figsize=(5.0, 3.0)); ax.bar(CATS, c.tests_per_1000_active_per_year, color=[CC[k] for k in CATS], width=.6, linewidth=0)
for i, v in enumerate(c.tests_per_1000_active_per_year): ax.text(i, v + .15, f"{v:.1f}", ha='center', fontsize=9)
ax.set_ylabel('Tests per 1,000 active subs per year'); ax.set_xlabel('Circle category'); save(fig, 'f06_tests_per_1000_active.png')

# F7 RQ4 false-negative rate by group on the hold-out, three models
g = pd.read_csv(os.path.join(TAB, 'rq4_group_metrics.csv')); g = g[g.split == 'hold-out 2023-2024']
models = ['Logistic regression (baseline)', 'Random forest', 'LightGBM']; MC = {'Logistic regression (baseline)': '#7FB2D9', 'Random forest': '#3F7CAC', 'LightGBM': '#1F3A5F'}
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
for ax, gv, order in zip(axes, ['category', 'provider'], [CATS, PROV]):
    sub = g[g.group_var == gv]; x = np.arange(len(order)); w = .25
    for i, mname in enumerate(models):
        v = sub[sub.model == mname].set_index('group').reindex(order).fnr
        ax.bar(x + (i - 1) * w, v, w, color=MC[mname], label=mname.replace(' (baseline)', ''), linewidth=0)
    ax.set_xticks(x); ax.set_xticklabels(order); ax.set_xlabel('Circle category' if gv == 'category' else 'Provider')
axes[0].set_ylabel('False-negative rate, hold-out'); axes[0].legend(frameon=False, fontsize=8); save(fig, 'f07_rq4_fnr_groups.png')

# F8 distribution of 4G download speed (histogram, 5 Mbps bins)
h = pd.read_csv(os.path.join(EDA, 'speed_hist_4g_download.csv')); h['share'] = h.n / h.n.sum() * 100
fig, ax = plt.subplots(figsize=(7.2, 2.8)); ax.bar(h.mbps_bin + 2.5, h.share, width=4.6, color='#3F7CAC', linewidth=0)
ax.set_xlabel('4G download speed (Mbps, 5 Mbps bins; last bin is 150 Mbps and above)'); ax.set_ylabel('Share of tests (%)')
ax.text(60, h.share.max() * .8, f"{h.share.iloc[0]:.0f}% of tests are below 5 Mbps", fontsize=9); save(fig, 'f08_speed_histogram.png')
print('figures written')

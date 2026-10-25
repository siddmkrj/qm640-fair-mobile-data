"""Two-panel figures for the interim report (compact layout). Usage: python3 scripts/10_paired_figures.py <eda_dir> <tables_dir> <fig_dir>"""
import pandas as pd, numpy as np, sys, os, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
EDA, TAB, FIG = sys.argv[1:4]
PROV = ['Jio', 'Airtel', 'Vi', 'BSNL']; PC = {'Jio': '#2B6CB0', 'Airtel': '#E05A3A', 'Vi': '#2E9E6B', 'BSNL': '#D9A400'}
CATS = ['Metro', 'A', 'B', 'C']; CC = {'Metro': '#1F3A5F', 'A': '#3F7CAC', 'B': '#7FB2D9', 'C': '#C8102E'}
plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 8.5, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': .25, 'grid.linewidth': .5, 'axes.axisbelow': True, 'legend.fontsize': 7.5})
def pair(name): fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.3)); return fig, ax
def save(fig, name): fig.tight_layout(w_pad=2.0); fig.savefig(os.path.join(FIG, name), dpi=220, facecolor='white'); plt.close(fig)
def label(ax, s): ax.set_title(s, loc='left', fontsize=9, fontweight='bold', pad=6)

# P1: tests by year x provider | missing rates
fig, (a, b) = pair('p1')
t = pd.read_csv(os.path.join(EDA, 'tests_by_year_provider.csv')); p = t.pivot(index='year', columns='provider', values='n').reindex(columns=PROV) / 1e6
x = np.arange(len(p)); w = .2
for i, pr in enumerate(PROV): a.bar(x + (i - 1.5) * w, p[pr], w, color=PC[pr], label=pr, linewidth=0)
a.set_xticks(x); a.set_xticklabels([str(y)[2:] + ('*' if y == 2018 else '') for y in p.index]); a.set_ylabel('Tests (millions)'); a.legend(ncol=2, frameon=False); label(a, '(a) Tests per year by provider')
m = pd.read_csv(os.path.join(EDA, 'missing_by_year.csv'))
b.plot(m.year, m.circle_missing_rate * 100, marker='o', color='#C8102E', lw=1.8, label='Circle missing'); b.plot(m.year, m.signal_missing_rate * 100, marker='s', color='#3F7CAC', lw=1.8, label='Signal missing')
for _, r in m.iterrows(): b.annotate(f"{r.circle_missing_rate*100:.0f}", (r.year, r.circle_missing_rate * 100), textcoords='offset points', xytext=(0, 5), ha='center', fontsize=7, color='#C8102E')
b.set_ylabel('Share of tests (%)'); b.set_ylim(0, 80); b.legend(frameon=False); label(b, '(b) Missing circle and signal by year'); b.set_xticks(m.year); b.set_xticklabels([str(y)[2:] for y in m.year])
save(fig, 'p1_volume_missing.png')

# P2: histogram | median speed by category-year
fig, (a, b) = pair('p2')
h = pd.read_csv(os.path.join(EDA, 'speed_hist_4g_download.csv')); h['share'] = h.n / h.n.sum() * 100
a.bar(h.mbps_bin + 2.5, h.share, width=4.6, color='#3F7CAC', linewidth=0); a.set_xlabel('4G download speed (Mbps, 5 Mbps bins)'); a.set_ylabel('Share of tests (%)')
a.text(55, h.share.max() * .75, f"{h.share.iloc[0]:.0f}% below 5 Mbps", fontsize=8); label(a, '(a) Distribution of 4G download speed')
s = pd.read_csv(os.path.join(EDA, 'speed_by_category_year.csv')); pv = s.pivot(index='year', columns='category', values='median_mbps')[CATS]
for c in CATS: b.plot(pv.index, pv[c], marker='o', ms=3.5, color=CC[c], lw=1.8, label=c)
b.set_ylabel('Median speed (Mbps)'); b.legend(frameon=False, ncol=4, loc='upper left', title='Circle category', title_fontsize=7.5); b.set_xticks(pv.index); b.set_xticklabels([str(y)[2:] for y in pv.index]); label(b, '(b) Median speed by circle category')
save(fig, 'p2_distribution_trend.png')

# P3: speed vs signal | representation ratio
fig, (a, b) = pair('p3')
sb = pd.read_csv(os.path.join(EDA, 'speed_by_signal_bin.csv')); sb = sb[(sb.technology == '4G') & (sb.test_type == 'download')]
a.bar(range(len(sb)), sb.median_mbps, color='#3F7CAC', width=.65, linewidth=0)
for i, v in enumerate(sb.median_mbps): a.text(i, v + 1, f"{v:.0f}", ha='center', fontsize=7)
a.set_xticks(range(len(sb))); a.set_xticklabels([f"{int(v)}" for v in sb.signal_bin], fontsize=7.5); a.set_xlabel('Signal strength bin, lower edge (dBm)'); a.set_ylabel('Median speed (Mbps)'); label(a, '(a) Speed by signal strength')
r = pd.read_csv(os.path.join(TAB, 'rq3_representation_by_category.csv')); pv = r.pivot(index='category', columns='provider', values='representation_ratio').reindex(CATS)[PROV]
x = np.arange(len(CATS)); w = .2
for i, pr in enumerate(PROV): b.bar(x + (i - 1.5) * w, pv[pr], w, color=PC[pr], label=pr, linewidth=0)
b.axhline(1, color='#333', lw=.9, ls='--'); b.set_xticks(x); b.set_xticklabels(CATS); b.set_xlabel('Circle category'); b.set_ylabel('Test share ÷ subscriber share'); b.legend(ncol=2, frameon=False); b.set_ylim(0, 2.2); label(b, '(b) Representation ratio (1 = parity)')
save(fig, 'p3_signal_representation.png')

# P4: tests per 1000 active | FNR by group (LightGBM and baseline)
fig, (a, b) = pair('p4')
c = pd.read_csv(os.path.join(TAB, 'rq5_tests_per_1000_active_by_category.csv')).set_index('category').reindex(CATS)
a.bar(CATS, c.tests_per_1000_active_per_year, color=[CC[k] for k in CATS], width=.6, linewidth=0)
for i, v in enumerate(c.tests_per_1000_active_per_year): a.text(i, v + .15, f"{v:.1f}", ha='center', fontsize=8)
a.set_ylabel('Tests per 1,000 active subs per year'); a.set_xlabel('Circle category'); label(a, '(a) Coverage by circle category')
g = pd.read_csv(os.path.join(TAB, 'rq4_group_metrics.csv')); g = g[g.split == 'hold-out 2023-2024']
models = ['Logistic regression (baseline)', 'LightGBM']; MC = {'Logistic regression (baseline)': '#7FB2D9', 'LightGBM': '#1F3A5F'}
order = CATS + PROV; x = np.arange(len(order)); w = .36
for i, mname in enumerate(models):
    v = pd.concat([g[(g.model == mname) & (g.group_var == 'category')].set_index('group').reindex(CATS).fnr, g[(g.model == mname) & (g.group_var == 'provider')].set_index('group').reindex(PROV).fnr])
    b.bar(x + (i - 0.5) * w, v.values, w, color=MC[mname], label=mname.replace(' (baseline)', ''), linewidth=0)
b.set_xticks(x); b.set_xticklabels(order, fontsize=7.5); b.axvline(3.5, color='#999', lw=.8); b.set_ylabel('False-negative rate'); b.legend(frameon=False, ncol=1, loc='upper left', fontsize=7); b.set_ylim(0, 1.05); label(b, '(b) Classifier FNR by group (hold-out)')
save(fig, 'p4_coverage_fnr.png')
print('ok')

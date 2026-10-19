"""Parse TRAI press-release Annexure II (wireless subscribers by circle x operator) and Annexure III (VLR %)
from the text layout produced by pdftotext -layout.
Usage: python3 parse_trai.py <pdf> ... -> CSV: month, circle, operator, subscribers, vlr_pct, raw_cols"""
import re, sys, os, collections, subprocess

NUM = re.compile(r'^-?\d[\d,]*(\.\d+)?$')
MON = re.compile(r'^[A-Z] ?[a-z]{2}-\d{2}$')
CIRCLES = ['Andhra Pradesh','Assam','Bihar','Delhi','Gujarat','Haryana','Himachal Pradesh','Jammu & Kashmir','Karnataka','Kerala','Kolkata',
           'Madhya Pradesh','Maharashtra','Mumbai','North East','Orissa','Punjab','Rajasthan','Tamil Nadu','UP East','UP West','West Bengal']
def norm_circle(s):
    s = re.sub(r'\s+', '', s).lower().replace('.', '')
    m = {'andhrapradesh':'Andhra Pradesh','assam':'Assam','bihar':'Bihar','delhi':'Delhi','gujarat':'Gujarat','haryana':'Haryana',
         'himachalpradesh':'Himachal Pradesh','j&k':'Jammu & Kashmir','jammu&kashmir':'Jammu & Kashmir','karnataka':'Karnataka','kerala':'Kerala',
         'kolkata':'Kolkata','madhyapradesh':'Madhya Pradesh','maharashtra':'Maharashtra','mumbai':'Mumbai','northeast':'North East',
         'odisha':'Orissa','orissa':'Orissa','punjab':'Punjab','rajasthan':'Rajasthan','tamilnadu':'Tamil Nadu','up(e)':'UP East','up(w)':'UP West',
         'upeast':'UP East','upwest':'UP West','westbengal':'West Bengal'}
    return m.get(s)

def pages_text(pdf):
    n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
    return [subprocess.run(['pdftotext', '-f', str(i), '-l', str(i), '-layout', pdf, '-'], capture_output=True, text=True).stdout for i in range(1, n+1)]

def tokens(line):
    """(start_col, end_col, text). Words separated by one space are merged only when neither is a number."""
    out = []
    for m in re.finditer(r'\S+', line):
        s, e, t = m.start(), m.end(), m.group()
        if t[0].isdigit(): t = t.rstrip(']})!|')
        if out and s - out[-1][1] == 1 and not NUM.match(t) and not NUM.match(out[-1][2]) and not MON.match(t) and not MON.match(out[-1][2]):
            out[-1] = (out[-1][0], e, out[-1][2] + ' ' + t)
        else: out.append((s, e, t))
    return out

def parse_annex2(text):
    lines = text.split('\n')
    li = next((i for i, l in enumerate(lines) if len([t for t in tokens(l) if MON.match(t[2])]) >= 6), None)
    if li is None: return {}, None
    labels = [t for t in tokens(lines[li]) if MON.match(t[2])]
    # operator header: the non-empty lines above the label line (up to 3), excluding 'Circle' and title words
    hdr = []
    for l in lines[max(0, li-8):li]:
        for s, e, t in tokens(l):
            if t in ('Circle', 'Service Area', 'Net Addition', 'Net', 'Addition', 'Group', '.') or 'Annexure' in t or 'Subscriber Base' in t: continue
            if MON.match(t): continue
            hdr.append((s, e, t))
    def op_of(x):
        best = None
        for s, e, t in hdr:
            d = 0 if s - 6 <= x <= e + 6 else min(abs(s - x), abs(e - x))
            if best is None or d < best[0]: best = (d, t)
        return best[1] if best else None
    labs = [dict(x=(s+e)/2, text=t, op=op_of((s+e)/2)) for s, e, t in labels]
    cur = []; i = 0
    while i < len(labs):
        if i+1 < len(labs) and labs[i]['op'] == labs[i+1]['op']: cur.append(labs[i+1]); i += 2
        else: cur.append(labs[i]); i += 1
    report_month = collections.Counter(c['text'] for c in cur).most_common(1)[0][0]
    data = {}
    for l in lines[li+1:]:
        toks = tokens(l)
        if not toks: continue
        name = None; nums = []
        for s, e, t in toks:
            if name is None:
                if norm_circle(t): name = norm_circle(t)
                elif NUM.match(t): break
            elif NUM.match(t): nums.append((s, e, t))
        if not name or name in data: continue
        row = collections.defaultdict(float)
        for s, e, t in nums:
            x = (s + e) / 2
            best = min(cur, key=lambda c: abs(c['x'] - x))
            if abs(best['x'] - x) <= 9: row[best['op']] += float(t.replace(',', ''))
        data[name] = dict(row)
    return data, report_month

def parse_annex3(text):
    lines = text.split('\n')
    hi = next((i for i, l in enumerate(lines) if l.strip().startswith('Circle') and ('Bharti' in l or 'BSNL' in l)), None)
    if hi is None: return {}
    hdr = [t for t in tokens(lines[hi]) if t[2] != 'Circle']
    out = {}
    for l in lines[hi+1:]:
        toks = tokens(l)
        if not toks: continue
        name = norm_circle(toks[0][2])
        if not name or name in out: continue
        row = {}
        for s, e, t in toks[1:]:
            if t == '-': continue
            if not NUM.match(t): continue
            x = (s + e) / 2
            g = min(hdr, key=lambda h: abs((h[0]+h[1])/2 - x))
            row[g[2]] = float(t)
        out[name] = row
    return out

OPMAP = [('bharti','Airtel'),('airtel','Airtel'),('vodafone idea','Vi'),('vodafone','Vi'),('idea','Vi'),('bsnl','BSNL'),('jio','Jio')]
def map_op(name):
    n = name.lower()
    if 'vno' in n: return None
    for k, v in OPMAP:
        if k in n: return v
    return None

if __name__ == '__main__':
    print('month,circle,operator,subscribers,vlr_pct,raw_cols')
    for f in sys.argv[1:]:
        month = re.search(r'(\d{4}-\d{2})', os.path.basename(f)).group(1)
        pages = pages_text(f)
        subs = {}; rm = None
        for p in pages:
            if not ('Wireless Subscriber' in p.replace('\n', ' ') or 'Annexure' in p): continue
            if 'Proportion of VLR' in p or 'Wireline' in p.replace(' ', '') or 'Broadband' in p.replace(' ', ''): continue
            d, m = parse_annex2(p)
            if not d: continue
            rm = rm or m
            for c, row in d.items():
                subs.setdefault(c, {}).update(row)
        p3 = next((p for p in pages if 'Proportion of VLR' in p and 'Circle' in p), None)
        vlr = parse_annex3(p3) if p3 else {}
        n = 0
        for c in CIRCLES:
            agg = collections.defaultdict(float); raw = collections.defaultdict(list); vl = collections.defaultdict(list)
            for op, v in subs.get(c, {}).items():
                m = map_op(op)
                if m: agg[m] += v; raw[m].append(op)
            for op, v in vlr.get(c, {}).items():
                m = map_op(op)
                if m: vl[m].append((v, agg.get(m, 1)))
            for m in ('Jio', 'Airtel', 'Vi', 'BSNL'):
                if m in agg:
                    vv = f"{sum(v for v, _ in vl[m]) / len(vl[m]):.2f}" if vl[m] else ''
                    print(f"{month},{c},{m},{int(agg[m])},{vv},{'|'.join(raw[m])}"); n += 1
        sys.stderr.write(f"{os.path.basename(f)}: report month {rm}, circles {len(subs)}, vlr circles {len(vlr)}, rows {n}\n")

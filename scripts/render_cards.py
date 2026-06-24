import json, html, math, os, statistics as _st
from collections import Counter as _Ctr

# ============================================================================
# render_cards.py — text-rich "AI proficiency card" renderer.
# Reads one or more workflow outputs (synthesized cards + raw per-task scores)
# plus the compact-stage nq_stats.json, and emits a self-contained HTML card
# per person: gate x equal-weight ability score, a 5-axis radar, signatures,
# top-3 actions, a count x difficulty x outcome table, and a leverage axis.
#
# Everything that used to be hardcoded now comes from config.json at the repo
# root. To run for your own people, point `workflow_outputs` at your exported
# workflow .output files; the rest is computed automatically.
# ============================================================================

# --- load config.json from the repo root (one level up from scripts/) --------
_CFG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
config = json.load(open(_CFG_PATH, encoding='utf-8'))
COMPACT_DIR = config.get('compact_dir', '/tmp/aiprof_compact')
OUT_DIR = config.get('out_dir', './cards')
_OUTS = config.get('workflow_outputs', [])   # add each person's .output here
PEOPLE = config.get('people', {})            # { person_id: {name, role} }

# --- merge all workflow outputs (later file wins on duplicate person) --------
cards = {}; _MERGED_RAW = []
for _f in _OUTS:
    _o = json.load(open(_f))
    for _c in _o['result']['cards']:
        cards[_c['person']] = _c            # same person id: later overrides (dedup)
    _MERGED_RAW += _o['result'].get('raw_tasks', [])

# Person display comes from config.people; fall back to the person id as name.
def NAME(p): return (PEOPLE.get(p) or {}).get('name', p)
def ROLE(p): return (PEOPLE.get(p) or {}).get('role', '')
def INIT(p):
    # Two-character avatar initials derived from the display name.
    n = NAME(p) or p
    return (n[:2]).upper()

# === gate x equal-weight 4-block scoring (computed from raw_tasks) ===========
# Gate = verification behavior = ground-truth closure + reflexivity (the two
# "do you actually check your own work" behaviors, equal-weight mean).
# Gate coefficient = gate / 4 (linear over the full range). We anchor on
# human-controllable rigor behavior rather than on landed outcome (rv), because
# soft domains (e.g. human sign-off) let sloppy work "land" and inflate scores.
_RAW = _MERGED_RAW
def _dm(ts, k):
    vs = [t['dims'][k] for t in ts if k in t.get('dims', {})]; return _st.mean(vs) if vs else None
def _blk(ts, keys):
    vs = [t['dims'][k] for t in ts for k in keys if k in t.get('dims', {})]; return _st.mean(vs) if vs else None
def _gatecoef(g):
    if g is None: return 1.0
    return max(0.0, min(1.0, g / 4.0))
_CTX = ['ctx_suff', 'ctx_time', 'ctx_src', 'ctx_scaf', 'ctx_noise']; _GOAL = ['goal_mot', 'goal_scope', 'goal_stab', 'goal_acc']; _FB = ['fb_detect', 'fb_loc', 'fb_hole']; _EFF = ['eff_decl', 'eff_sel']
GATE = {}
for _p in cards:
    _ts = [t for t in _RAW if t.get('person') == _p and t.get('cls') == 'real_task']
    _ver = _dm(_ts, 'fb_verify'); _refl = _dm(_ts, 'fb_reflex'); _gs = [x for x in [_ver, _refl] if x is not None]; _g = _st.mean(_gs) if _gs else None
    _gc = _gatecoef(_g); _a4 = _st.mean([x for x in [_blk(_ts, _CTX), _blk(_ts, _GOAL), _blk(_ts, _EFF), _blk(_ts, _FB)] if x is not None] or [0])
    GATE[_p] = {'coef': round(_gc, 2), 'ability4': round(_a4, 2), 'final': round(_gc * _a4, 2), 'gate': round(_g, 2) if _g is not None else None, 'ver': _ver, 'refl': _refl}

# === count x difficulty x outcome ============================================
# Manual override dicts (authoritative full-workflow counts / throughput windows).
# Left empty: everything below is auto-computed from nq_stats.json. Add entries
# here only if you have a more accurate full-corpus breakdown for a person.
_NQfull = {}   # person -> (chitchat, simple, complex, total)
_TM = {}       # person -> throughput / active-window description string
# Auto-read the count/difficulty/throughput stats the compact stage computed
# (nq_stats.json). The manual dicts above only act as an authoritative override:
# people present there keep their hand values; everyone else is filled from the
# session-level stats — so adding a new person needs no code change.
try:
    _NQ = json.load(open(os.path.join(COMPACT_DIR, 'nq_stats.json')))
    for _p, _r in _NQ.items():
        _NQfull.setdefault(_p, (_r['chat'], _r['simple'], _r['complex'], _r['chat'] + _r['simple'] + _r['complex']))
        if _p not in _TM:
            if _r.get('per_week'):
                _TM[_p] = '%s → %s · %d active days · ≈ %s / week (auto · session-level)' % (_r['date_min'], _r['date_max'], _r['active_days'], _r['per_week'])
            else:
                _TM[_p] = 'session-level window missing timestamps → rate TBD (auto)'
except Exception: pass

def _ctier(tid):
    # Classify a single task as simple/complex from its compact transcript size.
    f = os.path.join(COMPACT_DIR, 't', '%s.txt' % tid)
    if not os.path.exists(f): return None
    t = open(f, errors='ignore').read(); hum = t.count('[USER]'); sp = t.count('[AI]'); kb = len(t) / 1024; tl = t.count('⟨tools:')
    if hum < 1: return None
    return 'complex' if (kb >= 12 or sp >= 22 or hum >= 6 or tl >= 15) else 'simple'
XT = {}
for _p in cards:
    _ts = [t for t in _RAW if t.get('person') == _p and t.get('cls') == 'real_task']
    _g = {'simple': {'yes': 0, 'no': 0, 'na': 0}, 'complex': {'yes': 0, 'no': 0, 'na': 0}}; _hav = 0
    for t in _ts:
        tid = t.get('task_id'); tt = _ctier(tid) if tid else None
        rvk = 'yes' if t['rv'] == 'yes' else ('no' if t['rv'] == 'no' else 'na')
        if tt: _g[tt][rvk] += 1; _hav += 1
    _mar = _Ctr('yes' if t['rv'] == 'yes' else 'no' if t['rv'] == 'no' else 'na' for t in _ts)
    XT[_p] = {'g': _g, 'hav': _hav, 'n': len(_ts), 'mar': dict(_mar)}

def nqsec(p):
    x = XT.get(p, {}); full = _NQfull.get(p)
    diff = ('full corpus ' + str(full[3]) + ' real tasks · chitchat ' + str(full[0]) + ' · simple ' + str(full[1]) + ' · complex ' + str(full[2])) if full else (str(x.get('n', 0)) + ' evaluated tasks (no clean full baseline)')
    o = '<div style="margin-top:12px;border-top:0.5px solid var(--color-border-tertiary);padding-top:9px">'
    o += '<div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:5px">count × difficulty × outcome · throughput</div>'
    if _TM.get(p): o += '<div style="font-size:12px;color:var(--color-text-tertiary);margin-bottom:5px"><span style="color:var(--color-text-secondary)">⏱ throughput · </span>' + _TM[p] + '</div>'
    o += '<div style="font-size:12.5px;color:var(--color-text-secondary);margin-bottom:6px">' + diff + '</div>'
    if x.get('hav', 0) > 0:
        o += '<table style="width:100%;font-size:12.5px;border-collapse:collapse"><tr style="color:var(--color-text-tertiary)"><td style="padding:2px 6px"></td><td style="text-align:center">accepted</td><td style="text-align:center">abandoned</td><td style="text-align:center">unmeasurable</td></tr>'
        for tt in ['simple', 'complex']:
            gg = x['g'][tt]
            o += '<tr><td style="padding:2px 6px;font-weight:500">' + tt + '</td><td style="text-align:center;color:var(--color-text-success)">' + str(gg['yes']) + '</td><td style="text-align:center;color:var(--color-text-danger)">' + str(gg['no']) + '</td><td style="text-align:center;color:var(--color-text-tertiary)">' + str(gg['na']) + '</td></tr>'
        o += '</table><div style="font-size:11px;color:var(--color-text-tertiary);margin-top:3px">outcome from a sample of ' + str(x['hav']) + '; chitchat has no outcome</div>'
    else:
        m = x.get('mar', {})
        o += '<div style="font-size:12.5px">outcome (sample ' + str(x.get('n', 0)) + '): accepted ' + str(m.get('yes', 0)) + ' · abandoned ' + str(m.get('no', 0)) + ' · unmeasurable ' + str(m.get('na', 0)) + '</div><div style="font-size:11px;color:var(--color-text-tertiary);margin-top:2px">no landed sign-off in this domain → mostly unmeasurable; difficulty not split</div>'
    o += '</div>'
    return o
def e(s): return html.escape(str(s or ''))
def chip(s): return 'scg' if s >= 3 else ('sca' if s >= 2 else 'scr')
def barc(s): return '#639922' if s >= 3 else ('#BA7517' if s >= 2 else '#E24B4A')

ORDER = ['Feedback', 'Practice', 'Effort & selection', 'Goal', 'Context']
ANG = [-90, -18, 54, 126, 198]
def radar(ms):
    cx, cy, R = 150, 140, 95
    grid = ' '.join('%d,%d' % (cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))) for a in ANG)
    pts = []
    for m, a in zip(ORDER, ANG):
        r = (ms.get(m, 0) or 0) / 4 * R
        pts.append('%d,%d' % (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))))
    data = ' '.join(pts)
    lines = ''.join('<line x1="150" y1="140" x2="%d" y2="%d" style="stroke:var(--color-border-tertiary)"/>' % (cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))) for a in ANG)
    # Axis labels: (key, x, y, text-anchor). Keys match module_scores keys.
    lbl = [('Feedback', 'Feedback', 150, 34, 'middle'), ('Practice', 'Practice', 248, 108, 'start'), ('Effort', 'Effort & selection', 210, 236, 'middle'), ('Goal', 'Goal', 90, 236, 'middle'), ('Context', 'Context', 52, 108, 'end')]
    txt = ''.join('<text x="%d" y="%d" text-anchor="%s" style="fill:var(--color-text-secondary);font-size:11px">%s %s</text>' % (x, y, an, disp, ('%g' % (ms.get(key, 0) or 0))) for (disp, key, x, y, an) in lbl)
    return '<svg viewBox="0 0 300 250" width="270" role="img" aria-label="capability radar"><polygon points="%s" fill="none" style="stroke:var(--color-border-secondary)"/>%s<polygon points="%s" fill="rgba(55,138,221,0.18)" stroke="#378ADD" stroke-width="1.5"/>%s</svg>' % (grid, lines, data, txt)

def dim_html(d):
    s = d['score']
    h = '<div class="dim"><div class="dr"><span class="sc %s">%g</span><span class="dn">%s</span></div>' % (chip(s), s, e(d['name']))
    h += '<div class="why">%s</div>' % e(d['why_std'])
    if d.get('count_line'):
        h += '<div class="row"><span class="k">count</span><span class="v">%s</span></div>' % e(d['count_line'])
    if d.get('best'):
        q = '<details class="src"><summary>quote</summary><div class="q">%s</div></details>' % e(d['quote_best']) if d.get('quote_best') else ''
        h += '<div class="row hi"><span class="k">best</span><span class="v">%s%s</span></div>' % (e(d['best']), q)
    if d.get('worst'):
        q = '<details class="src"><summary>quote</summary><div class="q">%s</div></details>' % e(d['quote_worst']) if d.get('quote_worst') else ''
        h += '<div class="row lo"><span class="k">worst</span><span class="v">%s%s</span></div>' % (e(d['worst']), q)
    if d.get('pattern'):
        h += '<div class="row"><span class="k">pattern</span><span class="v">%s</span></div>' % e(d['pattern'])
    if d.get('crosslink'):
        h += '<div class="row"><span class="k">link</span><span class="v">%s</span></div>' % e(d['crosslink'])
    if d.get('so'):
        h += '<div class="row"><span class="k" style="color:var(--color-text-info)">so</span><span class="v">%s</span></div>' % e(d['so'])
    return h + '</div>'

STYLE = '''<style>
.dim{padding:11px 0;border-top:0.5px solid var(--color-border-tertiary)}.dim:first-of-type{border-top:none}
.dr{display:flex;align-items:center;gap:8px;font-size:15px;margin-bottom:5px}
.sc{min-width:30px;text-align:center;font-size:12px;font-weight:500;padding:1px 6px;border-radius:var(--border-radius-md);font-variant-numeric:tabular-nums}
.scg{background:var(--color-background-success);color:var(--color-text-success)}
.sca{background:var(--color-background-warning);color:var(--color-text-warning)}
.scr{background:var(--color-background-danger);color:var(--color-text-danger)}
.dn{font-weight:500}
.why{font-size:13px;line-height:1.6;color:var(--color-text-secondary);background:var(--color-background-secondary);border-radius:var(--border-radius-md);padding:7px 10px;margin-bottom:6px}
.row{font-size:13.5px;line-height:1.6;margin:5px 0;display:flex;gap:9px}
.row .k{flex:0 0 44px;color:var(--color-text-secondary);font-weight:500}.row .v{flex:1}
.row.hi .k{color:var(--color-text-success)}.row.lo .k{color:var(--color-text-warning)}
.src{margin-top:3px}.src summary{font-size:12px;color:var(--color-text-tertiary);cursor:pointer}
.src .q{font-size:12.5px;color:var(--color-text-secondary);font-style:italic;margin-top:3px;padding-left:8px;border-left:2px solid var(--color-border-secondary);line-height:1.5}
.mod{border:0.5px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);padding:11px 14px;margin-top:11px;background:var(--color-background-primary)}
.modh{display:flex;align-items:baseline;gap:9px;margin-bottom:3px;flex-wrap:wrap}
.sig{border-left:2px solid var(--color-border-info);border-radius:0;padding:2px 0 2px 11px;margin:7px 0}
.lev{display:flex;gap:9px;padding:7px 0;border-top:0.5px solid var(--color-border-tertiary);font-size:13px}.lev:first-of-type{border-top:none}
</style>'''

def card(p):
    c = cards[p]; cd = c['card']; ms = c['module_scores']
    gate = cd['gate']; gl = gate['level']
    gcls = 'success' if gl == 'strong' else ('warning' if gl == 'mid' else 'danger')
    h = '<h2 class="sr-only">%s AI proficiency card</h2>' % e(p) + STYLE + '<div style="font-family:var(--font-sans)">'
    # header
    h += '<div style="background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);padding:1.1rem 1.3rem">'
    h += '<div style="display:flex;align-items:center;gap:12px"><div style="width:44px;height:44px;border-radius:50%%;background:var(--color-background-info);color:var(--color-text-info);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:500">%s</div><div style="flex:1"><div style="font-size:17px;font-weight:500">%s</div><div style="font-size:13px;color:var(--color-text-secondary)">%s · per-task scored</div></div></div>' % (e(INIT(p)), e(NAME(p)), e(ROLE(p)))
    h += '<div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap">'
    h += '<div style="flex:1;min-width:110px;background:var(--color-background-secondary);border-radius:var(--border-radius-md);padding:9px 12px"><div style="font-size:12px;color:var(--color-text-secondary)">AI-native score · gate × ability</div><div style="font-size:22px;font-weight:500">%.2f<span style="font-size:12px;color:var(--color-text-secondary)"> /4</span></div><div style="font-size:11px;color:var(--color-text-tertiary);margin-top:2px">gate %.2f × ability %.2f · within-domain</div></div>' % (GATE[p]['final'], GATE[p]['coef'], GATE[p]['ability4'])
    h += '<div style="flex:1;min-width:110px;background:var(--color-background-secondary);border-radius:var(--border-radius-md);padding:9px 12px"><div style="font-size:12px;color:var(--color-text-secondary)">leverage · value realized</div><div style="font-size:14px;font-weight:500;margin-top:5px">four legs below · 3 awaiting data</div></div>'
    h += '<div style="flex:1;min-width:110px;background:var(--color-background-%s);border-radius:var(--border-radius-md);padding:9px 12px"><div style="font-size:12px;color:var(--color-text-%s)">reality gate · landing trust</div><div style="font-size:14px;font-weight:500;color:var(--color-text-%s);margin-top:5px">%s</div></div>' % (gcls, gcls, gcls, e(gl))
    h += '</div>'
    h += '<div style="margin-top:12px;font-size:14px;line-height:1.6"><span style="color:var(--color-text-secondary)">portrait · </span>%s</div>' % e(cd['portrait'])
    h += '<div style="margin-top:6px;font-size:13px;line-height:1.55;color:var(--color-text-secondary)">reality gate · %s</div>' % e(gate['line'])
    h += nqsec(p)
    # signatures
    h += '<div style="margin-top:12px;border-top:0.5px solid var(--color-border-tertiary);padding-top:9px"><div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:4px">your signature (cross-axis patterns)</div>'
    for s in cd['signatures']:
        h += '<div class="sig"><div style="font-size:13.5px;font-weight:500;color:var(--color-text-info)">%s</div><div style="font-size:13px;line-height:1.55">%s</div></div>' % (e(s['title']), e(s['line']))
    h += '</div>'
    # top3
    h += '<div style="margin-top:8px"><div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:4px">do these three first (highest leverage)</div>'
    for i, t in enumerate(cd['top3']):
        h += '<div style="font-size:13.5px;line-height:1.65"><span style="color:var(--color-text-warning);font-weight:500">%d.</span> %s</div>' % (i + 1, e(t))
    h += '</div></div>'
    # radar
    h += '<div style="display:flex;justify-content:center;margin-top:4px">%s</div>' % radar(ms)
    # modules
    for m in cd['modules']:
        mc = ms.get(m['module'], m['score'])
        h += '<div class="mod"><div class="modh"><span style="font-size:15px;font-weight:500">%s</span><span style="font-size:13px;color:var(--color-text-%s)">%g</span></div>' % (e(m['module']), 'success' if mc >= 3 else ('warning' if mc >= 2 else 'danger'), mc)
        for d in m['dims']:
            h += dim_html(d)
        h += '</div>'
    # leverage
    h += '<div class="mod" style="background:var(--color-background-secondary);border:none"><div class="modh"><span style="font-size:15px;font-weight:500">leverage axis (value realized)</span><span style="font-size:12px;color:var(--color-text-secondary)">not in ability score</span></div>'
    for L in cd['leverage']:
        _leg = L.get('leg', '').lower(); _lvl = L.get('level', '').lower()
        if 'pending' in _lvl or 'coverage' in _leg or 'speed' in _leg or 'impact' in _leg: continue
        line = L['line']
        h += '<div class="lev"><span class="sc %s" style="flex:0 0 auto">%s</span><span style="font-weight:500;flex:0 0 64px">%s</span><span style="flex:1;color:var(--color-text-secondary)">%s</span></div>' % (chip(3 if (('strong' in _lvl) or ('high' in _lvl)) else (1 if (('weak' in _lvl) or ('low' in _lvl)) else 2)), e(L['level']), e(L['leg']), e(line))
    h += '<div class="lev" style="color:var(--color-text-tertiary)"><span class="sc" style="flex:0 0 auto;background:var(--color-border-tertiary);color:var(--color-text-tertiary)">?</span><span style="font-weight:500;flex:0 0 64px">coverage·speed·impact</span><span style="flex:1">awaiting data: total workload baseline / time window / business-outcome link</span></div></div>'
    h += '</div>'
    return h

WRAP_HEAD = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AI proficiency card · %s</title><style>
:root{color-scheme:light;--color-background-primary:#ffffff;--color-background-secondary:#f4f3ee;--color-background-success:#eaf3de;--color-background-warning:#faeeda;--color-background-danger:#fcebeb;--color-background-info:#e6f1fb;--color-text-primary:#1a1a18;--color-text-secondary:#403f3a;--color-text-tertiary:#63625a;--color-text-info:#185fa5;--color-text-success:#3b6d11;--color-text-warning:#854f0b;--color-text-danger:#a32d2d;--color-border-tertiary:rgba(0,0,0,0.12);--color-border-secondary:rgba(0,0,0,0.22);--color-border-info:#85b7eb;--border-radius-md:8px;--border-radius-lg:12px;--font-sans:-apple-system,BlinkMacSystemFont,system-ui,sans-serif}
/* Fixed light theme: not following the OS dark mode (dark mode would lighten the
   body text and render it near-invisible on a white preview background). To
   restore dark auto-adaptation, set color-scheme back to "light dark" and add
   the @media (prefers-color-scheme: dark) block back. */
body{background:var(--color-background-secondary);margin:0;padding:20px;display:flex;justify-content:center}.wrap{max-width:720px;width:100%%}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
</style></head><body><div class="wrap">'''
WRAP_TAIL = '</div></body></html>'

os.makedirs(OUT_DIR, exist_ok=True)
for p in cards:
    frag = card(p)
    open(os.path.join(COMPACT_DIR, 'card_%s.html' % p), 'w').write(frag)
    open(os.path.join(OUT_DIR, '%s.html' % p), 'w').write((WRAP_HEAD % p) + frag + WRAP_TAIL)
    print('wrote fragment + standalone for %s (%d bytes)' % (p, len(frag)))

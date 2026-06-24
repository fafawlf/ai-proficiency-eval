import json, math, os, statistics as st

# ============================================================================
# render_stat_card.py — graphical "stat card" renderer.
# Same source data as render_cards.py (the same workflow output + nq_stats),
# rendered as a compact, card-like graphic: a 5-axis radar, gate/ability/native
# ring gauges, and a difficulty bar. Outputs cards/<person>_stat.html.
#
# All inputs come from config.json at the repo root. Point `workflow_outputs`
# at your exported workflow .output files; everything else is auto-computed.
# ============================================================================

# --- load config.json from the repo root (one level up from scripts/) --------
_CFG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
config = json.load(open(_CFG_PATH, encoding='utf-8'))
COMPACT_DIR = config.get('compact_dir', '/tmp/aiprof_compact')
OUT_DIR = config.get('out_dir', './cards')
_OUTS = config.get('workflow_outputs', [])   # add each person's .output here
PEOPLE = config.get('people', {})            # { person_id: {name, role} }
NQ_PATH = os.path.join(COMPACT_DIR, 'nq_stats.json')

# Person display comes from config.people; fall back to the person id as name.
def NAME(p): return (PEOPLE.get(p) or {}).get('name', p)
def ROLE(p): return (PEOPLE.get(p) or {}).get('role', '')

# Archetype override (en, zh, one-line headline). Left empty: the archetype
# comes from the synthesized card's `archetype` field, and falls back to the
# derive_arch heuristic below when that is absent. Add entries here only to
# force a specific archetype for a person.
ARCH = {}

cards = {}; RAW = []
for f in _OUTS:
    o = json.load(open(f))
    for c in o['result']['cards']: cards[c['person']] = c
    RAW += o['result'].get('raw_tasks', [])
try: NQ = json.load(open(NQ_PATH))
except Exception: NQ = {}

CTX = ['ctx_suff', 'ctx_time', 'ctx_src', 'ctx_scaf', 'ctx_noise']; GOAL = ['goal_mot', 'goal_scope', 'goal_stab', 'goal_acc']; FB = ['fb_detect', 'fb_loc', 'fb_hole']; EFF = ['eff_decl', 'eff_sel']
def _dm(ts, k):
    vs = [t['dims'][k] for t in ts if k in t.get('dims', {})]; return st.mean(vs) if vs else None
def _blk(ts, ks):
    vs = [t['dims'][k] for t in ts for k in ks if k in t.get('dims', {})]; return st.mean(vs) if vs else None

ANG = [-90, -18, 54, 126, 198]                  # feedback (top), context, goal, method, force
AXES = ['Feedback', 'Context', 'Goal', 'Practice', 'Effort']
MODK = ['Feedback', 'Context', 'Goal', 'Practice', 'Effort & selection']   # keys in module_scores
ANCH = ['middle', 'start', 'start', 'end', 'end']

def radar(scores):
    cx, cy, R = 140, 135, 95
    pl = lambda f: ' '.join('%g,%g' % (round(cx + R * f * math.cos(math.radians(a)), 1), round(cy + R * f * math.sin(math.radians(a)), 1)) for a in ANG)
    g = ''.join('<polygon points="%s" fill="none" stroke="rgba(255,255,255,%s)"/>' % (pl(f), op) for f, op in [(1, '.10'), (0.66, '.07'), (0.33, '.07')])
    g += ''.join('<line x1="140" y1="135" x2="%g" y2="%g" stroke="rgba(255,255,255,.06)"/>' % (round(cx + R * math.cos(math.radians(a)), 1), round(cy + R * math.sin(math.radians(a)), 1)) for a in ANG)
    vp = [(round(cx + R * max(0, min(1, s / 4)) * math.cos(math.radians(a)), 1), round(cy + R * max(0, min(1, s / 4)) * math.sin(math.radians(a)), 1)) for s, a in zip(scores, ANG)]
    g += '<polygon points="%s" fill="rgba(224,196,138,.15)" stroke="#E0C48A" stroke-width="1.5"/>' % (' '.join('%g,%g' % p for p in vp))
    g += ''.join('<circle cx="%g" cy="%g" r="3" fill="#E0C48A"/>' % p for p in vp)
    for nm, s, a, an in zip(AXES, scores, ANG, ANCH):
        lx = round(cx + 113 * math.cos(math.radians(a)), 1); ly = round(cy + 113 * math.sin(math.radians(a)) + (0 if a == -90 else 3), 1)
        g += '<text class="rt" x="%g" y="%g" text-anchor="%s">%s <tspan class="rs">%.1f</tspan></text>' % (lx, ly, an, nm, s)
    return g

def gauge(frac, num, label, color):
    return ('<div class="g"><svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="5"/>'
            '<circle cx="32" cy="32" r="26" fill="none" stroke="%s" stroke-width="5" stroke-linecap="round" stroke-dasharray="%.1f 163.4" transform="rotate(-90 32 32)"/>'
            '<text class="gnum" x="32" y="38" text-anchor="middle">%s</text></svg><div class="gl">%s</div></div>') % (color, frac * 163.4, num, label)

def derive_arch(modscores):
    # Heuristic fallback: pick an archetype from the person's strongest module.
    top = max(modscores, key=lambda k: modscores.get(k, 0))
    t = {'Feedback': ('The Verifier', 'checks before trusting'), 'Context': ('The Architect', 'sets the stage first'), 'Goal': ('The Strategist', 'aims at real problems'), 'Effort & selection': ('The Operator', 'dials the power right'), 'Practice': ('The Builder', 'compounds good habits')}
    title, subtitle = t.get(top, ('The Builder', 'compounds good habits')); return title, subtitle, ''

TPL = open(os.path.join(os.path.dirname(__file__), 'stat_card_template.html'), encoding='utf-8').read() if os.path.exists(os.path.join(os.path.dirname(__file__), 'stat_card_template.html')) else None

def render(p):
    c = cards[p]; cj = c.get('card', {}); ms = c.get('module_scores', {}) or {}
    ts = [t for t in RAW if t.get('person') == p and t.get('cls') == 'real_task']
    ver = _dm(ts, 'fb_verify'); refl = _dm(ts, 'fb_reflex'); gs = [x for x in [ver, refl] if x is not None]
    gate = st.mean(gs) if gs else (c.get('ability') or 0); gcoef = max(0.0, min(1.0, gate / 4.0))
    ab = [x for x in [_blk(ts, CTX), _blk(ts, GOAL), _blk(ts, EFF), _blk(ts, FB)] if x is not None]
    ability = st.mean(ab) if ab else (c.get('ability') or 0)
    native = gcoef * ability
    glevel = (cj.get('gate') or {}).get('level', '—')
    scores = [ms.get(k, 0) for k in MODK]
    av = ARCH.get(p)
    if not av:
        a = cj.get('archetype') or {}
        if a.get('en') and a.get('zh'): av = (a['en'], a['zh'], a.get('headline', ''))
    en, zh, head = av or derive_arch(ms)
    if not head: head = ((cj.get('gate') or {}).get('line') or (cj.get('signatures') or [{}])[0].get('line', '')); head = head[:54]
    # difficulty + throughput
    nq = NQ.get(p, {}); xL = nq.get('chat', 0); xS = nq.get('simple', 0); xC = nq.get('complex', 0)
    pw = nq.get('per_week'); sess = nq.get('sessions', 0)
    thru = '<span class="n">%s</span> <span class="kick">/ week · %d sessions · mostly complex work</span>' % (('%g' % round(pw) if pw else '—'), sess) if (xL + xS + xC) else '<span class="kick">volume data TBD</span>'
    bar = '<i style="flex:%d;background:#4a463e"></i><i style="flex:%d;background:#8a8378"></i><i style="flex:%d;background:#E0C48A"></i>' % (max(xL, 1), max(xS, 1), max(xC, 1))
    blabs = '<span>Chat <b>%d</b></span><span>Simple <b>%d</b></span><span>Complex <b>%d</b></span>' % (xL, xS, xC)
    # strongest / weakest from synthesized modules
    dims = [d for m in cj.get('modules', []) for d in m.get('dims', [])]
    strong = max(dims, key=lambda d: d.get('score', 0)) if dims else {}
    weak = min(dims, key=lambda d: d.get('score', 9)) if dims else {}
    s_name = strong.get('name', '—'); s_txt = (strong.get('best') or strong.get('why_std') or '')[:46]
    w_name = weak.get('name', '—'); w_txt = (weak.get('so') or weak.get('worst') or '')[:46]
    gauges = gauge(min(1, native / 4), ('%.2f' % native).lstrip('0') if native < 1 else '%.2f' % native, 'AI native', '#E0C48A') + \
             gauge(min(1, ability / 4), '%.2f' % ability, 'ability', '#cfcabf') + \
             gauge(min(1, gcoef), ('%.2f' % gcoef).lstrip('0'), 'verify gate', '#cfcabf')
    sub = '%s · %s · %s' % (NAME(p), ROLE(p), (cj.get('portrait', '') or '')[:14])
    rep = {'brand': config.get('brand', 'verity.'), 'name_en': en, 'arch_zh': zh, 'glevel': glevel, 'sub': sub, 'radar': radar(scores), 'gauges': gauges,
           'bar': bar, 'blabs': blabs, 'thru': thru, 'sig': head, 's_name': s_name, 's_txt': s_txt, 'w_name': w_name, 'w_txt': w_txt}
    html = TPL
    for k, v in rep.items(): html = html.replace('@@' + k + '@@', str(v))
    out = os.path.join(OUT_DIR, '%s_stat.html' % p); os.makedirs(OUT_DIR, exist_ok=True); open(out, 'w', encoding='utf-8').write(html)
    print('wrote', out, '· native %.2f · gate %.2f · ability %.2f' % (native, gcoef, ability))

if __name__ == '__main__':
    for p in cards: render(p)

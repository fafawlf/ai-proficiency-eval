#!/usr/bin/env python3
"""Compact raw agent session logs into clean, scorable task traces.

This is the first stage of the AI-proficiency-eval pipeline. It reads raw
session JSONL files from one or more configured sources (Claude Code, Cursor,
Codex, ...), strips them down to a clean alternating [USER]/[AI] trace, and
writes:

  - one compacted .txt per task under  <compact_dir>/t/
  - manifest.json   (one row per kept task: person/tool/task_id/path/turns/...)
  - nq_stats.json   (per-person session count x difficulty mix x throughput)

Everything is driven by a config.json that lives at the repo root (one level
up from this script). Nothing about the people or the file locations is
hardcoded here.

NOTE ON NEW TOOL FORMATS: iter_msgs() below is tolerant of the common
"message"/"payload" shapes used by Claude Code / Cursor / Codex. Some newer
agent formats bury the real human turns under layers of automation: heartbeat
events, tool-orchestration envelopes, scheduler chatter, etc. For those you
need a small per-format adapter (to locate the genuine user turn) plus a noise
filter (to drop the machine-generated events), otherwise the human signal gets
drowned out and difficulty/throughput stats skew. Add such an adapter as a new
branch in iter_msgs() rather than trying to force the existing heuristics.
"""

import json
import glob
import os
import re
import datetime as _dt
from collections import defaultdict, Counter

# --- Load config (always resolved relative to this script, repo-root/config.json) ---
_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')
with open(_CFG_PATH, encoding='utf-8') as _fh:
    CFG = json.load(_fh)

OUT = os.path.expanduser(CFG['compact_dir'])
os.makedirs(OUT + '/t', exist_ok=True)

# CANON merges several identities into one person. Use it when the same human
# shows up under more than one handle/machine (e.g. a server box and a laptop,
# each writing logs under a different account name) and you want their tasks
# pooled under a single canonical id. Driven entirely by config.canon, e.g.
#   "canon": { "alt-handle": "primary-handle" }
CANON = CFG.get('canon', {}) or {}


# === count x difficulty x throughput: prepared automatically at compact time ===
# (the render/score stage just reads nq_stats.json; nothing is filled in by hand)
_TSRE = re.compile(r'"(?:timestamp|created_at|createdAt|ts)"\s*:\s*"(\d{4}-\d\d-\d\d)')
_FNDATE = re.compile(r'(\d{4})[-_]?(\d\d)[-_]?(\d\d)')


def _sess_dates(f):
    """Set of calendar dates touched by this session.

    Prefers real timestamps found inside the file; falls back to a date parsed
    from the filename (some exporters put the date there). Empty set => the
    throughput rate for that person stays unknown (to be filled later).
    """
    ds = set()
    n = 0
    for line in open(f, errors='ignore'):
        n += 1
        if n > 4000:
            break
        m = _TSRE.search(line)
        if m:
            ds.add(m.group(1))
    if not ds:
        mm = _FNDATE.search(os.path.basename(f))
        if mm:
            ds.add('%s-%s-%s' % mm.groups())
    return ds


def _tier(hum, txt):
    """Classify a task by rough workload: chat / simple / complex.

    Same definition the render stage uses. Note this couples a little with a
    "deep-delegation" working style (few human turns, heavy tool use can still
    be complex), which is intentional.
    """
    kb = len(txt) / 1024
    sp = txt.count('[AI]')
    tl = txt.count('⟨tools:')
    if hum < 1 or (hum <= 2 and kb < 2 and tl <= 2):
        return 'chat'
    if kb >= 12 or sp >= 22 or hum >= 6 or tl >= 15:
        return 'complex'
    return 'simple'


STATS = defaultdict(lambda: {'sessions': 0, 'chat': 0, 'simple': 0, 'complex': 0, 'dates': set()})


def _accum(p, h, txt, f):
    """Accumulate per-person stats. Counts every session (including chat),
    i.e. before the h<3 'too thin to score' filter is applied downstream."""
    st = STATS[p]
    st['sessions'] += 1
    st[_tier(h, txt)] += 1
    st['dates'].update(_sess_dates(f))


def blocks_text(c):
    """Flatten a message 'content' value into (joined_text, tool_names)."""
    if isinstance(c, str):
        return c, []
    txt = []
    tools = []
    if isinstance(c, list):
        for b in c:
            if not isinstance(b, dict):
                continue
            ty = b.get('type')
            if ty in ('text', 'input_text', 'output_text'):
                txt.append(b.get('text', ''))
            elif ty in ('tool_use', 'function_call'):
                tools.append(b.get('name') or b.get('tool_name') or 'tool')
            elif ty == 'tool_result':
                pass
    return ' '.join(txt), tools


def iter_msgs(f):
    """Yield (role, text, tool_names) per message, tolerant of CC/Cursor/Codex.

    See the module docstring: a brand-new agent format that hides the real user
    turn under automation/heartbeat events needs its own adapter branch here
    plus a noise filter, not a tweak to the existing heuristics.
    """
    for line in open(f, errors='ignore'):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        # Codex: payload-based envelope
        pay = o.get('payload') if isinstance(o.get('payload'), dict) else None
        role = None
        content = None
        if pay and ('role' in pay or 'content' in pay):
            role = pay.get('role')
            content = pay.get('content')
        else:
            msg = o.get('message') if isinstance(o.get('message'), dict) else None
            role = o.get('type') if o.get('type') in ('user', 'assistant') else (o.get('role') or (msg.get('role') if msg else None))
            content = (msg.get('content') if msg else o.get('content'))
        if role not in ('user', 'assistant'):
            continue
        txt, tools = blocks_text(content)
        yield role, txt, tools


def clean_user(t):
    """Strip wrapper tags so only the genuine human text survives."""
    m = re.search(r'<user_query>(.*?)</user_query>', t, re.S)
    if m:
        t = m.group(1)
    t = re.sub(r'<timestamp>.*?</timestamp>', '', t, flags=re.S)
    return t.strip()


def compact(f):
    """Compact one session file into a clean [USER]/[AI] trace.

    Returns (num_human_turns, trace_text). Synthetic/system-injected user
    messages (XML envelopes, 'caveat' banners, tool_result echoes) are skipped
    so the human-turn count reflects real human prompts.
    """
    lines = []
    hum = 0
    for role, txt, tools in iter_msgs(f):
        if role == 'user':
            u = clean_user(txt)
            if not u or u.startswith('<') or u.lower().startswith('caveat') or 'tool_result' in u[:30]:
                continue
            hum += 1
            lines.append('\n[USER] ' + u[:1500])
        else:
            seg = ''
            if txt.strip():
                seg = txt.strip()[:600]
            if tools:
                seg = (seg + '  ⟨tools:' + ','.join(tools[:8]) + '⟩').strip()
            if seg:
                lines.append('[AI] ' + seg)
    return hum, '\n'.join(lines)


def expand_paths(pattern):
    """Expand ~ and shell globs in a source glob pattern."""
    return glob.glob(os.path.expanduser(pattern))


# --- Main: iterate config.sources, attribute each file to its source.person ---
man = []
for src in CFG['sources']:
    tool = src.get('tool', 'unknown')
    person_raw = src['person']
    pattern = src['glob']
    for f in expand_paths(pattern):
        # skip macOS AppleDouble sidecars and tiny/empty exports
        if '/._' in f:
            continue
        try:
            if os.path.getsize(f) < 5000:
                continue
        except OSError:
            continue
        # attribute strictly by config (no path-sniffing of usernames), then canonicalize
        p = CANON.get(person_raw, person_raw)
        h, txt = compact(f)
        _accum(p, h, txt, f)            # count / difficulty / throughput stats (chat counted, pre-filter)
        if h < 3:
            continue                    # too few human turns to score meaningfully
        tid = os.path.basename(f)[:8]
        op = OUT + '/t/%s_%s_%s.txt' % (p, tool, tid)
        with open(op, 'w') as wfh:
            wfh.write(txt)
        man.append({
            'person': p, 'tool': tool, 'task_id': tid, 'path': op,
            'turns': h, 'kb': round(len(txt) / 1024, 1), 'tier': _tier(h, txt),
        })

with open(OUT + '/manifest.json', 'w') as wfh:
    json.dump(man, wfh, ensure_ascii=False, indent=0)

# count x difficulty x throughput -> nq_stats.json (read by the render/score stage)
nq = {}
for p, st in STATS.items():
    ds = sorted(st['dates'])
    tot = st['sessions']
    rec = {
        'sessions': tot, 'chat': st['chat'], 'simple': st['simple'], 'complex': st['complex'],
        'date_min': ds[0] if ds else None, 'date_max': ds[-1] if ds else None,
        'active_days': len(ds), 'per_week': None,
    }
    if len(ds) >= 2:
        d0 = _dt.date.fromisoformat(ds[0])
        d1 = _dt.date.fromisoformat(ds[-1])
        wk = max(1.0, (d1 - d0).days / 7.0)
        rec['per_week'] = round(tot / wk, 1)   # tasks/week over the calendar span (None if no timestamps)
    nq[p] = rec
with open(OUT + '/nq_stats.json', 'w') as wfh:
    json.dump(nq, wfh, ensure_ascii=False, indent=0)
print('nq_stats (sessions / per_week):', {p: (r['sessions'], r['per_week']) for p, r in nq.items()})

c = Counter(m['person'] for m in man)
kb = defaultdict(float)
for m in man:
    kb[m['person']] += m['kb']
print('tasks per person:', dict(c))
print('compact KB per person:', {k: round(v) for k, v in kb.items()})
print('total tasks:', len(man))

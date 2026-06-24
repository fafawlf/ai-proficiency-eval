---
name: ai-proficiency-eval
description: >-
  Evaluate how well a person uses AI ("AI proficiency" / "AI-native") from their
  session logs. Scores each task 0–4, then produces one plain-language capability
  card per person plus a within-domain tier (strong / medium / weak). Useful for
  setting AI-native bonus tiers, comparing a team side by side, and giving an
  individual constructive feedback. Input is the session jsonl from Claude Code,
  Cursor, Codex, or similar agent CLIs.
  Use when you want to: assess one person's or a team's AI proficiency, build an
  AI-native capability card, set an AI-native bonus tier, compare who uses AI
  better, or understand how good someone is at front-loading context, course-
  correcting, and verifying.
  Three iron rules: score only what the human controls (the inputs they front-load
  and the corrections they make) — the AI's autonomous behavior is never the
  human's fault; score per task, in plain language, with every claim backed by a
  real quote; and rank by gate × ability × leverage into buckets, not a leaderboard.
  Not for: judging whether the business output itself is good, or grading a single
  prompt in isolation.
---

# AI Proficiency Evaluation

Feed in one person's AI session logs and get back an evaluation of "how well do they use AI?" plus constructive feedback. Two goals: help a leader judge objectively, and help the person improve. The full anchor tables, scoring method, and card format live in `reference/rubric.md` — **read it before you start.**

All scripts in this skill read a `config.json` at the repo root. That file is where you point the tool at your data and tell it who's who. Read it once before running anything.

## The three iron rules (this method was calibrated over dozens of painful iterations — break any one and the whole thing is worthless)

**1. The attribution law — only score what the human controls.** A person has exactly two levers over the AI: the **inputs they front-load** (the facts, goals, constraints, intensity, and tool choice they hand it) and their **course-correction** (catching mistakes and fixing them). **The AI's own autonomous behavior — fanning out sub-agents on its own, spinning in circles, faking completion, going baroque — is never directly counted against the human.** It's only used as evidence to reason backwards: did the human provoke it, and did they catch it? Before scoring any step, ask "whose move was this?" Process volume (tokens, turns, number of agents, number of sessions) is an *anti-indicator* and is never scored.

> Classic mistake: "they used 37 agents on an open-ended question" — that's the AI fanning out on its own, not the human's failing. The human's only lever was "didn't say keep it lightweight at the start." When the human shouts "this is overcomplicated" and cuts it back, that's a course-correction *win*, not bad practice.

**2. Score per task + plain language + every claim backed by a real quote.** The signal comes from having *actually counted* the cases behind each claim, not from skimming and going on impression (showing just one example = giving 1/N of the evidence, and it reads thin). Each dimension must show its work: the count (n times done / not done), the best and worst case (with the real quote), the pattern (under what conditions they pull it off), the cross-dimension signature, and the "so what" (next step). **Write the whole thing in plain language — no machine atom-names, abbreviations, or percentiles used as vocabulary** (plain numbers are fine). Pin each conclusion onto a real transcript snippet *as you read* (method B) — that beats reading everything and then trying to recall it (method A drifts into jargon).

**3. Gate × equal-weighted ability × leverage — buckets, not a leaderboard.**
- **The gate = verification behavior (closing the loop on ground truth + reflexive self-check). It's a multiplier, not an addend** — if someone doesn't check their own work, the output can't be trusted, so it has no value, and nothing else makes up for it. The gate score over 4 becomes a 0–1 coefficient. **Anchor the gate to "rigorous behavior the human controls," not "did it land / get accepted"** — landing gets gamed by soft domains (e.g. a human reviewer signs off), so sloppy people can still "land everything," which inflates the gate and collapses the discrimination. Acceptance criteria (setting a standard) belong to the *goal* dimension; the reflexive self-check belongs to the *gate*.
- **The four ability blocks are equally weighted** (measured weights come out ≈ equal anyway; discrimination comes mainly from the gate's multiplier, not from small fractional differences between ability blocks).
- **Leverage = the thing the bonus actually multiplies** (ability = can they use it; leverage = how much value they got out of it; accumulation / reuse / compounding lives here).
- **Only good enough for buckets (strong / medium / weak).** Adjacent 0.1 gaps are noise. Don't force cross-domain comparisons. Without low-proficiency samples in the pool, discrimination won't emerge.

## The pipeline (the scripts are all in `scripts/` and actually run)

**① Define scope + attribute to a person.** Find each person's session jsonl. **Attribution is by `cwd` / account → person, defined in `config.json`.** Each source entry carries a `person` field, and a `canon` map merges one person's multiple machines/accounts into a single identity (so the same person working from two different `cwd`s gets counted as one person, not two). **The scaffolding is point-in-time** — the evaluation input = the session *plus* the snapshot of the scaffolding as it was then (the current filesystem ≠ what it was at the time).

**② Compact the trajectory + auto-derive count / difficulty / throughput.** `scripts/compact_sessions.py` squeezes each jsonl into a "clean trajectory" (keeps the human's verbatim words + the AI's text + one line per tool call, drops the big tool-result blobs). It's compatible with the Claude Code / Cursor / Codex formats, attributes each session to a person (applying the `canon` merge from `config.json`), and writes `compact/t/*.txt` plus a **manifest** in the compact dir (configurable, default `/tmp/aiprof_compact`). **It also auto-produces `nq_stats.json`**: per person, the session count, difficulty buckets (chit-chat / simple / complex), the real-timestamp date window, active days, and per-day / per-week throughput. **This is what makes "whenever there's a session, the count dimension is automatic"** — render reads it directly, no manual entry (exports missing timestamps get auto-flagged "rate TBD"). **Before running, only adjust the input glob, the attribution config, and (for a new format) the parsing / cleaning rules.**

> **New formats need an adapter written on the spot:** this script only understands the Claude Code / Cursor / Codex shapes. Other runtimes are a different layout entirely. **Strip out automation noise — cron / heartbeat jobs, sub-agent continuations, ledger/bookkeeping files — entirely, and keep only the real human interactions.** Otherwise you count the machine's autonomous work as the person's. (This is exactly the trap where a feed shows dozens of "messages" but only a third were actually human-driven; counting the heartbeats as the person's tasks badly inflates their volume.) Note where the human's verbatim text lives in each format (e.g. Cursor wraps it in a `<user_query>` tag).

**③ Score per task (a Claude Code Workflow — needs multiple agents).** `scripts/score_workflow.mjs` runs `Workflow({scriptPath})`. **Convention: the workflow reads the manifest from a fixed path inside the compact dir** (the `args.manifest_path` workflow global isn't reliable at runtime — don't depend on it; to switch person, copy that person's manifest over the fixed path and rerun). One reader per task: read the full trajectory → for each of the 18 dimensions, score 0–4 *only where it's clearly demonstrated* → pull the human's verbatim quotes → apply the attribution correction → label each as real / meta / noise. Returns `cards` (the already-synthesized density-card JSON) plus `raw_tasks` (per-task per-dimension scores, used to validate the weights). ~120 tasks is roughly 7M tokens; 20 tasks roughly 1M.

> **`raw_tasks` is for sanity-checking only — don't anchor the gate to "verified vs. abandoned" outcomes:** that outcome label and the ground-truth-closing score are scored by the same reader, are near-synonyms (circular), and soft-domain landing is easy → contamination. The gate must be anchored to verification *behavior* (closing the loop on ground truth + reflexive self-check), not to the outcome. (A past version anchored the gate to that outcome and got an impressively high AUC — that's been retired precisely because it was measuring the circular thing.)

**④ Render the cards.** `scripts/render_cards.py` reads the workflow output → one standalone HTML per person (light/dark adaptive; the body gray text is already tuned for enough contrast) plus an inline fragment. **You normally only edit the output list (it can merge multiple runs) and the cards output path.** Count / difficulty / throughput are **read automatically from ②'s `nq_stats.json`** — the manual `_NQfull` / `_TM` dicts degrade to "authoritative overrides": a person present in the dict uses the hand-filled value (a full workflow gets difficulty more precisely), and anyone absent is auto-filled from the session-level stats, so **switching to a new person doesn't require editing those two dicts.** The card includes the **count × difficulty × outcome cross-tab + the time dimension · throughput** (method in the same-named section of `rubric.md`; the difficulty × outcome join uses each `raw_tasks` task_id to look the transcript back up at `<compact dir>/t/<task_id>.txt`). For the inline view, paste the fragment with the visualization tool; the persistent version is written into the repo at `cards/<person>.html`.

> **The graphical "stat card" (optional, a second skin):** `scripts/render_stat_card.py` (same source data + `stat_card_template.html`) produces a séance-styled **stat card** — a five-axis radar + three ring gauges (gate / ability / native) + a difficulty-distribution bar + a title (archetype), written to `cards/<person>_stat.html`. The radar, gauges, and difficulty bar are all computed automatically from the scores; the archetype comes from the synth's `archetype` field (or, if missing, is derived from the strongest module). It's the "lightweight version" suited to sharing in a group chat or a bio, complementary to the detailed 18+1-dimension card.

> **Auto vs. override:** `nq_stats.json` (auto-computed in ②, session-level, good enough day to day) supplies the full difficulty + throughput; only when you want a more precise "full structured difficulty across all top-level tasks," or when an anonymized export is missing timestamps and needs a one-line manual note, do you hand-fill an override in `_NQfull` / `_TM` (a hand-filled value always beats the auto one). Cursor agent transcripts often strip timestamps → auto-flagged "rate TBD."

**⑤ Bucket.** Compute `gate × equal-weighted ability × leverage` per `reference/rubric.md`; **sort into strong / medium / weak buckets within the same role / domain**, not a decimal-ranked leaderboard.

## Delivery (the honesty you must carry every time)
- One capability card per person (portrait + signature + dual axis + reality gate + Top 3 + the 18 dimensions with verbatim quotes + **count × difficulty × outcome cross-tab + the time dimension · throughput**); plus a team side-by-side and the shared signature (a common one: the whole team "under-invests in front-loading context, and 30 seconds in hasn't flagged the fork in the road").
- **Count × difficulty × outcome:** difficulty (chit-chat / simple / complex, full structured) × outcome (accepted / abandoned / can't-tell, sampled) shows *which tier* a person drops the ball in; the time dimension uses real timestamps for the window + per day/week. The three have different bases (full / sampled / only computable when timestamps exist) — label each separately on the card. See `rubric.md`.
- **Always state the limits:** buckets, not a ranking; don't compare across domains; under-powered (missing a low-proficiency floor); the 0–4 scores are LLM-judged — anything bonus-grade needs a second reader and an inter-rater agreement check; within leverage, **coverage (count) / speed (throughput) are now auto-computed from `nq_stats.json`** (timestamp-less exports flagged "rate TBD"), leaving only **impact (the tie to business outcomes) still waiting on data.**
- **Paying out bonuses:** anchor on the gate (verification behavior: closing the loop on ground truth + reflexive self-check, *not* the landing outcome), bucket within the same domain, and don't pay out on decimal differences. Within the gate, the reflexive self-check is the most subjective part — before paying, manually review the few cases that got marked down. If you need a true ranking or a cross-domain comparison, the prerequisite is first collecting samples that include failures, low-proficiency cases, and multiple domains.

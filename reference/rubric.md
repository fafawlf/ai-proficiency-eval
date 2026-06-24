# Scoring Reference: 19-Dimension Anchor Table + Gate + Scoring Method + Card Format

This is the intellectual core of the evaluation. It scores **how well a person uses AI** — not how good the AI is, and not how good the underlying work product is. Read the attribution law first; it governs every single point you assign.

## The Attribution Law (sits on top of everything — apply it before assigning any point)

You are scoring **what the human controlled**, not what happened inside the session. A person has exactly two control surfaces over an AI:

1. **Up-front input** — the facts, goals, constraints, and effort level they feed it, plus the tools/models they pick.
2. **Course correction** — catching the AI when it drifts, and steering it back.

**Autonomous AI behavior never counts directly against the human.** If the AI spins up its own sub-agents, loops in circles, fakes completion, or gold-plates something into a baroque mess — that is the AI's move, not the person's failing. Such behavior is only ever used as *evidence*, read in two directions:

- Did the human's input **invite or fail to fence off** the bad behavior?
- Did the human **catch and correct** it?

Before scoring any step, ask: **"Whose move was this?"**

**Anti-metrics.** Token count, number of turns, number of agents, number of sessions, prompt character count — these are all *process volume*, and they **never** earn points. High process volume is often a symptom of *low* efficiency, not skill.

## Unit of Analysis and Denoising

The unit is the **task**, not the session. A single session usually contains several tasks. Before scoring, strip out the noise:

- scheduled/cron runs
- sub-agent continuation fragments
- failed-auth scraps
- "meta" tasks where the person was building this very evaluation tool

Each reader first classifies every candidate as `real_task`, `meta_self_referential`, or `noise_or_failed`. Only `real_task` items are scored.

## The 0–4 Scale (plus N/A)

- **4 — Exemplary.** Could be used to teach others.
- **3 — Meets bar.** Done reliably and consistently.
- **2 — Partial.** Weak, inconsistent, or only done when forced.
- **1 — Missing.** Should have done it, didn't.
- **0 — Anti-pattern.** Actively did the opposite.
- **N/A — Not applicable.** The situation didn't call for it. Excluded from the mean. **Absence is not the same as failure** — an N/A never drags a score down.

## The 19-Dimension Anchor Table

Each dimension is anchored at its two poles (0 and 4); you interpolate for the middle. The table is grouped into five capability blocks. (Note: dimension #16 "setup-defense", #12's "emotion-stripping" rule, and the gate's severity rule are the substantive additions over earlier drafts.)

### Context — *can the AI even start on solid ground?*

1. **Sufficiency** — At kickoff, hand over the facts it couldn't possibly infer.
   - **4:** gives everything at once, zero clarifying questions needed.
   - **0:** feeds a misleading "fact" that sends the whole run off the rails.
2. **Timing** — Necessary premises are on the table *before* the AI needs them.
   - **4:** everything is already in place before the AI hits the wall.
   - **0:** the unlocking piece of info is withheld until after the AI has spun fruitlessly for a long time.
3. **Source quality** — What you provide (or ask the AI to consult) rests on real, verifiable things.
   - **4:** everything points at real files / real data.
   - **0:** feeds an unverified second-hand judgment as if it were fact, biasing the run.
4. **Scaffolding** — The things you use constantly are auto-loaded at startup.
   - **4:** hardened into lint rules / required-reading skills / persistent memory.
   - **0:** the scaffolding itself is wrong and biases the work.
5. **Signal-to-noise** — Context is relevant, layered, and internally consistent.
   - **4:** precisely layered, no contradictions.
   - **0:** dumps a flood of irrelevant or contradictory material that drowns the signal.

### Goal — *motivation / scope / stability / acceptance shape*

(Acceptance shape — i.e. setting a *verifiable pass condition* — is a property of *goal quality*, so it lives here, not in the gate.)

6. **Motivation / real problem** — You can articulate *why* this is being done, and it's a genuine problem.
   - **4:** tied to a real motive; proactively questions whether the problem is real.
   - **0:** a fake problem, and nobody challenges it.
7. **Scope** — Cut to a unit that can actually be closed.
   - **4:** proactively phases and isolates the work.
   - **0:** unbounded "boil the ocean," never converges.
8. **Goal stability** — Progress by *narrowing*, not by lurching between directions.
   - **4:** same core axis, deepening into a decision chain.
   - **0:** redefines the axis every few turns. (AI-proposed solution churn does *not* count against you — see the attribution law.)

### Effort and Tool Selection

9. **Effort declaration** — At kickoff, say whether this is a light touch or a heavy lift.
   - **4:** explicitly declares the intended effort level.
   - **0:** never declares it, so the AI routinely over- or under-powers the work. (The AI fanning out a few agents internally is not your doing.)
10. **Tool/model selection** — The tools, models, and approaches you actually chose fit the job.
    - **4:** chosen precisely.
    - **0:** persistently mismatched, and ignored.

### Feedback — *course correction*

(Truth-closure and reflexivity have been pulled out into the gate, so the capability side here keeps only detection, localization, and defect-hunting.)

11. **Detection** — When the AI reports "done," you see through whether it's real.
    - **4:** proactively forces a re-read and catches fake completions.
    - **0:** rubber-stamps it, and broken work ships.
12. **Localization** *(scored on constructive content; emotion is not scored)* — Your correction points at *where* and *why*.
    - **4:** pinpoints the exact column / row / definition + the reason, and the AI fixes it in one pass. **(Cursing *and* being precise still scores 4.)**
    - **0:** pure negation, zero direction.
    - ⚠️ **Emotion is a profile annotation (⚡), not a score input.** High emotion + high information still scores high. A low-information veto like "wrong, redo it" scores **1** (docked for carrying no information, *not* for the temper). Spinning in circles loses points *through this channel* — a 1 plus failure to converge — don't double-dock it by re-counting the emotion.
13. **Defect-hunting** — You proactively poke at real flaws.
    - **4:** surfaces a flaw the AI never mentioned, forcing out the root cause.
    - **0:** never checks for defects; everything blows up downstream.
14. **Reflexivity** — When the result is wrong, *suspect yourself first*.
    - **4:** proactively catches your own definition drift; overturns your own premise.
    - **0:** clings to a wrong premise, refuses to admit it.
    - **(Combined with truth-closure into the "verification-behavior gate" — does not live in the feedback block.)**

### Practice — *cross-task habits*

(Accumulation/reuse belongs to the *leverage* side; capability keeps only convergence.)

15. **Convergence** — When complexity rises, hit the brakes and cut back.
    - **4:** proactively deletes redundant artifacts, keeps it clean.
    - **0:** turns a simple thing into a baroque monster *yourself*. (The AI going baroque on its own is not your doing.)
16. **Setup-defense** *(prevention vs. firefighting — added in v2)* — Put a safety net under operations that can go wrong, *before* you run them.
    - **4:** defaults to a dev environment; runs destructive operations as dry-run / step-by-step first; declares the verification standard as a contract up front.
    - **0:** runs dangerous operations bare; only adds protection *after* hitting the wall or causing an incident.
    - **N/A:** pure read/analysis with no destructive operations → fold this into "verification-prefiguring" instead.

## The Gate: Verification Behavior (= Truth-Closure + Reflexivity; a multiplier, not an addend)

The gate measures one thing: **do you actually check your own work?** That is a *human-controllable rigor behavior* — it is **not** "did the work land" (an outcome).

It is built from two dimensions:

- **Truth-closure** — Before handing off, you genuinely *verify*: re-run it, read it back, re-check it in production, click through in a real browser — rather than trusting the AI's "it's done."
- **Reflexivity** — When the result is wrong, you suspect yourself first: you catch your own definition drift, your own "wrong-but-I-ran-with-it" premise. *This dimension has the largest spread across people and is the gate's main driver.*

### Severity rule (v2)

A human-driven destructive operation — `DROP`, deleting a partition, editing production, a force-push — costs that task **at least −1 on truth-closure** (capping it at ≤1), **even if the data was recovered afterward.** The more destructive incidents of this kind, the lower the gate goes; **two or more is a red line** that knocks the person down a tier on the reality-gate.

Attribution doesn't change here: the *AI* running a `DROP` on its own isn't charged to the human — but "the human didn't set up defenses, didn't dry-run, and let it rip" is an up-front failure, and it's docked on the gate by severity.

### The algorithm

```
gate_score   = mean(truth_closure, reflexivity)
gate_factor  = gate_score ÷ 4          (linear, full-scale)
```

Use the **equal-weighted mean** — when real money is on the line you want stability, not a score dangling off one noisy dimension. If you want to lean harder into the "weakest-link" philosophy, switch to **min**, which pushes people with a single bad dimension even lower and sharpens the separation.

### Why multiply, not add

Output value is a pipeline: *design → build → verify → deliver*. The value at the end is the **product** of each stage's pass-rate. If you don't check your own work, the output is untrustworthy, which means it has no value — and no amount of brilliance in the other stages buys that back. Addition would let someone "skip verification and still scrape a passing grade by stacking the other dimensions." That's wrong.

### ⚠️ Why anchor on BEHAVIOR, not OUTCOME (a hole we fell into — don't repeat it)

Do **not** use "did it land?" as the gate. Soft domains have low acceptance bars — a human reviewer signs off, a consulting deliverable gets accepted — which means **a person who isn't rigorous can still get everything "accepted" in a forgiving domain.** Anchor the gate on outcomes and that person's gate score is inflated, and your separation collapses.

Concretely: imagine someone working in a domain where the acceptance bar is just "a human signs off" — HR-style sign-offs, advisory deliverables. Their truth-closure and reflexivity may be the *lowest* in the cohort, yet *every one of their tasks "passed acceptance."* If you anchor the gate on landed outcomes, their score gets dragged *up* to match everyone else's. Only after you re-anchor the gate on **verification behavior** does their score fall back to where it belongs — well below the rigorous operators. **Landed outcomes carry a domain bias; they're useful as a sanity check, but they must never be the gate's anchor.**

(For the same reason, any historical "the gate has high AUC / cleanly separates good from bad"-style claim computed against a *landed-outcome* label is discarded — that label and truth-closure were scored by the same reader, are near-synonyms, so the number is both circular and contaminated by soft-domain bias. Do not cite it.)

### The "set a standard" half belongs to Goal

"Set a verifiable pass condition" (the deliverable's shape / who it's for / how you compute pass) = **acceptance shape**, which is **goal quality** and stays in the goal block. The gate only governs the *act of verifying*. In domains you can't mechanically verify (HR, advisory), the pass condition *is* "who reviews and signs off," and verification *is* "actually obtaining that sign-off."

## Final Scoring Method

```
AI-proficiency score
  = verification_gate (gate_score / 4, range 0–1)        gate_score = mean(truth_closure, reflexivity)
  × capability  (four equal-weighted blocks:
        Context · Goal[motivation/scope/stability/acceptance-shape] · Effort+Selection · Feedback[detection/localization/defect-hunting])
  × leverage    (target-picking × delegation × coverage × accumulation;  verification is counted once, in the gate)
```

- **Truth-closure and reflexivity are pulled *out* of capability** to avoid double-counting: acceptance-shape stays in Goal, reflexivity goes to the gate, and Feedback retains only detection / localization / defect-hunting.
- **Separation comes mainly from the gate (the multiplier), not from small decimal differences in capability.** The four capability blocks are equal-weighted (in practice a learned weighting ≈ equal weighting; the sample isn't large enough to support a real gradient). Don't hand-tune the gate curve against a handful of failure samples to massage the ranking — that's overfitting.
- **Accumulation / reuse belongs to leverage** (it compounds and can't be measured from a single task).
- **Leverage is what the bonus actually multiplies by.** Capability = *can you use AI well?* Leverage = *how much value did you produce with it?* Coverage / speed / impact often wait on data.

## Count × Difficulty × Outcome + The Time Dimension (how to operationalize "coverage / speed" inside leverage)

The capability score (gate × equal-weighted blocks) only answers *"can you use it?"* Leverage answers *"how much value did you produce?"* Coverage (count) and speed (time) used to be marked "pending data"; there's now a fixed method, and every card must carry it:

- **Difficulty tiers (structured, full population).** For **every top-level task** (after stripping sub-agents / cron / continuation runs), classify by trajectory into chat / simple / complex.
  - `chat` = human turns < 1, *or* (≤2 turns AND <2KB AND ≤2 tool calls)
  - `complex` = raw size ≥18KB, *or* human turns ≥8, *or* tool calls ≥25, *or* contains sub-agents
  - everything else = `simple`
  - ⚠️ This is a **workload** measure, and it couples with the style of someone who **delegates deeply** (they hand off broadly → the trajectory grows large → it *looks* complex). State this when you report. For cross-person comparison, use the **same measurement** (some exports lack a sub-agent signal — in that case, don't trigger on sub-agents for anyone).
- **Outcome (sampled).** Acceptance (`yes`) / abandoned (`no`) / unmeasurable (`domain_lacks_signature`). Only exists on **scored** tasks; chat tasks have no outcome.
- **The cross-product.** Difficulty × outcome shows **where a person drops the ball:** hard tasks abandoned = a closure weakness; easy tasks abandoned = not caring about small work; everything verified = strong closer. Draw a small simple/complex × accepted/abandoned/unmeasurable table on the card. **Join on `task_id`** — the workflow's `raw_tasks` must carry `task_id`, and the renderer looks up difficulty via the per-task trajectory file (configurable path, e.g. `<compact_dir>/t/<task_id>.txt`).
- **Time dimension (throughput).** Use **real timestamps** to compute date window + active days + count/week. Timestamp sources vary by tool: some have them in the message or path; some agent-transcript exports **strip the timestamps during anonymization** (then you can only count, not compute a rate); some exports put the time in the **filename** (e.g. `date_time_uuid`). **If there's no timestamp, honestly write "rate pending" — don't pass file-mtime off as real working time** (unless you've confirmed mtime wasn't reset by a copy).
- **HR / advisory domains.** Outcomes here are mostly "unmeasurable" (no run signature) — label that honestly, don't force a fake accepted/abandoned.
- **Honesty.** Difficulty = full-population structured; outcome = sampled; time = only when timestamps exist. The three use different measurement bases — label each one's source on the card.

## Card Output Format (plain language, per-task evidence)

**Each dimension = one self-justifying argument**, in this fixed order:

1. **Why → standard.** One causal sentence: *"Because the AI [does X], you have to [do Y] in order to [achieve Z]."*
2. **Count.** Across n tasks, did it X times / failed to Y times. (Plain numbers.)
3. **Best / worst.** One real high and one real low, **each with a verbatim quote that's traceable on click.**
4. **Pattern.** Under what conditions you *can* and *can't* do it. (This is the most valuable line.)
5. **Linkage.** Which dimensions share a root with this one — collapse them into one **signature** sentence.
6. **So.** Next step (how to fix a weakness / how to take a strength up another level).

**Top of the card:** a one-line profile + **"your signature"** (2–3 cross-dimension patterns) + the two axes (capability + leverage) + the reality-gate + Top 3.

**Iron rules:** plain language (no machine atom-names / abbreviations / percentile-as-a-word; plain numbers are fine), don't manufacture weaknesses to balance out strengths (honor the attribution law), quotes must be traceable, don't force cross-domain comparisons.

## Honesty / Limitations (must be delivered alongside the result)

- **Tiers, not ranks.** A 0.1 difference between adjacent people is noise — it's only good enough to bucket into strong / middle / weak tiers.
- **No cross-domain comparison.** A backend engineer "running tests" is not the same as a data/HR person "human review / sign-off." Rank within the same role and domain.
- **Underpowered when there are no low-proficiency samples.** Everyone clusters in the upper-middle band and the separation won't emerge — add weak samples, and the gate's multiplier will pull the weak ones apart.
- **Residual subjectivity.** The 0–4 scores are judged by an LLM. For pay-grade objectivity, add an **inter-rater consistency check** (two readers scoring the same batch of tasks). **Reflexivity inside the gate is both load-bearing and the most subjective** — before money changes hands, hand-audit the handful of tasks that scored low on it and confirm it's genuine "didn't self-check," not scoring noise.
- **Value judgment ≠ regression.** Anchoring the gate on "rigor behavior" is a **claim** (we believe rigor matters most) — we deliberately *don't* anchor on landed outcomes (to avoid domain bias). It is *not* a statistically-fit weight. Say so plainly.
- **Leverage needs more data.** Coverage (count) and speed (throughput) are **auto-computed** from the compact's stats (session count + difficulty tiers + real date window + count/week; missing timestamps → "rate pending"). Only **impact (the link to business outcomes) is still pending data.**

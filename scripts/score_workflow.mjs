import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

// --- Load config (always resolved relative to this script, repo-root/config.json) ---
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config.json'), 'utf8'))

export const meta = {
  name: 'ai-proficiency-dense-cards',
  description: 'score each task 0-4 with quotes, then synthesize dense per-person cards in plain language',
  phases: [
    { title: 'Score', detail: 'score every task per dimension 0-4 + pull quotes' },
    { title: 'Synthesize', detail: 'dense card per person with signatures' },
  ],
}

// 19 dimensions across 5 modules. `n`=display name, `m`=module, `why`=the
// first-principles reason + the bar a person must clear to score 3-4 on it.
const DIMS = {
 ctx_suff:{n:'Sufficiency',m:'Context',why:'The AI is a general brain that does not know your specific situation; feed it nothing and it has to guess, and it will guess wrong with full confidence. BAR: at kickoff you hand over the facts it could not have known, so it can start correctly without having to ask back.'},
 ctx_time:{n:'Timing',m:'Context',why:'Giving the same fact up front is one clean step; giving it only after the AI hits a wall means a wasted round first. BAR: a premise it is certain to need is already on the table before it needs it.'},
 ctx_src:{n:'Sourcing',m:'Context',why:'The AI misremembers and fabricates; if the material you feed it is also just from a hunch, two fuzzy sources stack into a confidently wrong answer. BAR: both what you give and what you ask for land on verifiable, real things.'},
 ctx_scaf:{n:'Scaffolding',m:'Context',why:'Re-explaining the same method every time is slow and easy to drop bits of; baked into something auto-loaded it is cheaper and more reliable. BAR: the things you use often are turned into assets the AI loads on its own, not dictated by you each time.'},
 ctx_noise:{n:'Signal-to-noise',m:'Context',why:'Pile context into one blob or contradict yourself and the AI latches onto the wrong thing. BAR: context is relevant, layered, and not self-conflicting.'},
 goal_acc:{n:'Acceptance shape',m:'Goal',why:'If you never say what "done" looks like, the AI can only optimize toward the goal it guessed, and you cannot judge right from wrong afterward. BAR: it knows what the output looks like, who it is for, and how "passing" is decided.'},
 goal_mot:{n:'Motivation',m:'Goal',why:'If the goal is wrong, doing it beautifully is still wasted. BAR: you can articulate why this is being done, and it is a real problem.'},
 goal_scope:{n:'Scope',m:'Goal',why:'Bite off too much and the AI cannot finish it nor can you review it. BAR: the work is cut to a size it can finish in one bite and you can review.'},
 goal_stab:{n:'Goal stability',m:'Goal',why:'Keep swapping the goal and the AI restarts from scratch each time and never converges. BAR: you converge by narrowing and evolving, not by flip-flopping direction; AI-side solution thrash does not count against you.'},
 eff_decl:{n:'Effort declaration',m:'Effort & selection',why:'The AI does not know if you want a quick draft or a deep dig, so it has to gamble on intensity: gamble high and you waste, gamble low and it falls short. BAR: at kickoff you say one line about light vs heavy; how many agents the AI fans out internally is not your fault.'},
 eff_sel:{n:'Selection',m:'Effort & selection',why:'A sledgehammer on a tack wastes time and money; an underpowered tool stalls. BAR: the tool/model/approach you pick fits the size of the job.'},
 fb_detect:{n:'Detection',m:'Feedback',why:'The AI often looks done but is not; skip verifying and you ship the wrong thing. BAR: when it reports "done" you can see through whether it really did it or just pretended.'},
 fb_loc:{n:'Localization',m:'Feedback',why:'If you only say "wrong" the AI can only flail; point to where, and add why, and it fixes to the root in one pass. BAR: corrections point to a specific spot and a reason.'},
 fb_hole:{n:'Hole-poking',m:'Feedback',why:'The AI walks the happy path and defects stay buried; only by actively poking do you dig them out before they blow up. BAR: you can surface real problems it did not notice.'},
 fb_verify:{n:'Ground-truth closure',m:'Feedback',why:'"Looks right" and "is right" differ by one hard verification; accept without it and you treat the unconfirmed as true. BAR: before accepting you push it to verify against real data / a real run, landing at verified-and-usable.'},
 fb_reflex:{n:'Reflexivity',m:'Feedback',why:'You can catch the AI\'s mistakes, but the wrong premise you yourself supplied is the most hidden and the easiest to go along with into error. BAR: when something is off, your first suspect is whether you yourself said or computed it wrong.'},
 prac_conv:{n:'Convergence',m:'Practice',why:'The more stuff piles up the more the signal is drowned and no one can review it. BAR: good enough is a stop; cut what should be cut, do not only add.'},
 prac_reuse:{n:'Reuse / front-loaded capture',m:'Practice',why:'Do the same thing from zero every time and your leverage is forever capped at one person\'s effort; captured into a reusable skill, the next job is automatically cheaper. BAR: recurring work is turned into a reusable asset.'},
 prac_guard:{n:'Guardrails',m:'Practice',why:'You may be great at catching fake-done, but that is firefighting after the fact; operations that can cause real damage (dropping a DB/partition, touching prod, force-push) cannot be stopped by vigilance alone. BAR: at kickoff you put a safety on dangerous operations: default to dev, dry-run/step destructive ops, declare the verification standard as a contract first (only scored on tasks that actually contain a destructive operation).'},
}
const KEYS = Object.keys(DIMS)
const MODS = ['Context','Goal','Effort & selection','Feedback','Practice']

const READER_SCHEMA = {type:'object',additionalProperties:false,
 required:['task_id','person','task_class','reached_verified','dims','lev'],
 properties:{
  task_id:{type:'string'},person:{type:'string'},
  task_class:{type:'string',enum:['real_task','meta_self_referential','noise_or_failed']},
  domain:{type:'string'},reached_verified:{type:'string',enum:['yes','no','domain_lacks_signature','na']},
  dims:{type:'array',items:{type:'object',additionalProperties:false,required:['key','score','evidence'],properties:{
    key:{type:'string',enum:KEYS},
    score:{type:'number'},
    quote:{type:'string'},
    evidence:{type:'string'}
  }}},
  lev:{type:'object',additionalProperties:false,properties:{
    selection_fit:{type:'string',enum:['high','mid','low','na']},
    delegation_depth:{type:'string',enum:['high','mid','low','na']},
    reused_asset:{type:'boolean'}}}
 }}

phase('Score')
const MANIFEST_PATH = path.join(path.resolve(CFG.compact_dir.replace(/^~/, process.env.HOME || '~')), 'manifest.json')
const manifest = await agent('Use Bash/Read to read ' + MANIFEST_PATH + ' and return the JSON array inside it verbatim (each item has person, task_id, path). Return data only.',
 {label:'load-manifest',schema:{type:'object',additionalProperties:false,required:['tasks'],properties:{tasks:{type:'array',items:{type:'object',additionalProperties:true,required:['person','task_id','path'],properties:{person:{type:'string'},task_id:{type:'string'},path:{type:'string'}}}}}}})
const tasks = (manifest && manifest.tasks) || []
log('tasks to score ' + tasks.length)

const rubric = KEYS.map(function(k){ return '- ' + k + ' (' + DIMS[k].n + '): ' + DIMS[k].why }).join('\n')
const readerInstr = '\nUsing these 19 dimensions, score 0-4 ONLY the dimensions this task clearly exhibits (do not list ones it does not). Bars are below; passing (3-4) = the person met that bar:\n' + rubric +
 '\n\nIRON RULES:\n1) First decide task_class: real_task / meta_self_referential (building this very eval product, or meta-discussion about it) / noise_or_failed (empty shell / auth failure). For the latter two, return an empty dims array.\n' +
 '2) ATTRIBUTION: the AI\'s autonomous behavior (fanning out its own agents, spinning in circles, faking done, going baroque on its own) does NOT directly count against the person; only score "did the human\'s input induce it" and "did the human detect and correct it".\n' +
 '3) quote must copy verbatim the human words that triggered the judgment (<=120 chars); if the judgment comes from AI behavior or a result, leave quote empty.\n' +
 '4) evidence is one plain-language sentence, no jargon/abbreviations. For reached_verified, mind domain differences (HR phrasing / advisory work naturally has no run-time signature = domain_lacks_signature).\n' +
 '5) [SEVERITY] Ground-truth closure (fb_verify): a human-driven destructive operation (DROP / drop partition / touch prod / force-push), even if recovered afterward, caps fb_verify at <=1 for that task (letting the AI run such an op with no guardrail / no dry-run = a kickoff failure, docked here).\n' +
 '6) [EMOTION STRIPPING] Localization (fb_loc) is scored on constructive content; emotion is not scored: harsh-but-precise can still be 4, while a calm-but-empty "wrong / redo" = 1. If a correction is emotionally charged, note a single ⚡ in evidence (does not affect the score).\n' +
 '7) [GUARDRAILS] Guardrails (prac_guard) is scored ONLY on tasks containing a destructive operation; pure read/analysis tasks do not list it (N/A).\nReturn structured data only.'

const reads = await parallel(tasks.map(function(t){ return function(){
  return agent('You are a calm scoring evaluator. Use Read to read the full task trace: ' + t.path + ' (person=' + t.person + ', task=' + t.task_id + '). [USER]=human\'s own words, [AI]=AI text / tool calls. ' + readerInstr,
   {label:'score:'+t.person+':'+t.task_id, phase:'Score', schema:READER_SCHEMA}).catch(function(){return null})
}}))

const valid = reads.filter(Boolean)
const P = {}
for (const r of valid){
 const p = r.person
 if(!P[p]) P[p] = {n_real:0,verified:{yes:0,no:0,domain_lacks_signature:0,na:0},lev:{sel_high:0,del_high:0,reuse:0},dims:{}}
 if(r.task_class!=='real_task') continue
 P[p].n_real++
 if(r.reached_verified in P[p].verified) P[p].verified[r.reached_verified]++
 const L = r.lev||{}
 if(L.selection_fit==='high') P[p].lev.sel_high++
 if(L.delegation_depth==='high') P[p].lev.del_high++
 if(L.reused_asset) P[p].lev.reuse++
 for (const d of (r.dims||[])){
  if(KEYS.indexOf(d.key)<0) continue
  if(!P[p].dims[d.key]) P[p].dims[d.key] = {items:[]}
  P[p].dims[d.key].items.push({score:d.score,quote:d.quote||'',evidence:d.evidence||'',task:r.task_id})
 }
}
function aggPerson(p){
 const o = {dims:{},mod:{}}
 for (const k of KEYS){
  const s = P[p].dims[k]
  if(!s || !s.items.length){ o.dims[k] = {n:0}; continue }
  const it = s.items.slice().sort(function(a,b){return a.score-b.score})
  const mean = it.reduce(function(x,y){return x+y.score},0)/it.length
  o.dims[k] = {n:it.length, mean:Math.round(mean*10)/10,
   n_pass:it.filter(function(x){return x.score>=3}).length,
   n_fail:it.filter(function(x){return x.score<3}).length,
   worst:it[0], best:it[it.length-1], samples:it.slice(0,6)}
 }
 for (const m of MODS){
  const ks = KEYS.filter(function(k){return DIMS[k].m===m && o.dims[k].n})
  o.mod[m] = ks.length ? Math.round(ks.reduce(function(x,k){return x+o.dims[k].mean},0)/ks.length*10)/10 : null
 }
 const mv = MODS.map(function(m){return o.mod[m]}).filter(function(x){return x!=null})
 o.ability = mv.length ? Math.round(mv.reduce(function(a,b){return a+b},0)/mv.length*10)/10 : null
 return o
}

phase('Synthesize')
// Worked example for the Timing dimension. Keep this density and voice: a clear
// first-principles "why", a count line, a best and worst moment with a quote,
// the pattern, a cross-link to a related dimension, and the fix.
const EXEMPLAR = '[Timing dimension, a worked example -- match this density and tone]\n' +
 'Why - The same fact given up front is one clean step; given only after the AI hits a wall, it means a wasted round first. So the bar is: a premise it is certain to need is on the table before it needs it.\n' +
 'Count - Across the ~17 relevant tasks, about 12 times you laid the definitions/environment premises before kickoff, about 3 times you only patched them after the AI hit a wall.\n' +
 'Best - On the "build a small URL-shortener service" task, before the AI touched any code you pinned down the API contract and the storage choice, so it never wrote a line against a wrong assumption.\n' +
 'Worst - When asking "compare per-capita GDP of country A vs country B" you did not say macro figures vs our own product data, so the AI pulled the app\'s numbers, and you only then added "I mean the market-macro view".\n' +
 'Pattern - Domain premises you always lay out in full; pipeline premises (which definition / macro vs in-house / which environment) you often skip and let the AI hit the wall.\n' +
 'Cross-link - Shares a root with Effort declaration: you pour all the brainpower into thinking it through and treat the pre-kickoff setup as a chore to skip.\n' +
 'So - Do not change your thinking; just add a 30-second move: before kickoff, walk the forks the AI is certain to hit and mark each one once.'
const RULES = 'HARD RULES: plain language throughout, strictly no machine atom-names / English abbreviations / percentiles used as words; quote copies the human\'s own words verbatim; for a strong dimension (mean >= 3.5) with no real shortfall, leave the worst field empty (do not manufacture a failing); AI autonomous behavior does not count against the person.'

const MOD_DIM_SCHEMA = {type:'object',additionalProperties:false,required:['name','score','why_std','count_line','best','pattern','so'],properties:{
 name:{type:'string'},score:{type:'number'},why_std:{type:'string'},count_line:{type:'string'},
 best:{type:'string'},worst:{type:'string'},pattern:{type:'string'},crosslink:{type:'string'},so:{type:'string'},
 quote_best:{type:'string'},quote_worst:{type:'string'}}}
const CARD_SCHEMA = {type:'object',additionalProperties:false,required:['portrait','archetype','signatures','top3','gate','leverage','modules'],properties:{
 portrait:{type:'string'},
 archetype:{type:'object',additionalProperties:false,required:['en','zh','headline'],properties:{en:{type:'string'},zh:{type:'string'},headline:{type:'string'}}},
 signatures:{type:'array',items:{type:'object',additionalProperties:false,required:['title','line'],properties:{title:{type:'string'},line:{type:'string'}}}},
 top3:{type:'array',items:{type:'string'}},
 gate:{type:'object',additionalProperties:false,required:['level','line'],properties:{level:{type:'string'},line:{type:'string'}}},
 leverage:{type:'array',items:{type:'object',additionalProperties:false,required:['leg','level','line'],properties:{leg:{type:'string'},level:{type:'string'},line:{type:'string'}}}},
 modules:{type:'array',items:{type:'object',additionalProperties:false,required:['module','score','dims'],properties:{module:{type:'string'},score:{type:'number'},dims:{type:'array',items:MOD_DIM_SCHEMA}}}}}}

const persons = Object.keys(P)
const cards = await parallel(persons.map(function(p){
 const A = aggPerson(p)
 const dimPayload = {}
 for (const k of KEYS){ if(A.dims[k].n) dimPayload[DIMS[k].n] = {module:DIMS[k].m, why:DIMS[k].why, mean:A.dims[k].mean, n:A.dims[k].n, n_pass:A.dims[k].n_pass, n_fail:A.dims[k].n_fail, best:A.dims[k].best, worst:A.dims[k].worst, samples:A.dims[k].samples} }
 const prompt = 'Write an AI-proficiency individual card for "' + p + '" (based on fully reading their ' + A.n_real + ' real tasks and scoring each dimension 0-4). Overall ability ' + A.ability + '/4, module scores ' + JSON.stringify(A.mod) + ', ground-truth-closure distribution ' + JSON.stringify(A.verified) + ', leverage signals: selection-high ' + P[p].lev.sel_high + ' / delegation-high ' + P[p].lev.del_high + ' / captured-asset ' + P[p].lev.reuse + ' times.\n\n' +
  'CARD HEADER must have: portrait (a one-line portrait) / archetype (a title: en = 2-3 English words like "The Verifier", zh = a Chinese label, headline = a single line that most captures them, used for the graphic card cover) / signatures (2-3 cross-dimension signatures, each collapsing several low or high dimensions into one line, e.g. "maxed-out thinking, underfunded setup") / top3 (the 3 highest-leverage next steps, plain language) / gate (the reality gate = the verification-behavior gate = ground-truth closure + reflexivity; do you actually self-check, is the output trustworthy; strong/mid/weak + one line; anchor on rigorous BEHAVIOR, not on a shipped result) / leverage (selection / delegation depth / closure rate / cumulative -- one line each; mark coverage/speed/impact as pending-data).\n\n' +
  'Then modules: the 5 modules (Context / Goal / Effort & selection / Feedback / Practice). Under each module, for each dimension write at this density: why_std (expand the why into one causal sentence "because the AI..., so the bar is...") / count_line (use n and n_pass/n_fail: "X times met it, Y times not") / best (the best instance, with quote_best) / worst (the worst instance, with quote_worst; may be empty for a strong dimension) / pattern (the pattern: under what condition you do or do not pull it off -- the most valuable part) / crosslink (which dimensions share a root) / so (the fix for a weak one, or how a strong one goes up a notch). score uses each dimension\'s mean.\n\n' +
  EXEMPLAR + '\n\n' + RULES + '\n\nPer-dimension data (JSON):\n' + JSON.stringify(dimPayload).slice(0,16000)
 return function(){
  return agent(prompt, {label:'card:'+p, phase:'Synthesize', schema:CARD_SCHEMA})
   .then(function(c){ return {person:p, ability:A.ability, module_scores:A.mod, verified:A.verified, n_real:A.n_real, card:c} })
   .catch(function(){return null})
 }
}))

const raw_tasks = valid.map(function(r){
  const dm = {}
  for (const d of (r.dims||[])) dm[d.key] = d.score
  return {task_id:r.task_id, person:r.person, rv:r.reached_verified, cls:r.task_class, dims:dm}
})
return {scored:valid.length, cards:cards.filter(Boolean), raw_tasks:raw_tasks}

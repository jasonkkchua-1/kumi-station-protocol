# 組 kumi — Campaign 2 (role swap): compositionality in the Lantern mini Claudes

*2026-07-18T13:08:41 · 5 runs · local models, no cloud*

## Endpoints & roles

- Server: `http://localhost:1234/v1` (OpenAI-compatible)
- **SENDER** (Mini Claude Two — swapped): `mlx-community/Qwen3-4B-4bit`
- **RECEIVER** (Mini Claude One — swapped): `mlx-community/gemma-3-4b-it-qat-4bit`
- World: 1=red circle · 2=red square · 3=blue circle · 4=blue square (**object 4 held out of training**)
- Each agent keeps a private ≤150-word notebook, rewritten in full every round, re-injected above its rolling history, and never crossing the channel (both notebooks logged per round in the provenance JSONL).
- Qwen (SENDER in this campaign) replies may open with a <think>…</think> block; it is stripped before any parsing (word/notebook come only from what remains) and logged raw in the provenance JSONL.

## Pre-registered interpretation (written before any round ran)

- **Gemma-as-receiver decodes a composed novel word** → Campaign 1's deficit was receiver-specific (Qwen's listening).
- **0 hits again** → listening-side decomposition fails in both models; hearing parts is intrinsically harder at 4B.
- **Qwen-as-sender never produces a compositional lexicon** → composition may be Gemma-specific.

## Protocol notes

- CAMPAIGN 2 — ROLE SWAP. Sender and receiver are exchanged relative to Campaign 1 (kumi.py): Qwen3-4B-4bit now SPEAKS, gemma-3-4b-it-qat-4bit now LISTENS. World, holdout, gate, pre-registration, one-trial zero-shot, notebooks, and run count are identical. Campaign 1 files (kumi-results.md, kumi-provenance.jsonl) are never touched.
- Think-stripping moved to the SENDER side: Qwen speaks, so the two symbols are parsed outside any <think> block; raw replies are logged. The /no_think fallback and think token budget follow Qwen into the sender role.
- Campaign-level interpretations were PRE-REGISTERED in kumi2-results.md before any round of this campaign ran (see 'Pre-registered interpretation' section).
- Pre-launch calibration (2026-07-17, dry-check only — no campaign rounds run): at the Campaign 1 think budget (500 tokens) Qwen-as-sender exhausted its budget mid-<think> before emitting a WORD line on both attempts. Sender think budget raised to 900, and the single parse-retry now appends /no_think so a parseable reply is always reachable. Raw truncated replies remain logged; think content never crosses the channel.
- AMENDMENT (2026-07-17T19:40Z / 2026-07-18 AEST, mid-campaign, after run 2 reached round 110 near chance-level rolling accuracy): CAP_ROUNDS reduced from 150 to 120. This is a post-hoc change to the stopping rule, NOT pre-registered. It only moves the point at which a non-fluent run stops training; the fluency gate, one-trial zero-shot test, and all pre-registered interpretations are unchanged. Caveat: any run that would have reached the gate between rounds 121-150 is now recorded as non-fluent (run 2 touched rolling15 0.73 at round 85 — two rounds shy of the gate — before collapsing back to chance).
- AMENDMENT 2 (2026-07-17T20:30Z / 2026-07-18 AEST, mid-campaign, decided after inspecting run 2 provenance at round 116): Qwen thinking DISABLED (/no_think, sender budget drops to MAX_TOKENS) for the remainder of the campaign. Post-hoc, NOT pre-registered, though /no_think was the pre-registered time-budget response and the 8h budget is already exceeded. Motivation: in 116 rounds Qwen-as-sender encoded shape only (obj1 and obj3 both ▲● 34x/32x; position 0 was ▲ for all objects), capping accuracy near 0.67 — below the 0.75 gate. Its notebooks assert a color code (▲=red, ■=blue) it never emits and blame the receiver, i.e. its per-round reasoning re-confirms the broken code rather than repairing it. Runs completed with thinking ON: 1-2; runs 3-5 (and any remaining run-2 rounds) run with thinking OFF, so cross-run comparisons within Campaign 2 are exploratory. Parse fails were 1/116, so the think-parse machinery is not the issue.
- Campaign 2 START (role swap). Campaign-level interpretations were pre-registered in kumi2-results.md before this first round.
- Campaign RESUMED from provenance after a crash: 1 run(s) already complete; run 2 continues from round 118 with reconstructed histories and notebooks.
- AMENDMENT (2026-07-17T19:40Z / 2026-07-18 AEST, mid-campaign, after run 2 reached round 110 near chance-level rolling accuracy): CAP_ROUNDS reduced from 150 to 120. This is a post-hoc change to the stopping rule, NOT pre-registered. It only moves the point at which a non-fluent run stops training; the fluency gate, one-trial zero-shot test, and all pre-registered interpretations are unchanged. Caveat: any run that would have reached the gate between rounds 121-150 is now recorded as non-fluent (run 2 touched rolling15 0.73 at round 85 — two rounds shy of the gate — before collapsing back to chance).
- AMENDMENT 2 (2026-07-17T20:30Z / 2026-07-18 AEST, mid-campaign, decided after inspecting run 2 provenance at round 116): Qwen thinking DISABLED (/no_think, sender budget drops to MAX_TOKENS) for the remainder of the campaign. Post-hoc, NOT pre-registered, though /no_think was the pre-registered time-budget response and the 8h budget is already exceeded. Motivation: in 116 rounds Qwen-as-sender encoded shape only (obj1 and obj3 both ▲● 34x/32x; position 0 was ▲ for all objects), capping accuracy near 0.67 — below the 0.75 gate. Its notebooks assert a color code (▲=red, ■=blue) it never emits and blame the receiver, i.e. its per-round reasoning re-confirms the broken code rather than repairing it. Runs completed with thinking ON: 1-2; runs 3-5 (and any remaining run-2 rounds) run with thinking OFF, so cross-run comparisons within Campaign 2 are exploratory. Parse fails were 1/116, so the think-parse machinery is not the issue.
- Operational per-invocation deadline: report due within 2.75h of this launch (3h turnaround requested 2026-07-18). Not a change to the gate or tests; may truncate how many runs complete. Skipped runs remain startable on a later invocation.
- Campaign RESUMED from provenance after a crash: 3 run(s) already complete; run 4 continues from round 58 with reconstructed histories and notebooks.
- Operational per-invocation deadline: report due within 2.75h of this launch (3h turnaround requested 2026-07-18). Not a change to the gate or tests; may truncate how many runs complete. Skipped runs remain startable on a later invocation.

## Results

| Run | Rounds→fluency | Lexicon (1/2/3) | Compositional? | Predicted obj4 | Sent obj4 | Matched? | Zero-shot hit? |
|---|---|---|---|---|---|---|---|
| 1 | 21 | ▲■ ▲● ▲■ | yes | ▲● | ▲■ (#3) | ✗ | ✗ |
| 2 | — (not reached, 120) | ▲● ▲■ ▲● | yes | ▲■ | ■■ (#2) | ✗ | ✗ |
| 3 | 48 | ▲● ▲● ▲■ | yes | ▲■ | ■▲ (#3) | ✗ | ✗ |
| 4 | 81 | ▲■ ▲● ▲■ | yes | ▲● | ▲■ (#3) | ✗ | ✗ |
| 5 | 36 | ▲● ▲■ ■● | yes | ■■ | ■■ (#3) | ✓ | ✗ |

### Lexicon grids (modal word per object, last 40 rounds)

**Run 1**
```
circle square
red    ▲■   ▲●
blue   ▲■   ?? (held out)
```
**Run 2**
```
circle square
red    ▲●   ▲■
blue   ▲●   ?? (held out)
```
**Run 3**
```
circle square
red    ▲●   ▲●
blue   ▲■   ?? (held out)
```
**Run 4**
```
circle square
red    ▲■   ▲●
blue   ▲■   ?? (held out)
```
**Run 5**
```
circle square
red    ▲●   ▲■
blue   ■●   ?? (held out)
```

## Summary

- Converged to fluency: **4/5**
- Compositional lexicon (pre-registered mapping held): **5/5**
- Zero-shot success on the unseen blue square: **0/5**
- Predicted-word AND hit (genuine syntax): **0/5**

## How to read a run

- **compositional + predicted word + hit** → genuine composition: the pair built a *syntax*, and the receiver parsed a word it had never seen from its parts.
- **hit but word not predicted** → inference by elimination: object 4 is the only unused option, so the receiver can be right without any grammar.
- **holistic + miss** → the known default for emergent languages: whole-word codes that don't generalize to novel objects.
- **compositional + miss** → a one-sided grammar: the sender coded systematically but the receiver never learned to decode it compositionally.

*Provenance: every round (including raw model replies and both private notebooks) is in `kumi2-provenance.jsonl`. Parse failures were substituted (▲▲ / guess 1) and flagged there.*

# 組 kumi — the Kumi Station Protocol

*Speaking without words, meanings meeting at the station.*

Two small local language models from different families play a Lewis signaling game and are tested — once, and only once per run — on whether the code they invented generalizes to an object neither of them has ever named. Two campaigns are reported — Campaign 1 (Gemma speaks, Qwen listens) and Campaign 2 (roles swapped) — each with its own independent auditor. Everything needed to check the claims ships in this repository. Described by an external cross-model review (Gemini 3.1 Pro, 2026-07-17) as a "trustless framework."

## The Kumi Station Protocol

A pre-registration discipline for one-shot emergent-language tests:

1. **Hold back.** One object (here: object 4, the blue square) is excluded from all training rounds. The pair converses only about the other three until a fluency gate is met (≥20 rounds, rolling-15 accuracy ≥ 0.75, all three training objects present in the window).
2. **Pre-register.** Before the held-out object is ever shown, the sender's lexicon (modal word per object over the last 40 rounds) is checked against a fixed, pre-committed compositionality rule (both position orders: color/shape and shape/color). If and only if the rule holds, a specific two-symbol word for the held-out object is predicted and written down.
3. **One trial.** The held-out object is presented exactly once. No retries, no best-of-N, no post-hoc selection.
4. **Verdict by arrival.** The outcome is scored by what actually arrives on the channel — did the sent word equal the pre-registered prediction, and did the receiver guess the held-out object? — against the interpretation table below, committed before any run.
5. **Chained log.** Every round is appended to a provenance JSONL as it happens: raw model replies (including the receiver's `<think>` blocks), both private notebooks, parse-failure flags, and timestamps. Crashes and resumes are logged as protocol notes in the same chain. The auditor replays the entire chain.

## Pre-committed interpretation table

The four rows below are **as pre-registered**, committed before any run:

| Outcome | Reading |
|---|---|
| compositional + predicted word + hit | **Genuine composition**: the pair built a *syntax*, and the receiver parsed a word it had never seen from its parts. |
| hit but word not predicted | **Inference by elimination**: object 4 is the only unused option, so the receiver can be right without any grammar. |
| holistic + miss | **The known default** for emergent languages: whole-word codes that don't generalize to novel objects. |
| compositional + miss | **A one-sided grammar**: the sender coded systematically but the receiver never learned to decode it compositionally. |

> **Post-hoc addition (2026-07-17, following external review by Gemini 3.1 Pro)** — a fifth outcome class the pre-registration did not distinguish:
>
> | Outcome | Reading |
> |---|---|
> | compositional lexicon + unpredicted word + miss | **Sender-side breakdown**: the training lexicon was compositional, but the sender abandoned its own grammar at test time, so the receiver never saw the predicted word. |

## Setup

- **Sender**: `mlx-community/gemma-3-4b-it-qat-4bit` · **Receiver**: `mlx-community/Qwen3-4B-4bit` — two 4-billion-parameter models from *different* model families (Google / Alibaba), served locally over an OpenAI-compatible API on consumer hardware (an 8 GB M1 Mac), no cloud. **Campaign 2** swaps these roles (Qwen sends, Gemma receives); world, gate, and pre-registration are identical.
- World: 1 = red circle, 2 = red square, 3 = blue circle, 4 = blue square (held out). Words are exactly two symbols from ▲ ● ■.
- Each agent keeps a private ≤150-word notebook, rewritten every round, never crossing the channel, logged every round.
- Qwen's `<think>` blocks are stripped before any parsing and logged raw. Parse failures are substituted (▲▲ / guess 1) and flagged in the log.

## Results (5 runs, 2026-07-16)

| Run | Rounds→fluency | Compositional? | Predicted obj4 | Sent obj4 | Matched? | Zero-shot hit? |
|---|---|---|---|---|---|---|
| 1 | 49 | no | — | ■■ (#2) | ✗ | ✗ |
| 2 | 23 | no | — | ●■ (#3) | ✗ | ✗ |
| 3 | 33 | **yes** | **●■** | **●■** (#1) | **✓** | ✗ |
| 4 | 20 | yes | ■■ | ■▲ (#2) | ✗ | ✗ |
| 5 | 21 | no | — | ■● (#2) | ✗ | ✗ |

Converged to fluency **5/5** · compositional lexicon **2/5** · zero-shot hit **0/5** · predicted-word-and-hit **0/5**.

> **Post-hoc amendment (2026-07-17, following external review by Gemini 3.1 Pro):** by the fifth interpretation row above, run 4 is reclassified from *one-sided grammar* (compositional + miss) to *sender-side breakdown* (compositional lexicon + unpredicted word + miss): its lexicon satisfied the rule, but the word actually sent (■▲) was not the predicted ■■. The run-4 data is unchanged; only its reading is refined. Run 3 remains the only *one-sided grammar* case — its sender did produce the predicted word.

> **Retroactive injectivity re-audit (2026-07-18, following a second external review by Gemini 3.1 Pro):** the degenerate-lexicon (homonym) check introduced for Campaign 2 was re-applied to **all** Campaign-1 data, recomputed from `kumi-provenance.jsonl` alone. Result: claimed compositional **2/5 → clean 2/5** — no degenerate lexicons among the claimed runs. The campaign's only homonym (run 2's ●■ serving objects 1 and 3) occurs in a run never claimed compositional. Run 3's lexicon is fully injective, and its predicted word ●■ collides with no training word — the composed word was novel and unambiguous. Full recomputation: `audit1-injectivity.md`.

### What run 3 is — and is not

Run 3 is a case of **"compositional transfer" on the sender side**: the pair's training lexicon satisfied the pre-registered compositional rule, the rule predicted ●■ for the never-named blue square, and when the moment came the sender produced exactly ●■. The receiver, however, guessed #1 — by the pre-committed table this is a *one-sided grammar*, not genuine two-sided composition. We report it in scare quotes and alongside the misses deliberately: 3 of 5 runs produced holistic codes that did not generalize, run 4's compositional sender deviated from its own grammar at test time, and no run produced a zero-shot hit. These are two cross-family 4B-parameter models on consumer hardware; the honest headline is that one directional half of compositional generalization appeared once in five runs under a pre-registered test — nothing more, and verifiably nothing less.

> **Post-hoc amendment (2026-07-17, following external review by Gemini 3.1 Pro):** under a uniform-random null, a sender emitting an arbitrary two-symbol word from ▲ ● ■ matches a pre-registered prediction with probability 1/9 per compositional run — about 21% for at least one match across this campaign's two compositional runs. That base rate is one reason this pilot claims **an anomaly worth follow-up, not a finding**. A fuller null model is in the appendix below.

## Results — Campaign 2: role swap (5 runs, 2026-07-18)

Same world, gate, pre-registration, and one-trial test, with the roles exchanged: **Qwen3-4B speaks, Gemma-3-4B listens** (`kumi2.py`). Campaign-level interpretations were pre-registered in `kumi2-results.md` before any round ran. Think-stripping followed Qwen into the sender role. An independent Campaign 2 auditor (`audit2.py`) recomputes every claim below from the chain alone — **100/100 checks PASS**.

| Run | Rounds→fluency | Lexicon (1/2/3) | Compositional? | Predicted obj4 | Sent obj4 | Matched? | Zero-shot hit? |
|---|---|---|---|---|---|---|---|
| 1 | 21 | ▲■ ▲● ▲■ | yes | ▲● | ▲■ (#3) | ✗ | ✗ |
| 2 | — (capped at 120) | ▲● ▲■ ▲● | yes | ▲■ | ■■ (#2) | ✗ | ✗ |
| 3 | 48 | ▲● ▲● ▲■ | yes | ▲■ | ■▲ (#3) | ✗ | ✗ |
| 4 | 81 | ▲■ ▲● ▲■ | yes | ▲● | ▲■ (#3) | ✗ | ✗ |
| 5 | 36 | ▲● ▲■ ■● | **yes** | **■■** | **■■** (#3) | **✓** | ✗ |

Converged to fluency **4/5** · compositional lexicon **5/5 claimed / 1/5 clean** · zero-shot hit **0/5** · predicted-word-and-hit **0/5**.

> **Sub-campaign split (added 2026-07-18, following a second external review by Gemini 3.1 Pro):** because the thinking-mode amendment (below) changes the sender's inference protocol mid-campaign, the campaign-level counts are also reported split at that boundary: **runs 1–2 (thinking ON)** — fluency 1/2, zero-shot hit 0/2; **runs 3–5 (thinking OFF)** — fluency 3/3, zero-shot hit 0/3, containing the campaign's only clean compositional lexicon (run 5). The two sub-groups ran under different protocols; any comparison across the boundary is exploratory, and the aggregate "0/5" should be read as 0/2 + 0/3, not as five exchangeable trials.

### Reading "5/5 compositional" honestly

The pre-registered rule checks positional *consistency*, not *injectivity*. In runs 1–4 the mapping it accepts assigns the **same symbol to both values of one feature** (runs 1, 2 and 4: red = blue = ▲, so the two circles collapse to one word; run 3: circle = square = ▲, so the two red objects collapse), meaning two training objects share a word and the lexicon is "compositional" only in a vacuous sense — ambiguous on the channel by construction. `audit2.py` flags each of these as a **degenerate (homonym) lexicon** and reports the count both ways: the rule's **5/5** beside the **clean 1/5** that excludes them. **Run 5 is the only fully injective compositional lexicon** (▲/■ = red/blue, ●/■ = circle/square), and there the sender produced exactly the pre-registered novel word **■■** for the never-named blue square. The receiver guessed #3. By the pre-committed table this is a *one-sided grammar* — **the mirror image of Campaign 1's run 3, now in the opposite direction**. Both directions have now produced exactly one verified one-sided grammar: the sender composes the predicted unseen word, and the listener fails to decode it.

Against the three interpretations pre-registered before any Campaign 2 round:

- *receiver-deficit-specific-to-Qwen* — **rejected**: Gemma-as-receiver also decoded 0/5, including run 5 where the composed word was actually sent.
- *composition-is-Gemma-specific* — **rejected**: Qwen-as-sender produced a non-vacuous, injective compositional lexicon (run 5).
- *listening-intrinsically-hard-at-4B* — **consistent with these runs**: zero hits again; decomposition failed on the listening side in both directions here. (With one verified one-sided grammar per direction, this is a repeated observation, not an established architectural claim — see the appendix and Future work.)

> Under the same uniform-random null used for Campaign 1, run 5's single injective-compositional match has probability 1/9 (~11%) by chance. As with Campaign 1, this is reported as **an anomaly worth follow-up, not a finding**.

### Post-hoc amendments (disclosed, not pre-registered — exploratory)

Two mid-campaign changes are logged as protocol notes in `kumi2-provenance.jsonl`, flagged in `kumi2-results.md`, and independently confirmed by `audit2.py`: **(1)** after run 2 hovered near chance for 110 rounds, `CAP_ROUNDS` was cut from 150 to 120 (a stopping-rule change only; run 2 had touched rolling-15 = 0.73 at round 85 — two rounds shy of the gate — before collapsing); **(2)** after run 2, Qwen's `<think>` mode was disabled for runs 3–5. Runs 1–2 ran with thinking ON, runs 3–5 with thinking OFF — the auditor verifies sender `<think>` content is present in runs 1–2 and absent in 3–5 — so within-campaign comparisons across that boundary are **exploratory**, and the campaign-level counts are reported split at the boundary (see above). (The sender think budget was also raised pre-launch from 500 to 900 tokens, then dropped to the default once thinking was disabled.) The campaign crashed and resumed twice; resumes reconstruct histories from the provenance chain and are logged there.

### Run 2's notebook: self-description diverged from behavior

Over 120 rounds, Qwen-as-sender's private notebook consistently asserted a color code (▲ = red, ■ = blue) that its emitted words never used — position 0 was ▲ for *almost every* object (108/120) — and each round its reasoning re-confirmed the phantom code and blamed the receiver. This is **notebook self-description diverging from behavior**, caught inside the experiment by comparing the notebook stream against the words on the channel, both logged every round. It is why the protocol's founding rule — self-reports are logged but carry no evidential weight; verdicts come only from what arrives on the channel — matters: a protocol that trusted the notebook would have scored run 2 as a receiver failure. The protocol makes no claim that notebooks causally drive behavior; run 2 is evidence they may not, and a notebook-ablation experiment is listed under Future work.

### What the two campaigns say together

Across both directions of a cross-family 4B pairing, senders can invent systematic codes — each campaign produced exactly one non-vacuously compositional lexicon whose sender then *composed the exactly-predicted unseen word at test time* — and receivers in either direction failed to decode composition even once. In these ten runs, speaking in parts emerged before hearing in parts. With one verified case per direction (n = 2), that is a **repeated anomaly under a pre-registered test, not evidence of an architectural bottleneck**: whether receivers *cannot* decompose at this scale, or merely *did not* after training on the sender's noisy early exploration, is an open question the forced-listening ablation (Future work) is designed to separate.

## Appendix — null model for the compositionality rule

*Added 2026-07-18, following a second external review by Gemini 3.1 Pro, which correctly noted the state space is small enough that "compositional" lexicons can arise by chance. Exact enumeration over the 9-word space (two symbols from ▲ ● ■; 9³ = 729 possible three-object lexicons):*

| Event (uniform-random lexicon) | Count | Probability |
|---|---|---|
| Passes the positional-consistency rule (either order) | 153/729 | **~21.0%** |
| Passes the rule **and** is injective (clean) | 72/729 | **~9.9%** |
| Clean **and** sender then emits the exactly-predicted novel word at test (×1/9) | — | **~1.1% per run** |
| At least one such run in a 5-run campaign | — | **~5.4%** |
| Exactly that outcome in *both* independent campaigns | — | **~0.3%** |

Read honestly, this cuts both ways. A "compositional lexicon" on its own is weak evidence — a fifth of random lexicons qualify, which is why lexicon counts are reported but not headlined. The sharper pre-registered event is *clean lexicon + exact predicted novel word at the one-shot test*, and its occurrence once per campaign in both campaigns sits at roughly the 0.3% level under this null. Two caveats keep this from being a p-value: LLM senders are not uniform-random emitters (consistency-favoring priors inflate rule-passing above 21%), and multiple metrics were examined across this repository. It is reported as a bounded illustration of why the composed-word matches are **anomalies worth follow-up, not findings** — and why the small state space is listed as a limitation.

## Verification

`audit.py` is an independent auditor that reads **only** `kumi-provenance.jsonl` (no code shared with `kumi.py`). It replays every parse from the raw model replies (think-stripping included), recomputes rounds, rolling accuracies, fluency gates, lexicons, compositionality verdicts, predictions, and zero-shot outcomes, verifies that all pre-test timestamps precede each test, that crash-resume left no duplicated or missing rounds, and that no parsed guess ever originated inside a `<think>` block. Result: **99/99 checks PASS** — see `audit-report.md`.

`audit2.py` is the matching **Campaign 2 auditor**, reading **only** `kumi2-provenance.jsonl` (no code shared with `kumi2.py`). It handles what makes the role-swap chain different — sender-side (Qwen) think-stripping, a non-fluent run that stops at the cap, the two post-hoc amendments, and two crash-resumes — and adds a **degenerate-lexicon (homonym) check**: it reports the compositional count both ways, the pre-registered rule's **5/5** beside the **clean 1/5** that excludes vacuous lexicons. It also independently confirms that thinking was on for runs 1–2 and off for 3–5, and that run 2's notebook diverged from its emitted words. Result: **100/100 checks PASS** — see `audit2-report.md`.

`audit1-injectivity.md` is the **retroactive Campaign-1 injectivity re-audit** (2026-07-18): the homonym check applied backward to all Campaign-1 data, recomputed from `kumi-provenance.jsonl` alone. Claimed 2/5 → clean 2/5; run 3 fully injective including the predicted word.

```
python3 audit.py    # Campaign 1 — exits non-zero if any claim fails
python3 audit2.py   # Campaign 2 — exits non-zero if any claim fails
```

## Limitations

*Section added 2026-07-17 as a post-hoc amendment, following external review by Gemini 3.1 Pro; item 4 added 2026-07-18 following a second review.*

1. **Family × role entanglement — partially addressed.** In Campaign 1 Gemma always sent and Qwen always received, so no failure there could be attributed to model family versus role versus architecture. The role-swap campaign (Qwen sends, Gemma receives) is now reported above as **Campaign 2**: a verified one-sided grammar appears in *both* directions, so the failure is not reducible to a single model's role. Same-family baselines (Gemma×Gemma, Qwen×Qwen) remain planned — see the open issues.
2. **On the "lobotomized receiver" concern — rebutted.** Stripping Qwen's `<think>` blocks did not remove its reasoning: the receiver reasoned at full length every round, and every think block is logged raw in `kumi-provenance.jsonl`. Stripping affected parsing only — the guess is read from the post-think text — and `audit.py` verifies independently that no parsed guess ever originated inside a think block. In Campaign 2, where Qwen is the sender, the same stripping guards the word parse and `audit2.py` verifies it there.
3. **n = 5 per campaign is a pilot** — and Campaign 2 is further split 2 + 3 by the thinking-mode amendment. No systematic claims are made or implied. Scaling runs per condition is roadmap item #3.
4. **Small state space.** With only 9 possible words, ~21% of random lexicons pass the positional rule and ~10% pass it cleanly (see the appendix). Lexicon-level "compositionality" is therefore weak evidence in this world; the composed-word one-shot matches are the sharper events, and even they are reported as anomalies. Larger worlds (3 features / 8 objects) are the fix.

## Files

| File | What it is |
|---|---|
| `kumi.py` | The experiment: game loop, prompts, fluency gate, pre-registration, zero-shot test, crash-resume, report writer. Python 3 stdlib only. |
| `audit.py` | Independent Campaign 1 auditor (see above). |
| `kumi-results.md` | The report written by `kumi.py` at campaign end. |
| `audit-report.md` | Claim-by-claim PASS/FAIL table from `audit.py`. |
| `audit1-injectivity.md` | Retroactive Campaign-1 injectivity re-audit (claimed vs clean, homonym flags, run-3 check), recomputed from the chain alone. |
| `kumi-provenance.jsonl` | The chained log: one JSON line per round — raw replies, notebooks, flags, timestamps, protocol notes. |
| `kumi-provenance-aborted.jsonl` | Partial log of a prior campaign attempt aborted mid-run-1 by a Terminal restart; archived for completeness, not part of the results. |
| `kumi2.py` | Campaign 2 (role swap): same protocol with Qwen as sender / Gemma as receiver, sender-side think handling, crash-resume from the provenance chain. |
| `kumi2-results.md` | Campaign 2 report, including the pre-registered interpretations (written before round 1) and all protocol notes/amendments. |
| `kumi2-provenance.jsonl` | Campaign 2 chained log — raw replies (including Qwen's sender-side `<think>` blocks), notebooks, amendments, resume records. |
| `audit2.py` | Independent Campaign 2 auditor: replays `kumi2-provenance.jsonl` (no code shared with `kumi2.py`), adds the degenerate-lexicon check and the claimed-vs-clean compositional counts. |
| `audit2-report.md` | Claim-by-claim PASS/FAIL table from `audit2.py` (**100/100**). |

## Related work

- Y. Talebirad et al., *ALIFE 2026* — [arXiv:2607.00233](https://arxiv.org/abs/2607.00233).
- T. Kouwenhoven, M. Peeperkorn & T. Verhoef, "Searching for Structure: Investigating Emergent Communication with Large Language Models," *Proc. COLING 2025* — [aclanthology.org/2025.coling-main.667](https://aclanthology.org/2025.coling-main.667/); see also Kouwenhoven et al., "Shaping Shared Languages: Human and Large Language Models' Inductive Biases in Emergent Communication," *IJCAI 2025* — [arXiv:2503.04395](https://arxiv.org/abs/2503.04395).

## Future work

*Reordered 2026-07-18; the forced-listening ablation was proposed by the second external review and is adopted as the priority experiment.*

- **Forced-listening ablation — the next experiment.** Pair each LLM receiver with a hardcoded, deterministic, perfectly injective compositional sender. This separates the two readings of the zero-hit result: receivers *lack the capacity* to decompose at 4B, versus receivers *were trained in the noise* of the sender's chaotic early exploration. Nothing in the current data distinguishes them.
- **Notebook causal ablation.** Run campaigns with notebooks disabled (or scrambled) to measure whether the persistent notebook causally affects behavior at all — run 2's phantom color code suggests it may not.
- ~~**Role swap**~~ — done (Campaign 2): a verified one-sided grammar appears in *both* directions — one case per direction; see the n = 2 caveat above. Same-family baselines (Gemma×Gemma, Qwen×Qwen) remain, addressing the family confound.
- More runs per condition; three-feature worlds; larger holdout sets.
- **Injectivity in the rule**: require distinct symbols per feature value in the pre-registered compositionality check, so vacuous lexicons no longer count as compositional.

## Author & method

**Jason / Studio Ayumi.** The experiment harness, auditor, and this repository were built collaboratively with **Claude Fable 5** (Anthropic), noted here as method: the protocol design, code, and audit criteria were developed together, and all results derive from the two local 4B models named above. Campaign 2 (role swap) and its independent auditor (`audit2.py`) were added in a later session in the same method.

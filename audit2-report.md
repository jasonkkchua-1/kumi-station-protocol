# kumi — Campaign 2 (role swap) · independent audit report

*2026-07-18T06:49:06 · audit2.py reads only `kumi2-provenance.jsonl` and shares no analysis code with `kumi2.py`*

**Verdict: CLEAN — all checks passed** (100/100 checks passed)

Published claims (rounds, lexicons, verdicts) are transcribed from `kumi2-results.md` into this script as constants and compared against values recomputed from the raw chain. The pre-registered prediction has no separate log record; it is verified as a deterministic function of the training rounds alone, all timestamped before the zero-shot test.

**Compositional count — claimed 5/5 vs CLEAN 1/5.** 4 of 5 lexicons are degenerate (one word serving two objects: runs [1, 2, 3, 4]); these satisfy the composition rule only because a feature dimension has collapsed. Only run 5 is a clean compositional lexicon — and it emitted the exact pre-registered word for the unseen object while the receiver still missed (a verified one-sided grammar).

| # | Check | Verdict | Detail |
|---|---|---|---|
| 1 | Run 1: round numbers are exactly 1..21, no duplicates or gaps | **PASS** | got 21 rounds, min 1, max 21 |
| 2 | Run 1: rounds to fluency = 21 (claimed) | **PASS** | recomputed 21 |
| 3 | Run 1: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 4 | Run 1: object features in log match the fixed world | **PASS** |  |
| 5 | Run 1: every train payoff == (guess == object) | **PASS** |  |
| 6 | Run 1: fluency gate (>=20 rounds, rolling15 >= 0.75, all 3 objects in window) fires at round 21 and at no earlier round | **PASS** | gate true at rounds [21]; final rolling15 = 0.800 |
| 7 | Run 1: every logged word reproduced by independent parse of raw SENDER (Qwen) replies, taken from outside any <think> block | **PASS** |  |
| 8 | Run 1: every logged guess reproduced by independent parse of raw RECEIVER (gemma) replies | **PASS** |  |
| 9 | Run 1: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 10 | Run 1: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 11 | Run 1: recomputed lexicon (modal word, last 40 rounds) = ▲■ ▲● ▲■ (claimed) | **PASS** | recomputed ▲■ ▲● ▲■; no modal ties |
| 12 | Run 1: degenerate-lexicon check — recorded whether any word serves two objects (DEGENERATE) | **PASS** | '▲■' serves objects [1, 3] |
| 13 | Run 1: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True  [NOTE: fires on a DEGENERATE lexicon — excluded from clean count] |
| 14 | Run 1: predicted obj-4 word recomputed = '▲●' (claimed), matches zero-shot record | **PASS** | recomputed '▲●', logged '▲●' |
| 15 | Run 1: prediction precedes test — all 21 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-17T12:50:46.898401+00:00 < test 2026-07-17T12:54:58.082855+00:00 |
| 16 | Run 1: timestamps strictly increase in round order through the test | **PASS** |  |
| 17 | Run 1: zero-shot record — object 4, sent '▲■', guess 3, hit=False (claimed) | **PASS** | logged word '▲■', guess 3, payoff 0 |
| 18 | Run 1: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 19 | Run 2: round numbers are exactly 1..120, no duplicates or gaps | **PASS** | got 120 rounds, min 1, max 120 |
| 20 | Run 2: non-fluent, ran to the cap of 120 rounds (claimed) | **PASS** | recomputed 120 |
| 21 | Run 2: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 22 | Run 2: object features in log match the fixed world | **PASS** |  |
| 23 | Run 2: every train payoff == (guess == object) | **PASS** |  |
| 24 | Run 2: non-fluent — fluency gate never fires across all 120 rounds | **PASS** | gate true at rounds []; final rolling15 = 0.400 |
| 25 | Run 2: every logged word reproduced by independent parse of raw SENDER (Qwen) replies, taken from outside any <think> block | **PASS** |  |
| 26 | Run 2: every logged guess reproduced by independent parse of raw RECEIVER (gemma) replies | **PASS** |  |
| 27 | Run 2: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 28 | Run 2: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 29 | Run 2: recomputed lexicon (modal word, last 40 rounds) = ▲● ▲■ ▲● (claimed) | **PASS** | recomputed ▲● ▲■ ▲●; no modal ties |
| 30 | Run 2: degenerate-lexicon check — recorded whether any word serves two objects (DEGENERATE) | **PASS** | '▲●' serves objects [1, 3] |
| 31 | Run 2: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True  [NOTE: fires on a DEGENERATE lexicon — excluded from clean count] |
| 32 | Run 2: predicted obj-4 word recomputed = '▲■' (claimed), matches zero-shot record | **PASS** | recomputed '▲■', logged '▲■' |
| 33 | Run 2: prediction precedes test — all 120 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-17T23:52:57.117308+00:00 < test 2026-07-17T23:54:49.013397+00:00 |
| 34 | Run 2: timestamps strictly increase in round order through the test | **PASS** |  |
| 35 | Run 2: zero-shot record — object 4, sent '■■', guess 2, hit=False (claimed) | **PASS** | logged word '■■', guess 2, payoff 0 |
| 36 | Run 2: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 37 | Run 3: round numbers are exactly 1..48, no duplicates or gaps | **PASS** | got 48 rounds, min 1, max 48 |
| 38 | Run 3: rounds to fluency = 48 (claimed) | **PASS** | recomputed 48 |
| 39 | Run 3: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 40 | Run 3: object features in log match the fixed world | **PASS** |  |
| 41 | Run 3: every train payoff == (guess == object) | **PASS** |  |
| 42 | Run 3: fluency gate (>=20 rounds, rolling15 >= 0.75, all 3 objects in window) fires at round 48 and at no earlier round | **PASS** | gate true at rounds [48]; final rolling15 = 0.800 |
| 43 | Run 3: every logged word reproduced by independent parse of raw SENDER (Qwen) replies, taken from outside any <think> block | **PASS** |  |
| 44 | Run 3: every logged guess reproduced by independent parse of raw RECEIVER (gemma) replies | **PASS** |  |
| 45 | Run 3: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 46 | Run 3: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 47 | Run 3: recomputed lexicon (modal word, last 40 rounds) = ▲● ▲● ▲■ (claimed) | **PASS** | recomputed ▲● ▲● ▲■; no modal ties |
| 48 | Run 3: degenerate-lexicon check — recorded whether any word serves two objects (DEGENERATE) | **PASS** | '▲●' serves objects [1, 2] |
| 49 | Run 3: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True  [NOTE: fires on a DEGENERATE lexicon — excluded from clean count] |
| 50 | Run 3: predicted obj-4 word recomputed = '▲■' (claimed), matches zero-shot record | **PASS** | recomputed '▲■', logged '▲■' |
| 51 | Run 3: prediction precedes test — all 48 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-18T00:51:18.380204+00:00 < test 2026-07-18T00:52:24.286798+00:00 |
| 52 | Run 3: timestamps strictly increase in round order through the test | **PASS** |  |
| 53 | Run 3: zero-shot record — object 4, sent '■▲', guess 3, hit=False (claimed) | **PASS** | logged word '■▲', guess 3, payoff 0 |
| 54 | Run 3: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 55 | Run 4: round numbers are exactly 1..81, no duplicates or gaps | **PASS** | got 81 rounds, min 1, max 81 |
| 56 | Run 4: rounds to fluency = 81 (claimed) | **PASS** | recomputed 81 |
| 57 | Run 4: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 58 | Run 4: object features in log match the fixed world | **PASS** |  |
| 59 | Run 4: every train payoff == (guess == object) | **PASS** |  |
| 60 | Run 4: fluency gate (>=20 rounds, rolling15 >= 0.75, all 3 objects in window) fires at round 81 and at no earlier round | **PASS** | gate true at rounds [81]; final rolling15 = 0.800 |
| 61 | Run 4: every logged word reproduced by independent parse of raw SENDER (Qwen) replies, taken from outside any <think> block | **PASS** |  |
| 62 | Run 4: every logged guess reproduced by independent parse of raw RECEIVER (gemma) replies | **PASS** |  |
| 63 | Run 4: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 64 | Run 4: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 65 | Run 4: recomputed lexicon (modal word, last 40 rounds) = ▲■ ▲● ▲■ (claimed) | **PASS** | recomputed ▲■ ▲● ▲■; no modal ties |
| 66 | Run 4: degenerate-lexicon check — recorded whether any word serves two objects (DEGENERATE) | **PASS** | '▲■' serves objects [1, 3] |
| 67 | Run 4: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True  [NOTE: fires on a DEGENERATE lexicon — excluded from clean count] |
| 68 | Run 4: predicted obj-4 word recomputed = '▲●' (claimed), matches zero-shot record | **PASS** | recomputed '▲●', logged '▲●' |
| 69 | Run 4: prediction precedes test — all 81 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-18T02:47:29.242330+00:00 < test 2026-07-18T02:48:26.222578+00:00 |
| 70 | Run 4: timestamps strictly increase in round order through the test | **PASS** |  |
| 71 | Run 4: zero-shot record — object 4, sent '▲■', guess 3, hit=False (claimed) | **PASS** | logged word '▲■', guess 3, payoff 0 |
| 72 | Run 4: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 73 | Run 5: round numbers are exactly 1..36, no duplicates or gaps | **PASS** | got 36 rounds, min 1, max 36 |
| 74 | Run 5: rounds to fluency = 36 (claimed) | **PASS** | recomputed 36 |
| 75 | Run 5: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 76 | Run 5: object features in log match the fixed world | **PASS** |  |
| 77 | Run 5: every train payoff == (guess == object) | **PASS** |  |
| 78 | Run 5: fluency gate (>=20 rounds, rolling15 >= 0.75, all 3 objects in window) fires at round 36 and at no earlier round | **PASS** | gate true at rounds [36]; final rolling15 = 0.800 |
| 79 | Run 5: every logged word reproduced by independent parse of raw SENDER (Qwen) replies, taken from outside any <think> block | **PASS** |  |
| 80 | Run 5: every logged guess reproduced by independent parse of raw RECEIVER (gemma) replies | **PASS** |  |
| 81 | Run 5: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 82 | Run 5: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 83 | Run 5: recomputed lexicon (modal word, last 40 rounds) = ▲● ▲■ ■● (claimed) | **PASS** | recomputed ▲● ▲■ ■●; no modal ties |
| 84 | Run 5: degenerate-lexicon check — recorded whether any word serves two objects (clean) | **PASS** | no homonyms — every object has a distinct word |
| 85 | Run 5: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True |
| 86 | Run 5: predicted obj-4 word recomputed = '■■' (claimed), matches zero-shot record | **PASS** | recomputed '■■', logged '■■' |
| 87 | Run 5: prediction precedes test — all 36 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-18T03:37:28.341921+00:00 < test 2026-07-18T03:38:41.082856+00:00 |
| 88 | Run 5: timestamps strictly increase in round order through the test | **PASS** |  |
| 89 | Run 5: zero-shot record — object 4, sent '■■', guess 3, hit=False (claimed) | **PASS** | logged word '■■', guess 3, payoff 0 |
| 90 | Run 5: matched_prediction recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True |
| 91 | HEADLINE — Run 5: sender emitted, for the unseen object, EXACTLY the pre-registered predicted word '■■' (compositional, non-degenerate lexicon; matched_prediction=True) | **PASS** | predicted '■■', sent '■■', receiver guessed #3 (hit=False) -> one-sided grammar: sender composed, receiver failed to decode |
| 92 | CRITICAL — compositional count, CLAIMED vs CLEAN: claimed 5/5 (pre-registered rule, counts degenerate lexicons); CLEAN 1/5 (excludes degenerate homonym lexicons) | **PASS** | degenerate (excluded) runs: [1, 2, 3, 4]; clean compositional runs: [5] |
| 93 | Amendment cross-check: Qwen sender <think> content present in runs 1-2 and absent from runs 3-5 (thinking DISABLED from run 3 onward, as amended) | **PASS** | think-content runs [1, 2]; no-think runs [3, 4, 5] run 1=28122c; run 2=128236c; run 3=0c; run 4=0c; run 5=0c |
| 94 | Run 2: notebook self-description diverged from behaviour — sender's notebooks assert a color code (▲=red / ■=blue) it does not emit; the emitted color slot (position 0) is nearly constant, so color is never actually encoded | **PASS** | 94/120 notebooks assert a ▲=red/■=blue-style code; emitted position-0 distribution {'▲': 108, '■': 12} (dominant '▲' 108/120 = 90%) |
| 95 | Exactly two crash-resume protocol notes in the log (run 2 from 118, run 4 from 58) | **PASS** | found 2 |
| 96 | Provenance file is append-only: physical line order is time-ordered | **PASS** |  |
| 97 | Role swap verified: Qwen SENDS and gemma RECEIVES in every record | **PASS** | model pairs seen: {('mlx-community/Qwen3-4B-4bit', 'mlx-community/gemma-3-4b-it-qat-4bit')} |
| 98 | Summary: converged to fluency 4/5 | **PASS** |  |
| 99 | Summary: zero-shot hits 0/5 | **PASS** |  |
| 100 | Summary: predicted-word AND hit 0/5 | **PASS** |  |

## Audit notes — protocol amendments (recorded from the chain)

- Sender token budget (post-hoc / exploratory): the chain documents the SENDER (Qwen) think budget being raised PRE-LAUNCH from Campaign 1's 500 to **900** tokens (dry-check calibration, before any round), then dropped to MAX_TOKENS (300) once thinking was disabled mid-campaign. **No value of 1500 appears anywhere in the chain** — if 1500 was expected, that figure is not supported by the provenance. (budget-adjacent figures found in notes: none.)
- Thinking DISABLED from run 3 (post-hoc / exploratory, NOT pre-registered): confirmed independently above — sender <think> content is present only in runs 1-2 and absent from runs 3-5. Cross-run comparisons within Campaign 2 are therefore exploratory, as the amendment itself states.
- Round-cap change (post-hoc / exploratory, NOT pre-registered): CAP_ROUNDS reduced mid-campaign from 150 to 120 after run 2 stalled near chance. Only run 2 is affected (it ran to the 120 cap and is recorded non-fluent). The fluency gate, one-trial zero-shot test, and pre-registered interpretations are unchanged.
- Degeneracy caveat (headline): the pre-registered composition rule scores 5/5 compositional, but 4/5 of those lexicons are DEGENERATE (a single word serves two objects: runs [1, 2, 3, 4]). After excluding degenerate lexicons the CLEAN compositional count is 1/5 — only run 5, which also emitted the exact pre-registered novel word for the unseen object.

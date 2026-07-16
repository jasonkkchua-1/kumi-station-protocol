# kumi — independent audit report

*2026-07-16T14:34:58 · audit.py reads only `kumi-provenance.jsonl` and shares no code with `kumi.py`*

**Verdict: CLEAN — all claims verified** (99/99 checks passed)

Published claims (rounds, lexicons, verdicts) are transcribed from `kumi-results.md` into the audit script as constants and compared against values recomputed from the raw log. The pre-registered prediction has no separate log record; it is verified as a deterministic function of the training rounds alone, all of which are timestamped before the zero-shot test.

| # | Claim | Verdict | Detail |
|---|---|---|---|
| 1 | Run 1: round numbers are exactly 1..49, no duplicates or gaps | **PASS** | got 49 rounds, min 1, max 49 |
| 2 | Run 1: rounds to fluency = 49 (claimed) | **PASS** | recomputed 49 |
| 3 | Run 1: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 4 | Run 1: object features in log match the fixed world | **PASS** |  |
| 5 | Run 1: every train payoff == (guess == object) | **PASS** |  |
| 6 | Run 1: fluency gate (≥20 rounds, rolling15 ≥ 0.75, all 3 objects in window) fires at round 49 and at no earlier round | **PASS** | gate true at rounds [49]; final rolling15 = 0.800 |
| 7 | Run 1: every logged word reproduced by independent parse of raw sender replies | **PASS** |  |
| 8 | Run 1: every logged guess reproduced by independent parse of raw receiver replies | **PASS** |  |
| 9 | Run 1: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 10 | Run 1: no <think> leakage — every parsed word/guess comes from think-stripped text or the flagged substitution rule, never from think content | **PASS** | flagged substitution rounds (not leakage): [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27] |
| 11 | Run 1: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 12 | Run 1: recomputed lexicon (modal word, last 40 rounds) = ●● ▲▲ ●■ (claimed) | **PASS** | recomputed ●● ▲▲ ●■; no modal ties |
| 13 | Run 1: compositionality recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False, logged False |
| 14 | Run 1: predicted obj-4 word recomputed = 'holistic — no prediction' (claimed), matches zero-shot record | **PASS** | recomputed 'holistic — no prediction', logged 'holistic — no prediction' |
| 15 | Run 1: prediction precedes test — all 49 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-16T12:43:39.563903+00:00 < test 2026-07-16T12:44:53.002079+00:00 |
| 16 | Run 1: timestamps strictly increase in round order through the test | **PASS** |  |
| 17 | Run 1: zero-shot record — object 4, sent '■■', guess 2, hit=False (claimed) | **PASS** | logged word '■■', guess 2, payoff 0 |
| 18 | Run 1: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 19 | Run 2: round numbers are exactly 1..23, no duplicates or gaps | **PASS** | got 23 rounds, min 1, max 23 |
| 20 | Run 2: rounds to fluency = 23 (claimed) | **PASS** | recomputed 23 |
| 21 | Run 2: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 22 | Run 2: object features in log match the fixed world | **PASS** |  |
| 23 | Run 2: every train payoff == (guess == object) | **PASS** |  |
| 24 | Run 2: fluency gate (≥20 rounds, rolling15 ≥ 0.75, all 3 objects in window) fires at round 23 and at no earlier round | **PASS** | gate true at rounds [23]; final rolling15 = 0.800 |
| 25 | Run 2: every logged word reproduced by independent parse of raw sender replies | **PASS** |  |
| 26 | Run 2: every logged guess reproduced by independent parse of raw receiver replies | **PASS** |  |
| 27 | Run 2: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 28 | Run 2: no <think> leakage — every parsed word/guess comes from think-stripped text or the flagged substitution rule, never from think content | **PASS** | flagged substitution rounds (not leakage): [2] |
| 29 | Run 2: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 30 | Run 2: recomputed lexicon (modal word, last 40 rounds) = ●■ ■● ●■ (claimed) | **PASS** | recomputed ●■ ■● ●■; no modal ties |
| 31 | Run 2: compositionality recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False, logged False |
| 32 | Run 2: predicted obj-4 word recomputed = 'holistic — no prediction' (claimed), matches zero-shot record | **PASS** | recomputed 'holistic — no prediction', logged 'holistic — no prediction' |
| 33 | Run 2: prediction precedes test — all 23 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-16T13:07:07.065767+00:00 < test 2026-07-16T13:08:10.438402+00:00 |
| 34 | Run 2: timestamps strictly increase in round order through the test | **PASS** |  |
| 35 | Run 2: zero-shot record — object 4, sent '●■', guess 3, hit=False (claimed) | **PASS** | logged word '●■', guess 3, payoff 0 |
| 36 | Run 2: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 37 | Run 3: round numbers are exactly 1..33, no duplicates or gaps | **PASS** | got 33 rounds, min 1, max 33 |
| 38 | Run 3: rounds to fluency = 33 (claimed) | **PASS** | recomputed 33 |
| 39 | Run 3: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 40 | Run 3: object features in log match the fixed world | **PASS** |  |
| 41 | Run 3: every train payoff == (guess == object) | **PASS** |  |
| 42 | Run 3: fluency gate (≥20 rounds, rolling15 ≥ 0.75, all 3 objects in window) fires at round 33 and at no earlier round | **PASS** | gate true at rounds [33]; final rolling15 = 0.800 |
| 43 | Run 3: every logged word reproduced by independent parse of raw sender replies | **PASS** |  |
| 44 | Run 3: every logged guess reproduced by independent parse of raw receiver replies | **PASS** |  |
| 45 | Run 3: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 46 | Run 3: no <think> leakage — every parsed word/guess comes from think-stripped text or the flagged substitution rule, never from think content | **PASS** | no substitutions |
| 47 | Run 3: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 48 | Run 3: recomputed lexicon (modal word, last 40 rounds) = ■● ■■ ●● (claimed) | **PASS** | recomputed ■● ■■ ●●; no modal ties |
| 49 | Run 3: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True |
| 50 | Run 3: predicted obj-4 word recomputed = '●■' (claimed), matches zero-shot record | **PASS** | recomputed '●■', logged '●■' |
| 51 | Run 3: prediction precedes test — all 33 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-16T13:38:46.869978+00:00 < test 2026-07-16T13:40:01.112840+00:00 |
| 52 | Run 3: timestamps strictly increase in round order through the test | **PASS** |  |
| 53 | Run 3: zero-shot record — object 4, sent '●■', guess 1, hit=False (claimed) | **PASS** | logged word '●■', guess 1, payoff 0 |
| 54 | Run 3: matched_prediction recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True |
| 55 | Run 4: round numbers are exactly 1..20, no duplicates or gaps | **PASS** | got 20 rounds, min 1, max 20 |
| 56 | Run 4: rounds to fluency = 20 (claimed) | **PASS** | recomputed 20 |
| 57 | Run 4: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 58 | Run 4: object features in log match the fixed world | **PASS** |  |
| 59 | Run 4: every train payoff == (guess == object) | **PASS** |  |
| 60 | Run 4: fluency gate (≥20 rounds, rolling15 ≥ 0.75, all 3 objects in window) fires at round 20 and at no earlier round | **PASS** | gate true at rounds [20]; final rolling15 = 0.800 |
| 61 | Run 4: every logged word reproduced by independent parse of raw sender replies | **PASS** |  |
| 62 | Run 4: every logged guess reproduced by independent parse of raw receiver replies | **PASS** |  |
| 63 | Run 4: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 64 | Run 4: no <think> leakage — every parsed word/guess comes from think-stripped text or the flagged substitution rule, never from think content | **PASS** | flagged substitution rounds (not leakage): [2] |
| 65 | Run 4: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 66 | Run 4: recomputed lexicon (modal word, last 40 rounds) = ▲● ▲■ ■● (claimed) | **PASS** | recomputed ▲● ▲■ ■●; no modal ties |
| 67 | Run 4: compositionality recomputed = True (claimed), matches zero-shot record | **PASS** | recomputed True, logged True |
| 68 | Run 4: predicted obj-4 word recomputed = '■■' (claimed), matches zero-shot record | **PASS** | recomputed '■■', logged '■■' |
| 69 | Run 4: prediction precedes test — all 20 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-16T13:58:10.567842+00:00 < test 2026-07-16T13:59:15.454396+00:00 |
| 70 | Run 4: timestamps strictly increase in round order through the test | **PASS** |  |
| 71 | Run 4: zero-shot record — object 4, sent '■▲', guess 2, hit=False (claimed) | **PASS** | logged word '■▲', guess 2, payoff 0 |
| 72 | Run 4: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 73 | Run 5: round numbers are exactly 1..21, no duplicates or gaps | **PASS** | got 21 rounds, min 1, max 21 |
| 74 | Run 5: rounds to fluency = 21 (claimed) | **PASS** | recomputed 21 |
| 75 | Run 5: training objects all in {1,2,3} (object 4 held out) | **PASS** |  |
| 76 | Run 5: object features in log match the fixed world | **PASS** |  |
| 77 | Run 5: every train payoff == (guess == object) | **PASS** |  |
| 78 | Run 5: fluency gate (≥20 rounds, rolling15 ≥ 0.75, all 3 objects in window) fires at round 21 and at no earlier round | **PASS** | gate true at rounds [21]; final rolling15 = 0.800 |
| 79 | Run 5: every logged word reproduced by independent parse of raw sender replies | **PASS** |  |
| 80 | Run 5: every logged guess reproduced by independent parse of raw receiver replies | **PASS** |  |
| 81 | Run 5: parse-failure flags match the replayed retry/substitution logic | **PASS** |  |
| 82 | Run 5: no <think> leakage — every parsed word/guess comes from think-stripped text or the flagged substitution rule, never from think content | **PASS** | no substitutions |
| 83 | Run 5: every logged word is exactly 2 symbols from ▲●■ | **PASS** |  |
| 84 | Run 5: recomputed lexicon (modal word, last 40 rounds) = ●▲ ■● ●■ (claimed) | **PASS** | recomputed ●▲ ■● ●■; no modal ties |
| 85 | Run 5: compositionality recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False, logged False |
| 86 | Run 5: predicted obj-4 word recomputed = 'holistic — no prediction' (claimed), matches zero-shot record | **PASS** | recomputed 'holistic — no prediction', logged 'holistic — no prediction' |
| 87 | Run 5: prediction precedes test — all 21 train timestamps < zero-shot timestamp, and prediction depends only on those train rounds | **PASS** | last train 2026-07-16T14:18:51.811132+00:00 < test 2026-07-16T14:19:51.005064+00:00 |
| 88 | Run 5: timestamps strictly increase in round order through the test | **PASS** |  |
| 89 | Run 5: zero-shot record — object 4, sent '■●', guess 2, hit=False (claimed) | **PASS** | logged word '■●', guess 2, payoff 0 |
| 90 | Run 5: matched_prediction recomputed = False (claimed), matches zero-shot record | **PASS** | recomputed False |
| 91 | HEADLINE — Run 3: the word the sender actually sent for the unseen object exactly equals the pre-registered predicted word | **PASS** | predicted '●■', sent '●■' |
| 92 | Exactly one crash-resume protocol note in the log | **PASS** | found 1 |
| 93 | Resume note ('run 1 continues from round 29') consistent with timestamps: rounds 1-28 precede the note, rounds 29+ follow it, nothing lost or repeated | **PASS** | pre-crash rounds 1-28, post-resume rounds 29-49 |
| 94 | Provenance file is append-only: physical line order is time-ordered | **PASS** |  |
| 95 | Sender/receiver models identical in every record (gemma sends, qwen receives) | **PASS** |  |
| 96 | Summary: converged to fluency 5/5 | **PASS** |  |
| 97 | Summary: compositional lexicon 2/5 | **PASS** |  |
| 98 | Summary: zero-shot hits 0/5 | **PASS** |  |
| 99 | Summary: predicted-word AND hit 0/5 | **PASS** |  |


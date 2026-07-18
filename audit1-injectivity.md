# 組 kumi — Campaign 1 injectivity re-audit

*The degenerate-lexicon (homonym) check developed for Campaign 2 (`audit2.py`), applied retroactively to Campaign 1. Input: **`kumi-provenance.jsonl` only** (read-only; no other file consulted for the computation). Method: modal word per training object over the last 40 training rounds (full run if shorter) — identical to the Campaign 2 audit window.*

*Generated 2026-07-18, following a second external review (Gemini 3.1 Pro).*

## The question

Campaign 2's audit showed its "5/5 compositional" was really 1/5 clean — four lexicons passed the positional-consistency rule while assigning the **same word to two objects** (homonyms). Does Campaign 1's claimed "2/5 compositional" survive the same injectivity check — and specifically, is run 3 (the headline one-sided grammar) injective?

## Per-run recomputation

| Run | n (train) | Modal lexicon (obj 1 / 2 / 3) | Positional? | Homonym (word→objs) | Injective? | CLEAN? | Rule predicts obj4 | Campaign claimed | Sent at test |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 49 | ●● / ▲▲ / ●■ | no | — | yes | no (not positional) | — | holistic ✓ | ■■ (#2) |
| 2 | 23 | ●■ / ■● / ●■ | no | **●■ → [1, 3]** | **no** | no (not positional) | — | holistic ✓ | ●■ (#3) |
| 3 | 33 | ■● / ■■ / ●● | **yes** | — | **yes** | **YES** | **●■** | compositional, predicted ●■ ✓ | **●■** (#1) |
| 4 | 20 | ▲● / ▲■ / ■● | **yes** | — | **yes** | **YES** | **■■** | compositional, predicted ■■ ✓ | ■▲ (#2) |
| 5 | 21 | ●▲ / ■● / ●■ | no | — | yes | no (not positional) | — | holistic ✓ | ■● (#2) |

## Counts

**Campaign claimed compositional: 2/5 · recomputed positional: 2/5 · CLEAN (positional + injective): 2/5 — gap: 0.**

Unlike Campaign 2 (claimed 5/5 → clean 1/5), **Campaign 1's compositional count survives the injectivity check unchanged.** The only homonym in the campaign (run 2's ●■ serving both objects 1 and 3) occurs in a run that was never claimed compositional, so it affects nothing.

## The critical question: run 3

**Yes — run 3 is fully injective.**

- Training lexicon: obj 1 = ■●, obj 2 = ■■, obj 3 = ●● — three distinct words, no homonyms.
- Positional structure (color at position 0, shape at position 1): red = ■, blue = ●; circle = ●, square = ■. Consistent across all three training objects.
- The rule's prediction for the held-out blue square: ●■ — matching the campaign's pre-registered prediction exactly.
- **Extended-lexicon check:** the predicted word ●■ does not collide with any training word, so even the 4-word lexicon {■●, ■■, ●●, ●■} is injective. The composed word was a genuinely *new, unambiguous* word — not a reuse.
- At test the sender sent exactly ●■; the receiver guessed #1. The **one-sided grammar** verdict stands on a clean, injective code. (Note the aesthetic quirk, irrelevant to injectivity: the *feature symbols* overlap across features — red and square share ■, blue and circle share ● — but every object's *word* is unique, which is what injectivity requires.)

Run 4 is also clean and injective; its known failure mode is different (sender-side breakdown: the rule predicted ■■ but the sender emitted ■▲ at test).

## Cross-checks

- These lexicons, homonym flags, and counts agree exactly with the independent kai-side audit ([`kai-audit-lexicons.md` in the kai-station repository](https://github.com/jasonkkchua-1/kai-station/blob/main/kai-audit-lexicons.md), computed separately for the Kai eavesdropper analysis).
- The recomputed positional verdicts and predicted words agree with the campaign's own `zero_shot` records in the chain (claimed flags read from the chain only after recomputation, for comparison).

## Bottom line

Campaign 1's headline is *strengthened*, not weakened, by the injectivity check: both of its claimed compositional runs are clean, and run 3 — the one-sided grammar — composed a novel, injective, pre-registered word that no training round had ever used. The C2 audit's homonym problem is specific to Campaign 2.

*Provenance untouched.*

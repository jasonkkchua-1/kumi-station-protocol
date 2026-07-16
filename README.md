# 組 kumi — the Kumi Station Protocol

*Speaking without words, meanings meeting at the station.*

Two small local language models from different families play a Lewis signaling game and are tested — once, and only once per run — on whether the code they invented generalizes to an object neither of them has ever named. Everything needed to check the claims ships in this repository, including an independent auditor.

## The Kumi Station Protocol

A pre-registration discipline for one-shot emergent-language tests:

1. **Hold back.** One object (here: object 4, the blue square) is excluded from all training rounds. The pair converses only about the other three until a fluency gate is met (≥20 rounds, rolling-15 accuracy ≥ 0.75, all three training objects present in the window).
2. **Pre-register.** Before the held-out object is ever shown, the sender's lexicon (modal word per object over the last 40 rounds) is checked against a fixed, pre-committed compositionality rule (both position orders: color/shape and shape/color). If and only if the rule holds, a specific two-symbol word for the held-out object is predicted and written down.
3. **One trial.** The held-out object is presented exactly once. No retries, no best-of-N, no post-hoc selection.
4. **Verdict by arrival.** The outcome is scored by what actually arrives on the channel — did the sent word equal the pre-registered prediction, and did the receiver guess the held-out object? — against the interpretation table below, committed before any run.
5. **Chained log.** Every round is appended to a provenance JSONL as it happens: raw model replies (including the receiver's `<think>` blocks), both private notebooks, parse-failure flags, and timestamps. Crashes and resumes are logged as protocol notes in the same chain. The auditor replays the entire chain.

## Pre-committed interpretation table

| Outcome | Reading |
|---|---|
| compositional + predicted word + hit | **Genuine composition**: the pair built a *syntax*, and the receiver parsed a word it had never seen from its parts. |
| hit but word not predicted | **Inference by elimination**: object 4 is the only unused option, so the receiver can be right without any grammar. |
| holistic + miss | **The known default** for emergent languages: whole-word codes that don't generalize to novel objects. |
| compositional + miss | **A one-sided grammar**: the sender coded systematically but the receiver never learned to decode it compositionally. |

## Setup

- **Sender**: `mlx-community/gemma-3-4b-it-qat-4bit` · **Receiver**: `mlx-community/Qwen3-4B-4bit` — two 4-billion-parameter models from *different* model families (Google / Alibaba), served locally over an OpenAI-compatible API on consumer hardware (an 8 GB M1 Mac), no cloud.
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

### What run 3 is — and is not

Run 3 is a case of **"compositional transfer" on the sender side**: the pair's training lexicon satisfied the pre-registered compositional rule, the rule predicted ●■ for the never-named blue square, and when the moment came the sender produced exactly ●■. The receiver, however, guessed #1 — by the pre-committed table this is a *one-sided grammar*, not genuine two-sided composition. We report it in scare quotes and alongside the misses deliberately: 3 of 5 runs produced holistic codes that did not generalize, run 4's compositional sender deviated from its own grammar at test time, and no run produced a zero-shot hit. These are two cross-family 4B-parameter models on consumer hardware; the honest headline is that one directional half of compositional generalization appeared once in five runs under a pre-registered test — nothing more, and verifiably nothing less.

## Verification

`audit.py` is an independent auditor that reads **only** `kumi-provenance.jsonl` (no code shared with `kumi.py`). It replays every parse from the raw model replies (think-stripping included), recomputes rounds, rolling accuracies, fluency gates, lexicons, compositionality verdicts, predictions, and zero-shot outcomes, verifies that all pre-test timestamps precede each test, that crash-resume left no duplicated or missing rounds, and that no parsed guess ever originated inside a `<think>` block. Result: **99/99 checks PASS** — see `audit-report.md`.

```
python3 audit.py   # exits non-zero if any claim fails
```

## Files

| File | What it is |
|---|---|
| `kumi.py` | The experiment: game loop, prompts, fluency gate, pre-registration, zero-shot test, crash-resume, report writer. Python 3 stdlib only. |
| `audit.py` | Independent auditor (see above). |
| `kumi-results.md` | The report written by `kumi.py` at campaign end. |
| `audit-report.md` | Claim-by-claim PASS/FAIL table from `audit.py`. |
| `kumi-provenance.jsonl` | The chained log: one JSON line per round — raw replies, notebooks, flags, timestamps, protocol notes. |
| `kumi-provenance-aborted.jsonl` | Partial log of a prior campaign attempt aborted mid-run-1 by a Terminal restart; archived for completeness, not part of the results. |

## Related work

- Y. Talebirad et al., *ALIFE 2026* — [arXiv:2607.00233](https://arxiv.org/abs/2607.00233).
- T. Kouwenhoven, M. Peeperkorn & T. Verhoef, "Searching for Structure: Investigating Emergent Communication with Large Language Models," *Proc. COLING 2025* — [aclanthology.org/2025.coling-main.667](https://aclanthology.org/2025.coling-main.667/); see also Kouwenhoven et al., "Shaping Shared Languages: Human and Large Language Models' Inductive Biases in Emergent Communication," *IJCAI 2025* — [arXiv:2503.04395](https://arxiv.org/abs/2503.04395).

## Future work

- **Role swap**: Qwen sends, Gemma receives — is run 3's one-sided grammar a property of the sender model, the receiver model, or the pairing?
- More runs per condition; three-feature worlds; larger holdout sets.

## Author & method

**Jason / Studio Ayumi.** The experiment harness, auditor, and this repository were built in one session with **Claude Fable 5** (Anthropic), which is noted here as method: the protocol design, code, and audit criteria were developed collaboratively, and all results derive from the two local 4B models named above.

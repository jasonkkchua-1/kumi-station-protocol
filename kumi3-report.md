# 組 kumi3 — forced-listening ablation: report

*Pre-registered: kumi-station-protocol issue #5 (2026-07-18) + thinking-policy addendum + amendment comments, all before the rounds they govern. Proposed by external review (Gemini 3.1 Pro). Independent audit: every number below recomputed from the two provenance chains alone.*

## Design (one line)

Replace the LLM sender with a **perfect, deterministic, injective compositional script** (1=▲●, 2=▲■, 3=■●; held-out 4=**■■**, always sent at test) and ask whether LLM receivers — trained under the standard fluency gate, one-shot tested as always — can decode the composed word when teaching noise is zero.

## Validity

- **First attempt (2026-07-19, morning): VOID — instrumentation failure**, disclosed on issue #5. Qwen-with-thinking exhausted its token budget inside unclosed `<think>` blocks on 87/103 replies; substituted guesses fabricated the apparent data. Archived unmodified: `kumi3-provenance-qwen-void-instrumentation-20260719.jsonl`.
- **This campaign (2026-07-19, fresh under the disclosed `--no-think` amendment): VALID — 0 parse failures in 205 rounds + 10 tests.** Scripted-word integrity 205/205; the amendment note is in-chain before round 1; Qwen's residual `<think>` tags are the empty blocks `/no_think` emits (all replies parsed). Three crash-resumes, all logged, no lost or duplicated rounds.

## Results

**A1 — Qwen listens (5 runs):**

| Run | Rounds→fluency | Training acc (parsed) | Zero-shot ■■ → | Hit? |
|---|---|---|---|---|
| 1 | 20 | 0.95 | **#4** | **✓** |
| 2 | 20 | 0.85 | #3 | ✗ |
| 3 | 20 | 0.80 | #2 | ✗ |
| 4 | 21 | 0.62 | #2 | ✗ |
| 5 | 20 | 0.90 | #2 | ✗ |

**A2 — Gemma listens (5 runs):**

| Run | Rounds→fluency | Training acc (parsed) | Zero-shot ■■ → | Hit? |
|---|---|---|---|---|
| 1 | 20 | 0.95 | #3 | ✗ |
| 2 | 20 | 0.85 | #3 | ✗ |
| 3 | 23 | 0.70 | #2 | ✗ |
| 4 | 20 | 0.95 | #3 | ✗ |
| 5 | 20 | 0.95 | #2 | ✗ |

**Fluency 10/10, almost all at the gate minimum (20–23 rounds, vs 20–120+ and one cap-out under LLM senders). Zero-shot decode 1/10 — below the 2.5/10 chance expectation.**

## Pre-registered verdicts

- **Fluent + miss (9 of 10 runs): the capacity-limit reading at 4B is SUPPORTED.** Receivers failed the composed word even under a perfect, noise-free, injective teacher.
- **Fluent + hit (A1 run 1):** reported as pre-registered — a chance-consistent event in which decode and elimination cannot be separated; at 1/10 overall (below the 1-in-4 base rate), it is not evidence against the capacity reading.
- **Not-fluent row: never fired.** The strongest capacity concern did not materialize — learning three clean mappings is easy for these models.
- **Campaign-level (exploratory):** teacher quality transforms *learning speed* (fluency at gate minimum, training accuracy to 0.95) but does nothing for *compositional generalization* (1/10 vs 0/10 under noisy teachers — indistinguishable). The training-noise explanation for Campaigns 1–2's zero decode rate is **refuted for fluency and unsupported for composition**.

## What this settles, and what it doesn't

The review that motivated this ablation asked: do receivers *lack the capacity* to decompose, or was their *learning context poisoned*? Answer: the context was not the problem. Small models memorize a clean code quickly and near-perfectly, and still map a novel composed word onto the nearest familiar object rather than reading its parts — Gemma's misses split between "blue circle" and "red square," the two halves of the answer, never the whole. Speaking-in-parts before hearing-in-parts now rests on an ablation, not just an observation: at this scale, production and comprehension of structure are separable capacities, and comprehension is the harder one.

Program-level echo (cross-instrument, exploratory): the sole decode is once again **■■** — the word that visually resembles its meaning — matching Kai Phase B's finding that resemblance, not grammar, is the only thing that ever leaks in this world.

Caveats: toy world (4 objects, 9 words), one-shot test, n=5 per receiver, 4-bit models on one machine, thinking-off deviation from Campaign 1's receiver protocol (disclosed; comparisons exploratory).

## Next

Per `KUMI-REMAINING-TESTS.md`: same-family baselines (Gemma×Gemma, Qwen×Qwen) now pre-register on the capacity branch — can shared priors rescue listening where a perfect teacher couldn't? Injectivity enters the pre-registered rule from S1/S2 onward.

*Chains: `kumi3-provenance-qwen.jsonl`, `kumi3-provenance-gemma.jsonl` (append-only, READ ONLY). Void archive disclosed above. Nothing here was published before review.*

# 組 kumi3 — forced-listening ablation

*2026-07-19T17:22:25 · 5 runs · scripted sender, LLM receiver `mlx-community/gemma-3-4b-it-qat-4bit` @ `http://localhost:1234/v1` · no cloud*

Proposed by external review (Gemini 3.1 Pro, 2026-07-18). The sender is a hardcoded, deterministic, perfectly injective compositional script (pos0 color ▲/■, pos1 shape ●/■ → 1=▲●, 2=▲■, 3=■●; held-out 4=■■). It never errs and never drifts; the receiver-side protocol is identical to Campaigns 1–2. This isolates the question the earlier campaigns could not: receiver capacity vs training-context contamination.

## Results

| Run | Rounds→fluency | Test word | Receiver guessed | Zero-shot hit? |
|---|---|---|---|---|
| 1 | 20 | ■■ | #3 | ✗ |
| 2 | 20 | ■■ | #3 | ✗ |
| 3 | 23 | ■■ | #2 | ✗ |
| 4 | 20 | ■■ | #3 | ✗ |
| 5 | 20 | ■■ | #2 | ✗ |

## Summary

- Converged to fluency (three clean mappings): **5/5** (median rounds 20)
- Zero-shot hit on the composed ■■: **0/5** (chance 1/4 ≈ 1.25; Campaigns 1–2 receivers: 0/10)

## Pre-registered reading

- **fluent + hit** → receiver decoded (or eliminated its way to) the composed word under a perfect teacher — evidence against the strong capacity-limit reading (decode vs eliminate not separable per run; disclosed).
- **fluent + miss** → receiver failed even a perfect, noise-free, injective teacher — supports the capacity-limit reading at 4B.
- **not fluent** → receiver could not learn three fixed clean mappings — reported as-is; a stronger capacity concern than a miss.

*Every round (raw replies, receiver notebook) is in the matching `kumi3-provenance-*.jsonl`. The scripted sender cannot parse-fail; receiver parse failures were substituted (guess 1) and flagged.*

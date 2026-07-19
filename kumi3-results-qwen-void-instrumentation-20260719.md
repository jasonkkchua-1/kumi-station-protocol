# 組 kumi3 — forced-listening ablation

*2026-07-19T01:17:01 · 1 runs · scripted sender, LLM receiver `mlx-community/Qwen3-4B-4bit` @ `http://localhost:1234/v1` · no cloud*

Proposed by external review (Gemini 3.1 Pro, 2026-07-18). The sender is a hardcoded, deterministic, perfectly injective compositional script (pos0 color ▲/■, pos1 shape ●/■ → 1=▲●, 2=▲■, 3=■●; held-out 4=■■). It never errs and never drifts; the receiver-side protocol is identical to Campaigns 1–2. This isolates the question the earlier campaigns could not: receiver capacity vs training-context contamination.

## Protocol notes

- kumi3 campaign RESUMED: 0 run(s) complete; run 1 continues from round 11.
- mlx server crashed and was restarted by the supervisor (restart #1).

## Results

| Run | Rounds→fluency | Test word | Receiver guessed | Zero-shot hit? |
|---|---|---|---|---|
| 1 | 33 | ■■ | #1 | ✗ |

## Summary

- Converged to fluency (three clean mappings): **1/1** (median rounds 33)
- Zero-shot hit on the composed ■■: **0/1** (chance 1/4 ≈ 0.25; Campaigns 1–2 receivers: 0/10)

## Pre-registered reading

- **fluent + hit** → receiver decoded (or eliminated its way to) the composed word under a perfect teacher — evidence against the strong capacity-limit reading (decode vs eliminate not separable per run; disclosed).
- **fluent + miss** → receiver failed even a perfect, noise-free, injective teacher — supports the capacity-limit reading at 4B.
- **not fluent** → receiver could not learn three fixed clean mappings — reported as-is; a stronger capacity concern than a miss.

*Every round (raw replies, receiver notebook) is in the matching `kumi3-provenance-*.jsonl`. The scripted sender cannot parse-fail; receiver parse failures were substituted (guess 1) and flagged.*

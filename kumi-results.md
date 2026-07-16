# 組 kumi — compositionality in the Lantern mini Claudes

*2026-07-17T00:19:51 · 5 runs · local models, no cloud*

## Endpoints & roles

- Server: `http://localhost:1234/v1` (OpenAI-compatible)
- **SENDER** (Mini Claude One): `mlx-community/gemma-3-4b-it-qat-4bit`
- **RECEIVER** (Mini Claude Two): `mlx-community/Qwen3-4B-4bit`
- World: 1=red circle · 2=red square · 3=blue circle · 4=blue square (**object 4 held out of training**)
- Phase 0 upgrade: each agent keeps a private ≤150-word notebook, rewritten in full every round, re-injected above its rolling history, and never crossing the channel (both notebooks logged per round in the provenance JSONL).
- Qwen (receiver) replies may open with a <think>…</think> block; it is stripped before any parsing (word/digit/notebook come only from what remains) and logged raw in the provenance JSONL.

## Protocol notes

- 2026-07-16 ~21:24 AEST: a prior campaign attempt was ABORTED mid run 1 (a Terminal restart killed the process at round 18, rolling15 0.87). Its partial provenance is archived as kumi-provenance-aborted-20260716-213202.jsonl (~/Desktop/kumi) and kumi-provenance-aborted.jsonl (project folder). This campaign restarted from scratch with fresh histories and notebooks.
- Progress-print fix before restart: rounds with fewer than 15 payoffs previously printed 'rolling15 0.00'; they now print the labelled partial mean. The fluency window itself was verified against the aborted run's provenance and was always a true last-15 mean. The fluency gate now additionally requires all three training objects to appear within the 15-round window.
- Campaign RESUMED from provenance after a crash: 0 run(s) already complete; run 1 continues from round 29 with reconstructed histories and notebooks.

## Results

| Run | Rounds→fluency | Lexicon (1/2/3) | Compositional? | Predicted obj4 | Sent obj4 | Matched? | Zero-shot hit? |
|---|---|---|---|---|---|---|---|
| 1 | 49 | ●● ▲▲ ●■ | no | holistic — no prediction | ■■ (#2) | ✗ | ✗ |
| 2 | 23 | ●■ ■● ●■ | no | holistic — no prediction | ●■ (#3) | ✗ | ✗ |
| 3 | 33 | ■● ■■ ●● | yes | ●■ | ●■ (#1) | ✓ | ✗ |
| 4 | 20 | ▲● ▲■ ■● | yes | ■■ | ■▲ (#2) | ✗ | ✗ |
| 5 | 21 | ●▲ ■● ●■ | no | holistic — no prediction | ■● (#2) | ✗ | ✗ |

### Lexicon grids (modal word per object, last 40 rounds)

**Run 1**
```
circle square
red    ●●   ▲▲
blue   ●■   ?? (held out)
```
**Run 2**
```
circle square
red    ●■   ■●
blue   ●■   ?? (held out)
```
**Run 3**
```
circle square
red    ■●   ■■
blue   ●●   ?? (held out)
```
**Run 4**
```
circle square
red    ▲●   ▲■
blue   ■●   ?? (held out)
```
**Run 5**
```
circle square
red    ●▲   ■●
blue   ●■   ?? (held out)
```

## Summary

- Converged to fluency: **5/5**
- Compositional lexicon (pre-registered mapping held): **2/5**
- Zero-shot success on the unseen blue square: **0/5**
- Predicted-word AND hit (genuine syntax): **0/5**

## How to read a run

- **compositional + predicted word + hit** → genuine composition: the pair built a *syntax*, and the receiver parsed a word it had never seen from its parts.
- **hit but word not predicted** → inference by elimination: object 4 is the only unused option, so the receiver can be right without any grammar.
- **holistic + miss** → the known default for emergent languages: whole-word codes that don't generalize to novel objects.
- **compositional + miss** → a one-sided grammar: the sender coded systematically but the receiver never learned to decode it compositionally.

*Provenance: every round (including raw model replies and both private notebooks) is in `kumi-provenance.jsonl`. Parse failures were substituted (▲▲ / guess 1) and flagged there.*

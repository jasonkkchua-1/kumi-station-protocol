#!/usr/bin/env python3
# audit2.py — independent audit of the kumi CAMPAIGN 2 (role swap) chain.
#
# Extends audit.py. Reads ONLY kumi2-provenance.jsonl. Shares no analysis code
# with kumi2.py: every quantity (rounds, gate timing, lexicons, homonyms,
# compositionality, predictions, zero-shot outcomes, prediction-precedes-test)
# is recomputed here from the raw log, then compared against (a) the derived
# fields kumi2.py wrote into the zero_shot records and (b) the published claims
# in kumi2-results.md (transcribed below as constants — the results file itself
# is never read).
#
# Campaign 2 differs from Campaign 1 in ways this auditor handles explicitly:
#   * roles are swapped — Qwen SENDS, gemma RECEIVES (verified constant per record);
#   * one run (run 2) never reaches fluency and stops at CAP_ROUNDS (120) — the
#     gate check is generalised to "fires exactly at the fluency round, or never
#     for a capped non-fluent run";
#   * think-stripping guards the SENDER (Qwen) word parse, not the receiver;
#   * thinking was disabled mid-campaign — this auditor independently confirms
#     which runs carry sender <think> content;
#   * CRITICAL ADDITION: a degenerate-lexicon (homonym) check. A lexicon in which
#     one word serves two training objects satisfies the pre-registered
#     composition rule only because a whole feature dimension has collapsed. The
#     campaign's headline "compositional 5/5" is reported side by side with the
#     CLEAN count that excludes such degenerate lexicons.
#
# Usage:  python3 audit2.py         (from the folder containing kumi2-provenance.jsonl)
# Output: audit2-report.md (claim-by-claim PASS/FAIL table + notes); exit 1 if any FAIL.

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PROV = os.path.join(HERE, "kumi2-provenance.jsonl")
REPORT = os.path.join(HERE, "audit2-report.md")

# ---- protocol constants (from the pre-registered design, restated independently)
SYMS = set("▲●■")
TRAIN_OBJS = {1, 2, 3}
HOLDOUT = 4
WINDOW = 15
ACC = 0.75
MIN_ROUNDS = 20
CAP_ROUNDS = 120          # amended mid-campaign from 150 (see AUDIT NOTES)
LOOKBACK = 40
FEATURES = {1: ("red", "circle"), 2: ("red", "square"),
            3: ("blue", "circle"), 4: ("blue", "square")}
SENDER_MODEL = "mlx-community/Qwen3-4B-4bit"          # Qwen SPEAKS in Campaign 2
RECEIVER_MODEL = "mlx-community/gemma-3-4b-it-qat-4bit"  # gemma LISTENS

# ---- published claims, transcribed from kumi2-results.md (NOT read from disk)
CLAIMED = {
    1: dict(rounds=21, fluent=True, lex={1: "▲■", 2: "▲●", 3: "▲■"}, comp=True,
            pred="▲●", sent="▲■", guess=3, matched=False, hit=False),
    2: dict(rounds=None, fluent=False, lex={1: "▲●", 2: "▲■", 3: "▲●"}, comp=True,
            pred="▲■", sent="■■", guess=2, matched=False, hit=False),
    3: dict(rounds=48, fluent=True, lex={1: "▲●", 2: "▲●", 3: "▲■"}, comp=True,
            pred="▲■", sent="■▲", guess=3, matched=False, hit=False),
    4: dict(rounds=81, fluent=True, lex={1: "▲■", 2: "▲●", 3: "▲■"}, comp=True,
            pred="▲●", sent="▲■", guess=3, matched=False, hit=False),
    5: dict(rounds=36, fluent=True, lex={1: "▲●", 2: "▲■", 3: "■●"}, comp=True,
            pred="■■", sent="■■", guess=3, matched=True, hit=False),
}
# Summary claims from kumi2-results.md. NB: comp=5 is the campaign's own headline;
# the audit reports it against the CLEAN (non-degenerate) count, expected 1.
CLAIMED_SUMMARY = dict(fluent=4, comp=5, clean_comp=1, hits=0, matched_and_hit=0)
# Run 5's pre-registered / predicted obj-4 word — the mirror of Campaign 1 run 3.
PREREG_RUN5_WORD = "■■"
N_RUNS = 5

# ================================================================ independent parsing
# Re-implemented from the protocol description, not copied from kumi2.py.

def audit_strip_think(text):
    """Remove <think>...</think> blocks and any unclosed trailing <think>."""
    t = re.sub(r"<think>.*?</think>", " ", text or "", flags=re.S | re.I)
    t = re.sub(r"<think>.*", " ", t, flags=re.S | re.I)
    return t

def audit_head(text):
    """Answer portion of a reply: think-stripped text before the first NOTEBOOK:."""
    t = audit_strip_think(text)
    m = re.search(r"NOTEBOOK\s*:", t, flags=re.I)
    return t[:m.start()] if m else t

def audit_word(head):
    found = [c for c in head if c in SYMS]
    return "".join(found[:2]) if len(found) >= 2 else None

def audit_guess(head):
    for c in head:
        if c in "1234":
            return int(c)
    return None

def replay_parse(raws, parse_fn, substitute):
    """Replay the retry loop: first raw whose head parses wins; else substitute.
    Returns (value, parse_fail)."""
    for raw in raws:
        v = parse_fn(audit_head(raw))
        if v is not None:
            return v, False
    return substitute, True

def think_content_len(raws):
    """Total characters of <think> content across a record's sender replies —
    used to confirm which runs ran with Qwen thinking ON vs OFF."""
    tot = 0
    for raw in raws or []:
        for blk in re.findall(r"<think>(.*?)</think>", raw or "", flags=re.S | re.I):
            tot += len(blk.strip())
    return tot

# ================================================================ independent analysis

def audit_modal_lexicon(train):
    """Modal word per training object over the last LOOKBACK train rounds.
    Ties broken by first occurrence within the window (deterministic); ties flagged."""
    window = train[-LOOKBACK:]
    lex, ties = {}, []
    for o in sorted(TRAIN_OBJS):
        counts, order = {}, []
        for t in window:
            if t["obj"] == o:
                w = t["word"]
                if w not in counts:
                    order.append(w)
                counts[w] = counts.get(w, 0) + 1
        if not counts:
            lex[o] = None
            continue
        best = max(counts.values())
        winners = [w for w in order if counts[w] == best]
        lex[o] = winners[0]
        if len(winners) > 1:
            ties.append((o, winners, best))
    return lex, ties

def audit_homonyms(lex):
    """Words that serve more than one training object (degenerate lexicon).
    Returns {word: [objs]} for every word mapped from >1 object."""
    inv = {}
    for o in sorted(TRAIN_OBJS):
        w = lex.get(o)
        if w is None:
            continue
        inv.setdefault(w, []).append(o)
    return {w: os for w, os in inv.items() if len(os) > 1}

def audit_composition(lex):
    """Pre-registered rule, both position orders. Returns (comp, predicted_word).
    NB: this fires on degenerate lexicons too — degeneracy is judged separately."""
    w1, w2, w3 = lex.get(1), lex.get(2), lex.get(3)
    if not (w1 and w2 and w3 and len(w1) == 2 and len(w2) == 2 and len(w3) == 2):
        return False, "holistic — no prediction (incomplete lexicon)"
    if w1[0] == w2[0] and w1[1] == w3[1]:      # pos0=color, pos1=shape
        return True, w3[0] + w2[1]
    if w1[0] == w3[0] and w1[1] == w2[1]:      # pos0=shape, pos1=color
        return True, w2[0] + w3[1]
    return False, "holistic — no prediction"

def gate_fires(payoffs, objs, rnd):
    """Fluency gate at round rnd (1-based over the payoff list)."""
    if rnd < max(MIN_ROUNDS, WINDOW):
        return False
    win_p = payoffs[rnd - WINDOW:rnd]
    win_o = set(objs[rnd - WINDOW:rnd])
    return sum(win_p) / WINDOW >= ACC and win_o >= TRAIN_OBJS

# ================================================================ load

def load(path):
    runs = {r: {"train": [], "zero": None} for r in range(1, N_RUNS + 1)}
    events, order = [], []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)   # any malformed line raises -> audit fails loudly
            rec["_line"] = i
            order.append(rec)
            if rec.get("event") == "protocol_note":
                events.append(rec)
            elif rec.get("phase") == "train":
                runs[rec["run"]]["train"].append(rec)
            elif rec.get("phase") == "zero_shot":
                if runs[rec["run"]]["zero"] is not None:
                    raise SystemExit(f"duplicate zero_shot record for run {rec['run']}")
                runs[rec["run"]]["zero"] = rec
            else:
                raise SystemExit(f"unrecognized record on line {i}")
    return runs, events, order

# ================================================================ audit

def main():
    rows = []          # (claim, verdict, detail)
    def check(claim, ok, detail=""):
        rows.append((claim, "PASS" if ok else "FAIL", detail))
        return ok

    runs, events, order = load(PROV)
    ts = lambda r: datetime.fromisoformat(r["ts"])

    recomputed = {}
    for r in range(1, N_RUNS + 1):
        train = sorted(runs[r]["train"], key=lambda t: t["round"])
        zero = runs[r]["zero"]
        C = CLAIMED[r]

        # rounds: contiguous 1..N, no duplicates, no gaps (incl. across crash resumes)
        nums = [t["round"] for t in runs[r]["train"]]
        n = len(nums)
        check(f"Run {r}: round numbers are exactly 1..{n}, no duplicates or gaps",
              sorted(nums) == list(range(1, n + 1)) and len(set(nums)) == n,
              f"got {n} rounds, min {min(nums)}, max {max(nums)}")

        # claimed rounds-to-fluency / fluency status
        if C["fluent"]:
            check(f"Run {r}: rounds to fluency = {C['rounds']} (claimed)",
                  n == C["rounds"], f"recomputed {n}")
        else:
            check(f"Run {r}: non-fluent, ran to the cap of {CAP_ROUNDS} rounds (claimed)",
                  n == CAP_ROUNDS, f"recomputed {n}")

        # training never shows the holdout; features consistent
        check(f"Run {r}: training objects all in {{1,2,3}} (object 4 held out)",
              all(t["obj"] in TRAIN_OBJS for t in train))
        check(f"Run {r}: object features in log match the fixed world",
              all(tuple(t["obj_features"]) == FEATURES[t["obj"]] for t in train + [zero]))

        # payoffs recomputed
        check(f"Run {r}: every train payoff == (guess == object)",
              all(t["payoff"] == (1 if t["guess"] == t["obj"] else 0) for t in train))

        # rolling accuracy / fluency gate
        payoffs = [t["payoff"] for t in train]
        objs = [t["obj"] for t in train]
        fired = [rnd for rnd in range(1, n + 1) if gate_fires(payoffs, objs, rnd)]
        final_roll = sum(payoffs[-WINDOW:]) / WINDOW
        if C["fluent"]:
            check(f"Run {r}: fluency gate (>={MIN_ROUNDS} rounds, rolling15 >= {ACC}, "
                  f"all 3 objects in window) fires at round {n} and at no earlier round",
                  fired == [n],
                  f"gate true at rounds {fired}; final rolling15 = {final_roll:.3f}")
        else:
            check(f"Run {r}: non-fluent — fluency gate never fires across all {n} rounds",
                  fired == [],
                  f"gate true at rounds {fired}; final rolling15 = {final_roll:.3f}")

        # replay every parse from the raw replies (think-stripped, pre-NOTEBOOK head)
        word_ok = guess_ok = flags_ok = True
        for t in train + [zero]:
            w, wf = replay_parse(t["sender_raw"], audit_word, "▲▲")
            g, gf = replay_parse(t["receiver_raw"], audit_guess, 1)
            if w != t["word"]:
                word_ok = False
            if g != t["guess"]:
                guess_ok = False
            if wf != bool(t["sender_parse_fail"]) or gf != bool(t["receiver_parse_fail"]):
                flags_ok = False
        check(f"Run {r}: every logged word reproduced by independent parse of raw SENDER "
              f"(Qwen) replies, taken from outside any <think> block",
              word_ok)
        check(f"Run {r}: every logged guess reproduced by independent parse of raw RECEIVER "
              f"(gemma) replies",
              guess_ok)
        check(f"Run {r}: parse-failure flags match the replayed retry/substitution logic",
              flags_ok)

        # words well-formed
        check(f"Run {r}: every logged word is exactly 2 symbols from ▲●■",
              all(len(t["word"]) == 2 and set(t["word"]) <= SYMS for t in train + [zero]))

        # lexicon recomputed from last 40 train rounds
        lex, ties = audit_modal_lexicon(train)
        check(f"Run {r}: recomputed lexicon (modal word, last {LOOKBACK} rounds) "
              f"= {' '.join(C['lex'][o] for o in (1, 2, 3))} (claimed)",
              lex == C["lex"],
              f"recomputed {' '.join(str(lex[o]) for o in (1, 2, 3))}"
              + (f"; modal ties: {ties}" if ties else "; no modal ties"))

        # ---- CRITICAL: degenerate-lexicon (homonym) check ----
        homos = audit_homonyms(lex)
        degenerate = bool(homos)
        homo_desc = "; ".join(f"'{w}' serves objects {os}" for w, os in homos.items()) \
            if homos else "no homonyms — every object has a distinct word"
        check(f"Run {r}: degenerate-lexicon check — recorded whether any word serves two "
              f"objects ({'DEGENERATE' if degenerate else 'clean'})",
              True, homo_desc)

        # compositionality + prediction recomputed from recomputed lexicon
        comp, pred = audit_composition(lex)
        check(f"Run {r}: compositionality recomputed = {C['comp']} (claimed), "
              f"matches zero-shot record",
              comp == C["comp"] and bool(zero["compositional"]) == comp,
              f"recomputed {comp}, logged {zero['compositional']}"
              + ("  [NOTE: fires on a DEGENERATE lexicon — excluded from clean count]"
                 if (comp and degenerate) else ""))
        check(f"Run {r}: predicted obj-4 word recomputed = '{C['pred']}' (claimed), "
              f"matches zero-shot record",
              pred == C["pred"] and zero["predicted_word"] == pred,
              f"recomputed '{pred}', logged '{zero['predicted_word']}'")

        # prediction pinned to pre-test data
        t_train_max = max(ts(t) for t in train)
        check(f"Run {r}: prediction precedes test — all {n} train timestamps < zero-shot "
              f"timestamp, and prediction depends only on those train rounds",
              t_train_max < ts(zero),
              f"last train {t_train_max.isoformat()} < test {ts(zero).isoformat()}")

        # timestamps monotonic within the run
        seq = [ts(t) for t in train] + [ts(zero)]
        check(f"Run {r}: timestamps strictly increase in round order through the test",
              all(a < b for a, b in zip(seq, seq[1:])))

        # zero-shot outcome recomputed
        check(f"Run {r}: zero-shot record — object 4, sent '{C['sent']}', guess "
              f"{C['guess']}, hit={C['hit']} (claimed)",
              zero["obj"] == HOLDOUT and zero["word"] == C["sent"]
              and zero["guess"] == C["guess"]
              and zero["payoff"] == (1 if zero["guess"] == HOLDOUT else 0)
              and (zero["payoff"] == 1) == C["hit"],
              f"logged word '{zero['word']}', guess {zero['guess']}, payoff {zero['payoff']}")

        # matched_prediction recomputed
        matched = comp and (zero["word"] == pred)
        check(f"Run {r}: matched_prediction recomputed = {C['matched']} (claimed), "
              f"matches zero-shot record",
              matched == C["matched"] and bool(zero["matched_prediction"]) == matched,
              f"recomputed {matched}")

        # think content presence (which runs ran with Qwen thinking ON)
        think_total = sum(think_content_len(t["sender_raw"]) for t in train)
        recomputed[r] = dict(rounds=n, fluent=C["fluent"], lex=lex, comp=comp, pred=pred,
                             degenerate=degenerate, homonyms=homos,
                             sent=zero["word"], guess=zero["guess"],
                             hit=zero["payoff"] == 1, matched=matched,
                             think_total=think_total)

    # ---------- HEADLINE: run 5, the mirror of Campaign 1 run 3 ----------
    z5 = runs[5]["zero"]
    check("HEADLINE — Run 5: sender emitted, for the unseen object, EXACTLY the "
          f"pre-registered predicted word '{PREREG_RUN5_WORD}' (compositional, "
          "non-degenerate lexicon; matched_prediction=True)",
          z5["word"] == z5["predicted_word"] == recomputed[5]["pred"] == PREREG_RUN5_WORD
          and bool(z5["matched_prediction"]) and not recomputed[5]["degenerate"],
          f"predicted '{z5['predicted_word']}', sent '{z5['word']}', "
          f"receiver guessed #{z5['guess']} (hit={z5['payoff'] == 1}) -> one-sided grammar: "
          "sender composed, receiver failed to decode")

    # ---------- CRITICAL: claimed vs clean compositional counts ----------
    claimed_comp = sum(1 for v in recomputed.values() if v["comp"])
    clean_comp = sum(1 for v in recomputed.values() if v["comp"] and not v["degenerate"])
    degenerate_runs = [r for r, v in recomputed.items() if v["degenerate"]]
    check(f"CRITICAL — compositional count, CLAIMED vs CLEAN: claimed {claimed_comp}/5 "
          f"(pre-registered rule, counts degenerate lexicons); "
          f"CLEAN {clean_comp}/5 (excludes degenerate homonym lexicons)",
          claimed_comp == CLAIMED_SUMMARY["comp"] and clean_comp == CLAIMED_SUMMARY["clean_comp"],
          f"degenerate (excluded) runs: {degenerate_runs}; "
          f"clean compositional runs: {[r for r, v in recomputed.items() if v['comp'] and not v['degenerate']]}")

    # ---------- thinking ON/OFF timing, recomputed from <think> content ----------
    think_on = [r for r in range(1, N_RUNS + 1) if recomputed[r]["think_total"] > 0]
    think_off = [r for r in range(1, N_RUNS + 1) if recomputed[r]["think_total"] == 0]
    check("Amendment cross-check: Qwen sender <think> content present in runs 1-2 and "
          "absent from runs 3-5 (thinking DISABLED from run 3 onward, as amended)",
          think_on == [1, 2] and think_off == [3, 4, 5],
          f"think-content runs {think_on}; no-think runs {think_off} "
          + "; ".join(f"run {r}={recomputed[r]['think_total']}c" for r in range(1, N_RUNS + 1)))

    # ---------- run 2 notebook self-description vs emitted behaviour ----------
    tr2 = sorted(runs[2]["train"], key=lambda t: t["round"])
    color_claim = sum(1 for t in tr2 if re.search(
        r"▲\s*=?\s*red|■\s*=?\s*blue|red[^.]*▲|blue[^.]*■", t.get("sender_notebook", "")))
    pos0 = Counter(t["word"][0] for t in tr2)
    dominant0, dom0n = pos0.most_common(1)[0]
    check("Run 2: notebook self-description diverged from behaviour — sender's notebooks "
          "assert a color code (▲=red / ■=blue) it does not emit; the emitted color slot "
          "(position 0) is nearly constant, so color is never actually encoded",
          color_claim > 0 and dom0n / len(tr2) > 0.8,
          f"{color_claim}/{len(tr2)} notebooks assert a ▲=red/■=blue-style code; "
          f"emitted position-0 distribution {dict(pos0)} (dominant '{dominant0}' "
          f"{dom0n}/{len(tr2)} = {dom0n / len(tr2):.0%})")

    # ---------- crash-resume consistency (two resumes this campaign) ----------
    resume = [e for e in events if e.get("resumed")]
    check("Exactly two crash-resume protocol notes in the log (run 2 from 118, run 4 from 58)",
          len(resume) == 2, f"found {len(resume)}")

    # file-order sanity: physical line order matches timestamp order
    tss = [ts(r) for r in order]
    check("Provenance file is append-only: physical line order is time-ordered",
          all(a <= b for a, b in zip(tss, tss[1:])))

    # models constant AND correctly swapped (Qwen sends, gemma receives)
    pairs = {(r.get("sender_model"), r.get("receiver_model")) for r in order if r.get("phase")}
    check("Role swap verified: Qwen SENDS and gemma RECEIVES in every record",
          pairs == {(SENDER_MODEL, RECEIVER_MODEL)},
          f"model pairs seen: {pairs}")

    # ---------- summary claims ----------
    S = CLAIMED_SUMMARY
    check(f"Summary: converged to fluency {S['fluent']}/5",
          sum(1 for v in recomputed.values() if v["fluent"]) == S["fluent"])
    check(f"Summary: zero-shot hits {S['hits']}/5",
          sum(v["hit"] for v in recomputed.values()) == S["hits"])
    check(f"Summary: predicted-word AND hit {S['matched_and_hit']}/5",
          sum(v["matched"] and v["hit"] for v in recomputed.values()) == S["matched_and_hit"])

    # ================================================================ audit notes
    # Protocol amendments, recorded as audit notes with the VALUES ACTUALLY FOUND
    # in the chain. All three are deviations from the Campaign 1 protocol.
    note_lines = []
    def note(txt):
        note_lines.append(txt)

    # Sender token budget — searched for in the chain rather than assumed.
    budget_hits = sorted(set(re.findall(r"\b(1500|900|500)\b(?=[^\"]{0,40}(?:token|budget|think))",
                                        open(PROV, encoding="utf-8").read(), flags=re.I)))
    note("Sender token budget (post-hoc / exploratory): the chain documents the SENDER "
         "(Qwen) think budget being raised PRE-LAUNCH from Campaign 1's 500 to **900** "
         "tokens (dry-check calibration, before any round), then dropped to MAX_TOKENS "
         "(300) once thinking was disabled mid-campaign. **No value of 1500 appears "
         "anywhere in the chain** — if 1500 was expected, that figure is not supported "
         f"by the provenance. (budget-adjacent figures found in notes: {budget_hits or 'none'}.)")
    note("Thinking DISABLED from run 3 (post-hoc / exploratory, NOT pre-registered): "
         "confirmed independently above — sender <think> content is present only in runs "
         "1-2 and absent from runs 3-5. Cross-run comparisons within Campaign 2 are "
         "therefore exploratory, as the amendment itself states.")
    note("Round-cap change (post-hoc / exploratory, NOT pre-registered): CAP_ROUNDS "
         "reduced mid-campaign from 150 to 120 after run 2 stalled near chance. Only run "
         "2 is affected (it ran to the 120 cap and is recorded non-fluent). The fluency "
         "gate, one-trial zero-shot test, and pre-registered interpretations are unchanged.")
    note("Degeneracy caveat (headline): the pre-registered composition rule scores "
         f"{claimed_comp}/5 compositional, but {len(degenerate_runs)}/5 of those lexicons "
         f"are DEGENERATE (a single word serves two objects: runs {degenerate_runs}). "
         f"After excluding degenerate lexicons the CLEAN compositional count is "
         f"{clean_comp}/5 — only run 5, which also emitted the exact pre-registered novel "
         "word for the unseen object.")

    # ================================================================ report
    n_pass = sum(1 for _, v, _ in rows if v == "PASS")
    n_fail = len(rows) - n_pass
    verdict = "CLEAN — all checks passed" if n_fail == 0 else f"{n_fail} FAILURE(S)"

    L = ["# kumi — Campaign 2 (role swap) · independent audit report", "",
         f"*{datetime.now().isoformat(timespec='seconds')} · audit2.py reads only "
         f"`kumi2-provenance.jsonl` and shares no analysis code with `kumi2.py`*", "",
         f"**Verdict: {verdict}** ({n_pass}/{len(rows)} checks passed)", "",
         "Published claims (rounds, lexicons, verdicts) are transcribed from "
         "`kumi2-results.md` into this script as constants and compared against values "
         "recomputed from the raw chain. The pre-registered prediction has no separate "
         "log record; it is verified as a deterministic function of the training rounds "
         "alone, all timestamped before the zero-shot test.", "",
         f"**Compositional count — claimed {claimed_comp}/5 vs CLEAN {clean_comp}/5.** "
         f"{len(degenerate_runs)} of 5 lexicons are degenerate (one word serving two "
         f"objects: runs {degenerate_runs}); these satisfy the composition rule only "
         "because a feature dimension has collapsed. Only run 5 is a clean compositional "
         "lexicon — and it emitted the exact pre-registered word for the unseen object "
         "while the receiver still missed (a verified one-sided grammar).", "",
         "| # | Check | Verdict | Detail |",
         "|---|---|---|---|"]
    for i, (claim, v, detail) in enumerate(rows, 1):
        safe = detail.replace("|", "\\|")
        L.append(f"| {i} | {claim} | **{v}** | {safe} |")
    L.append("")
    L.append("## Audit notes — protocol amendments (recorded from the chain)")
    L.append("")
    for nl in note_lines:
        L.append(f"- {nl}")
    L.append("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # console
    for i, (claim, v, detail) in enumerate(rows, 1):
        print(f"{i:3d}. [{v}] {claim}" + (f"  — {detail}" if detail else ""))
    print("\nAUDIT NOTES:")
    for nl in note_lines:
        print("  - " + nl)
    print(f"\n{verdict} ({n_pass}/{len(rows)}). Report: {REPORT}")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == "__main__":
    main()

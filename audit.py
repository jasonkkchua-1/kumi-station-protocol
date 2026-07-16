#!/usr/bin/env python3
# audit.py — independent audit of the kumi campaign.
#
# Reads ONLY kumi-provenance.jsonl. Shares no code with kumi.py: every quantity
# (rounds, rolling accuracies, lexicons, compositionality, predictions, zero-shot
# outcomes) is recomputed here from the raw log, then compared against (a) the
# derived fields kumi.py wrote into the zero-shot records and (b) the published
# claims in kumi-results.md (transcribed below as constants — the results file
# itself is never read).
#
# Usage:  python3 audit.py            (from the folder containing kumi-provenance.jsonl)
# Output: audit-report.md (claim-by-claim PASS/FAIL table); exit 1 if any FAIL.

import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PROV = os.path.join(HERE, "kumi-provenance.jsonl")
REPORT = os.path.join(HERE, "audit-report.md")

# ---- protocol constants (from the pre-registered design, restated independently)
SYMS = set("▲●■")
TRAIN_OBJS = {1, 2, 3}
HOLDOUT = 4
WINDOW = 15
ACC = 0.75
MIN_ROUNDS = 20
LOOKBACK = 40
FEATURES = {1: ("red", "circle"), 2: ("red", "square"),
            3: ("blue", "circle"), 4: ("blue", "square")}

# ---- published claims, transcribed from kumi-results.md (NOT read from disk)
CLAIMED = {
    1: dict(rounds=49, lex={1: "●●", 2: "▲▲", 3: "●■"}, comp=False,
            pred="holistic — no prediction", sent="■■", guess=2, matched=False, hit=False),
    2: dict(rounds=23, lex={1: "●■", 2: "■●", 3: "●■"}, comp=False,
            pred="holistic — no prediction", sent="●■", guess=3, matched=False, hit=False),
    3: dict(rounds=33, lex={1: "■●", 2: "■■", 3: "●●"}, comp=True,
            pred="●■", sent="●■", guess=1, matched=True, hit=False),
    4: dict(rounds=20, lex={1: "▲●", 2: "▲■", 3: "■●"}, comp=True,
            pred="■■", sent="■▲", guess=2, matched=False, hit=False),
    5: dict(rounds=21, lex={1: "●▲", 2: "■●", 3: "●■"}, comp=False,
            pred="holistic — no prediction", sent="■●", guess=2, matched=False, hit=False),
}
CLAIMED_SUMMARY = dict(fluent=5, comp=2, hits=0, matched_and_hit=0)
N_RUNS = 5

# ================================================================ independent parsing
# Re-implemented from the protocol description, not copied from kumi.py.

def audit_strip_think(text):
    """Remove <think>...</think> blocks and any unclosed trailing <think>."""
    t = re.sub(r"<think>.*?</think>", " ", text or "", flags=re.S | re.I)
    t = re.sub(r"<think>.*", " ", t, flags=re.S | re.I)
    return t

def audit_head(text):
    """Answer portion of a reply: think-stripped text before the first NOTEBOOK: marker."""
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

def think_leaked(raws, parse_fn, substitute, logged_value, logged_fail):
    """<think> leakage means the logged value was influenced by think content:
    either (a) the logged value differs from what the think-stripped replay
    (including the documented substitution rule) produces, or (b) nothing was
    parseable outside think blocks yet the record was NOT flagged as a parse
    failure (i.e. the value silently came from inside think). A flagged
    substitution is NOT leakage, even if the discarded think text happens to
    contain the same digit/symbols — the value came from the substitution rule."""
    stripped, failed = replay_parse(raws, parse_fn, substitute)
    if stripped != logged_value:
        return True
    if failed and not logged_fail:
        return True
    return False

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

def audit_composition(lex):
    """Pre-registered rule, both position orders. Returns (comp, predicted_word)."""
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

    # ---------- per-run structural + recomputation checks ----------
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

        # claimed rounds-to-fluency
        check(f"Run {r}: rounds to fluency = {C['rounds']} (claimed)",
              n == C["rounds"], f"recomputed {n}")

        # training never shows the holdout; features consistent
        check(f"Run {r}: training objects all in {{1,2,3}} (object 4 held out)",
              all(t["obj"] in TRAIN_OBJS for t in train))
        check(f"Run {r}: object features in log match the fixed world",
              all(tuple(t["obj_features"]) == FEATURES[t["obj"]] for t in train + [zero]))

        # payoffs recomputed
        check(f"Run {r}: every train payoff == (guess == object)",
              all(t["payoff"] == (1 if t["guess"] == t["obj"] else 0) for t in train))

        # rolling accuracy / fluency gate: fires at final round, never earlier
        payoffs = [t["payoff"] for t in train]
        objs = [t["obj"] for t in train]
        fired = [rnd for rnd in range(1, n + 1) if gate_fires(payoffs, objs, rnd)]
        final_roll = sum(payoffs[-WINDOW:]) / WINDOW
        check(f"Run {r}: fluency gate (≥{MIN_ROUNDS} rounds, rolling15 ≥ {ACC}, "
              f"all 3 objects in window) fires at round {n} and at no earlier round",
              fired == [n],
              f"gate true at rounds {fired}; final rolling15 = {final_roll:.3f}")

        # replay every parse from the raw replies (think-stripped, pre-NOTEBOOK head)
        word_ok = guess_ok = flags_ok = True
        leak, subs = [], []
        for t in train + [zero]:
            w, wf = replay_parse(t["sender_raw"], audit_word, "▲▲")
            g, gf = replay_parse(t["receiver_raw"], audit_guess, 1)
            if w != t["word"]:
                word_ok = False
            if g != t["guess"]:
                guess_ok = False
            if wf != bool(t["sender_parse_fail"]) or gf != bool(t["receiver_parse_fail"]):
                flags_ok = False
            if think_leaked(t["receiver_raw"], audit_guess, 1,
                            t["guess"], bool(t["receiver_parse_fail"])) or \
               think_leaked(t["sender_raw"], audit_word, "▲▲",
                            t["word"], bool(t["sender_parse_fail"])):
                leak.append(t["round"])
            if t["receiver_parse_fail"] or t["sender_parse_fail"]:
                subs.append(t["round"])
        check(f"Run {r}: every logged word reproduced by independent parse of raw sender replies",
              word_ok)
        check(f"Run {r}: every logged guess reproduced by independent parse of raw receiver replies",
              guess_ok)
        check(f"Run {r}: parse-failure flags match the replayed retry/substitution logic",
              flags_ok)
        check(f"Run {r}: no <think> leakage — every parsed word/guess comes from "
              f"think-stripped text or the flagged substitution rule, never from think content",
              not leak,
              (f"leaks at rounds {leak}" if leak else "")
              + (f"flagged substitution rounds (not leakage): {subs}" if subs else "no substitutions"))

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

        # compositionality + prediction recomputed from recomputed lexicon
        comp, pred = audit_composition(lex)
        check(f"Run {r}: compositionality recomputed = {C['comp']} (claimed), "
              f"matches zero-shot record",
              comp == C["comp"] and bool(zero["compositional"]) == comp,
              f"recomputed {comp}, logged {zero['compositional']}")
        check(f"Run {r}: predicted obj-4 word recomputed = '{C['pred']}' (claimed), "
              f"matches zero-shot record",
              pred == C["pred"] and zero["predicted_word"] == pred,
              f"recomputed '{pred}', logged '{zero['predicted_word']}'")

        # prediction is pinned to pre-test data: it is a deterministic function of the
        # train rounds only, and every train round's timestamp precedes the zero-shot ts
        t_train_max = max(ts(t) for t in train)
        check(f"Run {r}: prediction precedes test — all {n} train timestamps < zero-shot "
              f"timestamp, and prediction depends only on those train rounds",
              t_train_max < ts(zero),
              f"last train {t_train_max.isoformat()} < test {ts(zero).isoformat()}")

        # timestamps monotonic within the run (in round order, then the test)
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

        recomputed[r] = dict(rounds=n, lex=lex, comp=comp, pred=pred,
                             sent=zero["word"], guess=zero["guess"],
                             hit=zero["payoff"] == 1, matched=matched)

    # ---------- headline check: run 3 ----------
    z3 = runs[3]["zero"]
    check("HEADLINE — Run 3: the word the sender actually sent for the unseen object "
          "exactly equals the pre-registered predicted word",
          z3["word"] == z3["predicted_word"] == recomputed[3]["pred"] == "●■",
          f"predicted '{z3['predicted_word']}', sent '{z3['word']}'")

    # ---------- crash-resume consistency ----------
    resume = [e for e in events if e.get("resumed")]
    check("Exactly one crash-resume protocol note in the log", len(resume) == 1,
          f"found {len(resume)}")
    if len(resume) == 1:
        ev = resume[0]
        pre = [t["round"] for t in runs[1]["train"] if ts(t) < ts(ev)]
        post = [t["round"] for t in runs[1]["train"] if ts(t) > ts(ev)]
        check("Resume note ('run 1 continues from round 29') consistent with timestamps: "
              "rounds 1-28 precede the note, rounds 29+ follow it, nothing lost or repeated",
              sorted(pre) == list(range(1, 29)) and sorted(post) == list(range(29, 50)),
              f"pre-crash rounds {min(pre)}-{max(pre)}, post-resume rounds {min(post)}-{max(post)}")

    # file-order sanity: physical line order matches timestamp order
    tss = [ts(r) for r in order]
    check("Provenance file is append-only: physical line order is time-ordered",
          all(a <= b for a, b in zip(tss, tss[1:])))

    # models constant
    check("Sender/receiver models identical in every record (gemma sends, qwen receives)",
          len({(r.get("sender_model"), r.get("receiver_model"))
               for r in order if r.get("phase")}) == 1)

    # ---------- summary claims ----------
    S = CLAIMED_SUMMARY
    check(f"Summary: converged to fluency {S['fluent']}/5",
          sum(1 for r in recomputed.values() if r["rounds"] is not None) == S["fluent"])
    check(f"Summary: compositional lexicon {S['comp']}/5",
          sum(r["comp"] for r in recomputed.values()) == S["comp"])
    check(f"Summary: zero-shot hits {S['hits']}/5",
          sum(r["hit"] for r in recomputed.values()) == S["hits"])
    check(f"Summary: predicted-word AND hit {S['matched_and_hit']}/5",
          sum(r["matched"] and r["hit"] for r in recomputed.values()) == S["matched_and_hit"])

    # ================================================================ report
    n_pass = sum(1 for _, v, _ in rows if v == "PASS")
    n_fail = len(rows) - n_pass
    verdict = "CLEAN — all claims verified" if n_fail == 0 else f"{n_fail} FAILURE(S)"

    L = ["# kumi — independent audit report", "",
         f"*{datetime.now().isoformat(timespec='seconds')} · audit.py reads only "
         f"`kumi-provenance.jsonl` and shares no code with `kumi.py`*", "",
         f"**Verdict: {verdict}** ({n_pass}/{len(rows)} checks passed)", "",
         "Published claims (rounds, lexicons, verdicts) are transcribed from "
         "`kumi-results.md` into the audit script as constants and compared against "
         "values recomputed from the raw log. The pre-registered prediction has no "
         "separate log record; it is verified as a deterministic function of the "
         "training rounds alone, all of which are timestamped before the zero-shot test.", "",
         "| # | Claim | Verdict | Detail |",
         "|---|---|---|---|"]
    for i, (claim, v, detail) in enumerate(rows, 1):
        L.append(f"| {i} | {claim} | **{v}** | {detail} |")
    L.append("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # console table
    width = max(len(c) for c, _, _ in rows)
    for i, (claim, v, detail) in enumerate(rows, 1):
        print(f"{i:3d}. [{v}] {claim}" + (f"  — {detail}" if detail else ""))
    print(f"\n{verdict} ({n_pass}/{len(rows)}). Report: {REPORT}")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == "__main__":
    main()

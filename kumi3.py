#!/usr/bin/env python3
# 組 kumi3 — FORCED-LISTENING ABLATION.
#
# Proposed by external review (Gemini 3.1 Pro, 2026-07-18) and adopted as the
# priority experiment. Question: in Campaigns 1-2, receivers decoded the composed
# zero-shot word 0/10 times. Is that because 4B receivers LACK THE CAPACITY to
# decompose words into parts — or because their learning context was POISONED by
# the LLM sender's noisy early exploration?
#
# This ablation removes the second explanation: the sender is a HARDCODED,
# DETERMINISTIC, PERFECTLY INJECTIVE COMPOSITIONAL SCRIPT. It never errs, never
# drifts, never explores. The receiver (an LLM) trains against this ideal teacher
# on objects 1-3 under the standard fluency gate, then faces the standard ONE
# zero-shot trial on the held-out object 4.
#
#   Scripted code (fixed forever, pre-registered):
#     position 0 = COLOR  (red = ▲, blue = ■)
#     position 1 = SHAPE  (circle = ●, square = ■)
#     1 red circle = ▲●   2 red square = ▲■   3 blue circle = ■●
#     4 blue square = ■■  (held out; the composed test word — always sent)
#
# PRE-REGISTERED INTERPRETATIONS (committed before any round; also written as the
# first record of each provenance chain):
#   - fluent + zero-shot HIT  → the receiver decoded (or eliminated its way to)
#     the composed word under a perfect teacher. Evidence AGAINST the strong
#     capacity-limit reading. (Per-run, decode vs eliminate cannot be separated;
#     disclosed. Chance base rate per trial = 1/4. In Campaigns 1-2 receivers
#     managed 0/10 under noisy teachers.)
#   - fluent + zero-shot MISS → the receiver failed the composed word even under
#     a perfect, noise-free, injective teacher. SUPPORTS the capacity-limit
#     reading at 4B.
#   - NOT fluent (cap reached) → the receiver could not even learn three fixed,
#     clean mappings; reported as-is (a stronger capacity concern than a miss).
#   - Campaign-level (exploratory, disclosed): fluency speed vs the LLM-sender
#     campaigns; hit-rate vs the 0/10 of Campaigns 1-2 and vs the 1/4 chance rate.
#
# Protocol parity with kumi.py/kumi2.py wherever the sender is not involved:
# same world, same fluency gate (>=20 rounds, rolling-15 >= 0.75, all three
# training objects in the window), same LOOKBACK, same receiver prompts/notebook,
# same think-stripping, same parse-failure substitution (guess 1, flagged),
# same one-trial test. CAP_ROUNDS = 120 from the start (no mid-campaign change).
#
# Python 3, stdlib only. Runs ON THE MAC (needs the local model server).
#   python3 ~/Desktop/kumi/kumi3.py --receiver qwen     # Campaign A1
#   python3 ~/Desktop/kumi/kumi3.py --receiver gemma    # Campaign A2
#   python3 ~/Desktop/kumi/kumi3.py --selftest          # offline loop check, no server
#
# Outputs (per receiver, in this script's folder):
#   kumi3-results-<tag>.md
#   kumi3-provenance-<tag>.jsonl

import argparse, json, os, random, re, statistics, subprocess, sys, time
import urllib.request, urllib.error
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- world (identical)
SYMBOLS = ["▲", "●", "■"]
OBJECTS = {1: ("red", "circle"), 2: ("red", "square"),
           3: ("blue", "circle"), 4: ("blue", "square")}
TRAIN_OBJECTS = [1, 2, 3]
HOLDOUT = 4

# ---------------------------------------------------------------- the scripted sender
SCRIPT_COLOR = {"red": "▲", "blue": "■"}     # position 0
SCRIPT_SHAPE = {"circle": "●", "square": "■"}  # position 1

def scripted_word(obj):
    c, s = OBJECTS[obj]
    return SCRIPT_COLOR[c] + SCRIPT_SHAPE[s]

SCRIPT_LEX = {o: scripted_word(o) for o in (1, 2, 3, 4)}   # 4 = ■■, the composed word
assert len(set(SCRIPT_LEX.values())) == 4, "scripted code must be injective"

# ---------------------------------------------------------------- run params (parity)
FLUENCY_WINDOW = 15
FLUENCY_ACC = 0.75
FLUENCY_MIN_ROUNDS = 20
CAP_ROUNDS = 120            # fixed from the start; pre-registered, no mid-campaign change
LOOKBACK = 40
N_RUNS = 5
TEMPERATURE = 0.8
MAX_TOKENS = 300
THINK_BUDGET = 500
NOTEBOOK_WORDS = 150
HTTP_RETRIES = 3
RESTARTS_TO_NOTHINK = 2

CANDIDATE_BASES = [
    "http://localhost:1234/v1", "http://127.0.0.1:1234/v1",
    "http://localhost:12341/v1", "http://localhost:12342/v1",
    "http://localhost:11434/v1", "http://localhost:8080/v1",
    "http://localhost:8000/v1", "http://localhost:5000/v1",
]

PREREG = {
    "experiment": "kumi3 forced-listening ablation",
    "proposed_by": "external review (Gemini 3.1 Pro, 2026-07-18); adopted as priority experiment",
    "scripted_code": {"pos0_color": SCRIPT_COLOR, "pos1_shape": SCRIPT_SHAPE,
                      "lexicon": SCRIPT_LEX, "injective": True,
                      "holdout_word": SCRIPT_LEX[HOLDOUT]},
    "gate": {"min_rounds": FLUENCY_MIN_ROUNDS, "window": FLUENCY_WINDOW,
             "acc": FLUENCY_ACC, "all_objects_in_window": True,
             "cap_rounds": CAP_ROUNDS},
    "interpretations": {
        "fluent+hit": ("receiver decoded (or eliminated its way to) the composed word under a "
                       "perfect teacher — evidence AGAINST the strong capacity-limit reading; "
                       "decode-vs-eliminate not separable per run (disclosed); chance = 1/4"),
        "fluent+miss": ("receiver failed the composed word even under a perfect, noise-free, "
                        "injective teacher — SUPPORTS the capacity-limit reading at 4B"),
        "not_fluent": ("receiver could not learn three fixed clean mappings; reported as-is "
                       "(stronger capacity concern than a miss)"),
        "campaign_level": ("exploratory: fluency speed vs LLM-sender campaigns; hit-rate vs "
                           "0/10 in Campaigns 1-2 and vs the 1/4 chance rate"),
    },
    "parity_note": ("Receiver-side protocol identical to kumi.py/kumi2.py: prompts, notebook, "
                    "think-stripping, parse substitution (guess 1, flagged), one-trial test. "
                    "Sender-side scripted; sender parse failures impossible by construction."),
    "thinking_policy": ("Qwen thinking ON by default (as Campaign 1's receiver), <think> blocks "
                        "stripped before parsing and logged raw, budget 500 tokens. "
                        "PRE-SPECIFIED contingency: thinking auto-disabled (/no_think) only if "
                        "the server crashes twice (RESTARTS_TO_NOTHINK=2), logged as a protocol "
                        "note; if it fires, results are reported split at that boundary, as in "
                        "Campaign 2's amended reporting. Gemma has no think mode; N/A."),
}

# ================================================================ HTTP (as kumi.py)
def _post_stream(url, payload, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Accept": "text/event-stream"})
    chunks, plain = [], []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw_line in r:
            line = raw_line.decode("utf-8", "replace").strip()
            if not line:
                continue
            if line.startswith("data:"):
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                try:
                    obj = json.loads(body)
                except Exception:
                    continue
                for ch in obj.get("choices", []):
                    delta = ch.get("delta") or {}
                    piece = delta.get("content") or ch.get("text") \
                            or (ch.get("message") or {}).get("content") or ""
                    if piece:
                        chunks.append(piece)
            else:
                plain.append(line)
    if chunks:
        return "".join(chunks)
    if plain:
        obj = json.loads("".join(plain))
        return obj["choices"][0]["message"]["content"] or ""
    return ""

def _get(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def discover_all():
    found, seen_ids = [], set()
    for base in CANDIDATE_BASES:
        try:
            obj = _get(base + "/models", timeout=20)
            ids = [m.get("id", "") for m in obj.get("data", []) if m.get("id")]
            key = (base.split("//")[1].split(":", 1)[1], tuple(sorted(ids)))
            if ids and key not in seen_ids:
                seen_ids.add(key)
                found.append((base, ids))
        except Exception:
            continue
    return found

def chat(base, model, messages, max_tokens=None):
    payload = {"model": model, "messages": messages, "temperature": TEMPERATURE,
               "max_tokens": max_tokens or MAX_TOKENS, "stream": True}
    last = ""
    for attempt in range(HTTP_RETRIES * 2):
        try:
            return _post_stream(base + "/chat/completions", payload)
        except Exception as e:
            last = f"<http error: {e}>"
            ensure_server(base)
            time.sleep(1.5 * (attempt + 1))
    return last

# ================================================================ supervisor (as kumi.py)
SERVER_CFG = os.path.join(HERE, "kumi-server.json")

def _server_cmd():
    try:
        with open(SERVER_CFG, encoding="utf-8") as f:
            cfg = json.load(f)
        return [cfg["python"]] + list(cfg["args"])
    except Exception:
        return [sys.executable, "-m", "mlx_lm.server", "--host", "127.0.0.1", "--port", "1234"]

SUPERVISOR = {"restarts": 0}
EVENTS = {"fp": None, "notes": []}
NOTHINK = {"on": False}

def log_event(obj):
    obj = dict(obj)
    obj["event"] = "protocol_note"
    obj["ts"] = datetime.now(timezone.utc).isoformat()
    if obj.get("note"):
        EVENTS["notes"].append(obj["note"])
    if EVENTS["fp"]:
        EVENTS["fp"].write(json.dumps(obj, ensure_ascii=False) + "\n")
        EVENTS["fp"].flush()

def server_alive(base):
    try:
        _get(base + "/models", timeout=10)
        return True
    except Exception:
        return False

def ensure_server(base):
    for i in range(4):
        if server_alive(base):
            return True
        if i < 3:
            print(f"  [supervisor] server not answering (busy or dead) — probe {i+2}/4…", flush=True)
            time.sleep(15)
    SUPERVISOR["restarts"] += 1
    n = SUPERVISOR["restarts"]
    cmd = _server_cmd()
    print(f"  [supervisor] server dead — restarting (#{n}): {' '.join(cmd)}", flush=True)
    try:
        logf = open(os.path.join(HERE, "mlx-server-supervised.log"), "ab")
        subprocess.Popen(cmd, stdout=logf, stderr=logf, start_new_session=True)
    except Exception as e:
        print(f"  [supervisor] failed to spawn server: {e}", flush=True)
        return False
    for _ in range(40):
        time.sleep(3)
        if server_alive(base):
            log_event({"supervisor_restart": n,
                       "note": f"mlx server crashed and was restarted by the supervisor (restart #{n})."})
            if n >= RESTARTS_TO_NOTHINK and not NOTHINK["on"]:
                NOTHINK["on"] = True
                log_event({"nothink_enabled": True,
                           "note": (f"Server crashes persisted (restart #{n}); Qwen thinking was "
                                    f"disabled (/no_think) mid-campaign to cut memory pressure.")})
            print(f"  [supervisor] server back up (restart #{n})", flush=True)
            return True
    print("  [supervisor] could not revive the server after 120 s", flush=True)
    return False

# ================================================================ parsing (as kumi.py)
def strip_think(text):
    t = re.sub(r"<think>.*?</think>", " ", text or "", flags=re.S | re.I)
    t = re.sub(r"<think>.*", " ", t, flags=re.S | re.I)
    return t

def split_reply(text):
    t = strip_think(text)
    m = re.search(r"NOTEBOOK\s*:", t, flags=re.I)
    if not m:
        return t, None
    head, nb = t[:m.start()], t[m.end():]
    nb = " ".join(nb.split())
    words = nb.split()
    if len(words) > NOTEBOOK_WORDS:
        nb = " ".join(words[:NOTEBOOK_WORDS])
    return head, nb.strip()

def parse_guess(text):
    for c in text:
        if c in "1234":
            return int(c)
    return None

# ================================================================ receiver (as kumi.py)
RECEIVER_RULES = (
    "Game: four possible objects:\n"
    "1 = red circle   2 = red square   3 = blue circle   4 = blue square\n"
    "You are the RECEIVER. You see a 2-symbol word your partner sent and must guess "
    "which object it means.\n"
    "Reply in EXACTLY this format (two lines, nothing else):\n"
    "GUESS: <one digit 1, 2, 3 or 4>\n"
    "NOTEBOOK: <rewrite your ENTIRE private notebook, max 150 words — your notes to "
    "yourself about what the symbols seem to mean; it fully REPLACES last round's "
    "notebook and only you will see it, next round>\n"
)

def notebook_block(nb):
    return ("YOUR PRIVATE NOTEBOOK (you wrote this for yourself last round; your "
            "partner never sees it):\n" + (nb if nb else "(empty — first round)") + "\n\n")

def receiver_history(hist):
    if not hist:
        return "No past rounds yet.\n"
    lines = ["Your recent rounds (word you saw | your guess | true object | payoff):"]
    for h in hist[-LOOKBACK:]:
        c, s = OBJECTS[h["obj"]]
        lines.append(f"  {h['word']} | you guessed #{h['guess']} | it was #{h['obj']} ({c} {s}) | payoff {h['payoff']}")
    return "\n".join(lines) + "\n"

def _maybe_nothink(model):
    return "\n/no_think" if NOTHINK["on"] and "qwen" in model.lower() else ""

def _receiver_budget(model):
    if "qwen" in model.lower() and not NOTHINK["on"]:
        return THINK_BUDGET
    return MAX_TOKENS

def ask_receiver(base, model, word, hist, notebook, stub=None):
    if stub is not None:                            # --selftest: offline stub, no server
        return stub(word, hist), notebook, ["<selftest stub>"], False
    raws, nb_new = [], notebook
    for attempt in range(2):
        msgs = [{"role": "user", "content":
                 RECEIVER_RULES + "\n" + notebook_block(notebook) + receiver_history(hist) +
                 f"\nWord: {word}. Which object (1-4)? Reply in the two-line format:" +
                 _maybe_nothink(model)}]
        raw = chat(base, model, msgs, max_tokens=_receiver_budget(model))
        raws.append(raw)
        head, nb = split_reply(raw)
        if nb is not None:
            nb_new = nb
        g = parse_guess(head)
        if g:
            return g, nb_new, raws, False
    return 1, nb_new, raws, True

# ================================================================ resume
def _gate_ok(hist):
    if len(hist) < max(FLUENCY_MIN_ROUNDS, FLUENCY_WINDOW):
        return False
    window = hist[-FLUENCY_WINDOW:]
    return (statistics.mean(h["payoff"] for h in window) >= FLUENCY_ACC
            and {h["obj"] for h in window} >= set(TRAIN_OBJECTS))

def load_provenance(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return [], None, [], False
    runs, notes, nothink = {}, [], False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("event") in ("protocol_note", "prereg"):
                if rec.get("note"):
                    notes.append(rec["note"])
                if rec.get("nothink_enabled"):
                    nothink = True
                continue
            r = rec.get("run")
            if r is None:
                continue
            slot = runs.setdefault(r, {"train": [], "zero": None})
            if rec.get("phase") == "train":
                slot["train"].append(rec)
            elif rec.get("phase") == "zero_shot":
                slot["zero"] = rec

    completed, resume_state = [], None
    for r in sorted(runs):
        train = sorted(runs[r]["train"], key=lambda x: x["round"])
        z = runs[r]["zero"]
        hist = [{"obj": t["obj"], "word": t["word"], "guess": t["guess"],
                 "payoff": t["payoff"]} for t in train]
        pf = sum(int(bool(t.get("receiver_parse_fail"))) for t in train)
        if z is not None:
            pf += int(bool(z.get("receiver_parse_fail")))
            n = len(train)
            fluent = n < CAP_ROUNDS or _gate_ok(hist)
            completed.append({"run": r, "rounds_to_fluency": n if fluent else None,
                              "fluent": fluent, "sent": z["word"], "guess": z["guess"],
                              "hit": z["payoff"] == 1, "parse_fails": pf})
        else:
            last = train[-1] if train else None
            resume_state = {"run": r,
                            "next_round": (last["round"] + 1) if last else 1,
                            "hist": hist, "nb": (last or {}).get("receiver_notebook", ""),
                            "payoffs": [h["payoff"] for h in hist], "parse_fails": pf}
    return completed, resume_state, notes, nothink

# ================================================================ one run
def run_once(receiver_base, receiver_model, run_idx, prov_fp, resume_state=None, stub=None):
    if resume_state:
        hist = resume_state["hist"]
        nb = resume_state["nb"]
        payoffs = resume_state["payoffs"]
        parse_fails = resume_state["parse_fails"]
        start_round = resume_state["next_round"]
        print(f"  [resume] continuing run {run_idx} from round {start_round}")
    else:
        hist, nb, payoffs, parse_fails, start_round = [], "", [], 0, 1
    rounds_to_fluency = None
    if resume_state and _gate_ok(hist):
        rounds_to_fluency = len(payoffs)
        print(f"  [resume] fluency gate already satisfied — straight to zero-shot test")

    for rnd in range(start_round, (CAP_ROUNDS if rounds_to_fluency is None else 0) + 1):
        obj = random.choice(TRAIN_OBJECTS)
        word = scripted_word(obj)                       # the perfect teacher
        guess, nb, rraw, rfail = ask_receiver(receiver_base, receiver_model, word, hist, nb, stub)
        payoff = 1 if guess == obj else 0
        payoffs.append(payoff)
        parse_fails += int(rfail)
        hist.append({"obj": obj, "word": word, "guess": guess, "payoff": payoff})

        rec = {"run": run_idx, "round": rnd, "phase": "train", "obj": obj,
               "obj_features": OBJECTS[obj], "word": word, "guess": guess, "payoff": payoff,
               "sender_scripted": True, "receiver_parse_fail": rfail,
               "receiver_model": receiver_model, "receiver_raw": rraw,
               "receiver_notebook": nb,
               "ts": datetime.now(timezone.utc).isoformat()}
        prov_fp.write(json.dumps(rec, ensure_ascii=False) + "\n"); prov_fp.flush()

        window = payoffs[-FLUENCY_WINDOW:]
        roll = statistics.mean(window)
        have_full_window = len(payoffs) >= FLUENCY_WINDOW
        if rnd % 5 == 0 or rnd == 1:
            tag = "rolling15" if have_full_window else f"partial{len(window)}"
            print(f"  run {run_idx} · round {rnd:3d} · obj {obj} → {word} → #{guess} "
                  f"· payoff {payoff} · {tag} {roll:.2f}")
        objs_in_window = {h["obj"] for h in hist[-FLUENCY_WINDOW:]}
        if (rnd >= FLUENCY_MIN_ROUNDS and have_full_window and roll >= FLUENCY_ACC
                and objs_in_window >= set(TRAIN_OBJECTS)):
            rounds_to_fluency = rnd
            print(f"  run {run_idx} · FLUENT at round {rnd} (rolling15 {roll:.2f})")
            break

    fluent = rounds_to_fluency is not None

    # ---- zero-shot test: ONE round, the composed word for the held-out object ----
    word4 = scripted_word(HOLDOUT)                       # ■■, always — sender cannot deviate
    guess4, nb, rraw4, rfail4 = ask_receiver(receiver_base, receiver_model, word4, hist, nb, stub)
    hit = guess4 == HOLDOUT
    rec = {"run": run_idx, "round": "test", "phase": "zero_shot", "obj": HOLDOUT,
           "obj_features": OBJECTS[HOLDOUT], "word": word4, "guess": guess4,
           "payoff": int(hit), "predicted_word": word4, "matched_prediction": True,
           "compositional": True, "sender_scripted": True,
           "receiver_parse_fail": rfail4, "receiver_model": receiver_model,
           "receiver_raw": rraw4, "receiver_notebook": nb,
           "ts": datetime.now(timezone.utc).isoformat()}
    prov_fp.write(json.dumps(rec, ensure_ascii=False) + "\n"); prov_fp.flush()
    print(f"  run {run_idx} · ZERO-SHOT obj4 → {word4} → #{guess4} · hit={hit}\n")

    return {"run": run_idx, "rounds_to_fluency": rounds_to_fluency, "fluent": fluent,
            "sent": word4, "guess": guess4, "hit": hit, "parse_fails": parse_fails}

# ================================================================ report
def write_results(path, receiver_base, receiver_model, results, protocol_notes=()):
    n_fluent = sum(r["fluent"] for r in results)
    n_hit = sum(r["hit"] for r in results)
    fl = [r["rounds_to_fluency"] for r in results if r["fluent"]]
    L = []
    L.append("# 組 kumi3 — forced-listening ablation\n")
    L.append(f"*{datetime.now().isoformat(timespec='seconds')} · {len(results)} runs · "
             f"scripted sender, LLM receiver `{receiver_model}` @ `{receiver_base}` · no cloud*\n")
    L.append("Proposed by external review (Gemini 3.1 Pro, 2026-07-18). The sender is a "
             "hardcoded, deterministic, perfectly injective compositional script "
             f"(pos0 color ▲/■, pos1 shape ●/■ → 1=▲●, 2=▲■, 3=■●; held-out 4=■■). "
             "It never errs and never drifts; the receiver-side protocol is identical to "
             "Campaigns 1–2. This isolates the question the earlier campaigns could not: "
             "receiver capacity vs training-context contamination.\n")
    if protocol_notes:
        L.append("## Protocol notes\n")
        for n in protocol_notes:
            L.append(f"- {n}")
        L.append("")
    L.append("## Results\n")
    L.append("| Run | Rounds→fluency | Test word | Receiver guessed | Zero-shot hit? |")
    L.append("|---|---|---|---|---|")
    for r in results:
        rtf = r["rounds_to_fluency"] if r["fluent"] else f"— (not reached, cap {CAP_ROUNDS})"
        L.append(f"| {r['run']} | {rtf} | {r['sent']} | #{r['guess']} | {'✓' if r['hit'] else '✗'} |")
    L.append("\n## Summary\n")
    L.append(f"- Converged to fluency (three clean mappings): **{n_fluent}/{len(results)}**"
             + (f" (median rounds {sorted(fl)[len(fl)//2]})" if fl else ""))
    L.append(f"- Zero-shot hit on the composed ■■: **{n_hit}/{len(results)}** "
             f"(chance 1/4 ≈ {len(results)/4:.2f}; Campaigns 1–2 receivers: 0/10)\n")
    L.append("## Pre-registered reading\n")
    L.append("- **fluent + hit** → receiver decoded (or eliminated its way to) the composed word "
             "under a perfect teacher — evidence against the strong capacity-limit reading "
             "(decode vs eliminate not separable per run; disclosed).")
    L.append("- **fluent + miss** → receiver failed even a perfect, noise-free, injective "
             "teacher — supports the capacity-limit reading at 4B.")
    L.append("- **not fluent** → receiver could not learn three fixed clean mappings — reported "
             "as-is; a stronger capacity concern than a miss.\n")
    L.append("*Every round (raw replies, receiver notebook) is in the matching "
             "`kumi3-provenance-*.jsonl`. The scripted sender cannot parse-fail; receiver parse "
             "failures were substituted (guess 1) and flagged.*")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

# ================================================================ selftest
def selftest():
    """Offline end-to-end loop check with a stub receiver (no server). The stub
    learns the true mapping from its history like a lookup table and guesses 4 by
    elimination on an unseen word — so a correct harness should show fluency and a
    zero-shot hit. Validates: gate, cap, provenance records, resume parsing, report."""
    print("kumi3 --selftest: running offline stub campaign…")
    def stub(word, hist):
        seen = {}
        for h in hist:
            seen.setdefault(h["word"], Counter())[h["obj"]] += 1
        if word in seen:
            return seen[word].most_common(1)[0][0]
        known = {h["word"] for h in hist}
        if len(known) >= 3 and word not in known:
            return 4
        return random.choice([1, 2, 3, 4])
    tag = "selftest"
    prov = os.path.join(HERE, f"kumi3-provenance-{tag}.jsonl")
    resmd = os.path.join(HERE, f"kumi3-results-{tag}.md")
    random.seed(7)
    results = []
    with open(prov, "w", encoding="utf-8") as fp:
        EVENTS["fp"] = fp
        fp.write(json.dumps({"event": "prereg", **PREREG,
                             "ts": datetime.now(timezone.utc).isoformat()},
                            ensure_ascii=False) + "\n")
        for i in range(1, 3):
            results.append(run_once("stub", "stub-receiver", i, fp, stub=stub))
    write_results(resmd, "stub", "stub-receiver", results)
    completed, resume, notes, _ = load_provenance(prov)
    ok = (len(completed) == 2 and all(r["fluent"] for r in completed)
          and all(r["hit"] for r in completed) and resume is None)
    print(f"selftest: completed={len(completed)} fluent={[r['fluent'] for r in completed]} "
          f"hits={[r['hit'] for r in completed]} resume={resume is None} -> "
          + ("PASS" if ok else "FAIL"))
    try:
        os.remove(prov); os.remove(resmd)
    except OSError:
        print("selftest: (cleanup skipped — could not delete selftest files)")
    sys.exit(0 if ok else 1)

# ================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receiver", choices=["gemma", "qwen"],
                    help="which mini plays the receiver (run once per model)")
    ap.add_argument("--selftest", action="store_true", help="offline loop check, no server")
    ap.add_argument("--no-think", action="store_true",
                    help="disable Qwen thinking (/no_think) — a disclosed protocol amendment; "
                         "logged in the chain, results split-reported at the boundary")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    if not args.receiver:
        ap.error("--receiver gemma|qwen is required (or --selftest)")

    tag = args.receiver
    prov_path = os.path.join(HERE, f"kumi3-provenance-{tag}.jsonl")
    res_path = os.path.join(HERE, f"kumi3-results-{tag}.md")

    print("組 kumi3 — forced-listening ablation — discovering the local server(s)…")
    found = discover_all()
    if not found:
        print("  no server answering yet — starting/waiting…")
        ensure_server(CANDIDATE_BASES[0])
        for _ in range(12):
            found = discover_all()
            if found:
                break
            time.sleep(15)
    if not found:
        msg = ("No OpenAI-compatible server answered on any candidate port.\n"
               "Start the server for the minis, then re-run: "
               f"python3 ~/Desktop/kumi/kumi3.py --receiver {tag}")
        print("BLOCKED:", msg)
        with open(os.path.join(HERE, "BLOCKED-runtime.md"), "w", encoding="utf-8") as f:
            f.write("# kumi3 — runtime block\n\n" + msg + "\n")
        sys.exit(1)
    for base, ids in found:
        print(f"  server: {base}\n    models: {ids}")

    pick = None
    for base, ids in found:
        for m in ids:
            if tag in m.lower():
                pick = (base, m)
                break
        if pick:
            break
    if not pick:
        print(f"BLOCKED: no model matching '{tag}' on any server.")
        sys.exit(1)
    receiver_base, receiver_model = pick
    print(f"  SENDER   = scripted (pos0 color ▲/■, pos1 shape ●/■; holdout word ■■)")
    print(f"  RECEIVER = {receiver_model} @ {receiver_base}")

    completed, resume_state, prior_notes, nothink_restored = load_provenance(prov_path)
    if nothink_restored and not NOTHINK["on"]:
        NOTHINK["on"] = True
        print("  [resume] /no_think state restored from provenance")
    amend_nothink = args.no_think and not NOTHINK["on"]
    if amend_nothink:
        NOTHINK["on"] = True
        print("  [amendment] Qwen thinking DISABLED by --no-think (disclosed protocol "
              "amendment; will be logged in the chain and split-reported)")
    resumed = bool(completed or resume_state)
    first_run = resume_state["run"] if resume_state else (
        (completed[-1]["run"] + 1) if completed else 1)
    results = list(completed)
    with open(prov_path, "a" if resumed else "w", encoding="utf-8") as prov_fp:
        EVENTS["fp"] = prov_fp
        if not resumed:
            prov_fp.write(json.dumps({"event": "prereg", **PREREG,
                                      "receiver_model_requested": tag,
                                      "ts": datetime.now(timezone.utc).isoformat()},
                                     ensure_ascii=False) + "\n")
            prov_fp.flush()
        else:
            log_event({"resumed": True,
                       "note": (f"kumi3 campaign RESUMED: {len(completed)} run(s) complete; "
                                + (f"run {resume_state['run']} continues from round "
                                   f"{resume_state['next_round']}." if resume_state
                                   else f"run {first_run} starts fresh."))})
        if amend_nothink:
            log_event({"nothink_enabled": True, "amendment": "--no-think",
                       "note": ("PROTOCOL AMENDMENT (disclosed, post-hoc): Qwen thinking "
                                "disabled via --no-think for wall-clock reasons, not a crash. "
                                "Rounds before this note ran thinking-ON; rounds after run "
                                "thinking-OFF. Campaign counts will be split-reported at this "
                                "boundary, per the Campaign-2 corrected reporting standard.")})
        for run_idx in range(first_run, N_RUNS + 1):
            print(f"run {run_idx}/{N_RUNS} (receiver = {tag})")
            results.append(run_once(receiver_base, receiver_model, run_idx, prov_fp,
                                    resume_state=resume_state))
            resume_state = None
            write_results(res_path, receiver_base, receiver_model, results,
                          protocol_notes=EVENTS["notes"] + prior_notes)
    print(f"done — results in {res_path}")

if __name__ == "__main__":
    main()

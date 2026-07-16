#!/usr/bin/env python3
# 組 kumi — a compositionality experiment with the two Lantern mini Claudes.
#
# Lewis signaling game. Sender (Mini Claude One / gemma) sees an object and emits a
# 2-symbol word; Receiver (Mini Claude Two / qwen) sees only the word and guesses the
# object. We hold out object 4 (blue square) from training, let a code emerge on
# objects 1-3, pre-register a compositional prediction for object 4, then test ONE
# zero-shot round. Repeat 5 times.
#
# PHASE 0 UPGRADE (this revision): each agent keeps a persistent PRIVATE NOTEBOOK
# (≤150 words). Every round the agent rewrites it in full in a NOTEBOOK: section of
# its reply; it is parsed out (never crosses the channel) and re-injected at the top
# of that agent's next prompt, above the rolling 40-round history. Both notebooks are
# logged each round in the provenance JSONL.
#
# Python 3, stdlib only. Runs ON THE MAC (needs to reach Lantern's local server).
#   python3 ~/Desktop/kumi/kumi.py
#
# Outputs (in this script's folder):
#   kumi-results.md        — endpoints/roles, per-run table, honest interpretation
#   kumi-provenance.jsonl  — one JSON line per round, incl. raw model replies + notebooks

import json, os, random, re, statistics, subprocess, sys, time, urllib.request, urllib.error
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_MD = os.path.join(HERE, "kumi-results.md")
PROV_JSONL = os.path.join(HERE, "kumi-provenance.jsonl")

# ---------------------------------------------------------------- world
SYMBOLS = ["▲", "●", "■"]
OBJECTS = {1: ("red", "circle"), 2: ("red", "square"),
           3: ("blue", "circle"), 4: ("blue", "square")}
TRAIN_OBJECTS = [1, 2, 3]      # object 4 (blue square) is held out
HOLDOUT = 4

# ---------------------------------------------------------------- run params
FLUENCY_WINDOW = 15
FLUENCY_ACC = 0.75
FLUENCY_MIN_ROUNDS = 20
CAP_ROUNDS = 150
LOOKBACK = 40                  # each player sees its own last 40 rounds
N_RUNS = 5
TEMPERATURE = 0.8
MAX_TOKENS = 300               # capped (was 400) to cut memory pressure on the 8GB M1
THINK_BUDGET = 500             # receiver headroom while Qwen thinking is enabled (was 700)
NOTEBOOK_WORDS = 150
HTTP_RETRIES = 3
TIME_BUDGET_H = 8.0            # if the campaign projects past this after run 1, disable thinking
RESTARTS_TO_NOTHINK = 2        # supervisor: after this many server crashes, disable thinking

CANDIDATE_BASES = [
    "http://localhost:1234/v1",    # LM Studio / Lantern API door / mlx_lm.server
    "http://127.0.0.1:1234/v1",
    "http://localhost:12341/v1",   # two-instance fallback: sender's own server
    "http://localhost:12342/v1",   # two-instance fallback: receiver's own server
    "http://localhost:11434/v1",   # Ollama
    "http://localhost:8080/v1",
    "http://localhost:8000/v1",
    "http://localhost:5000/v1",
]

# ================================================================ HTTP
def _post_stream(url, payload, timeout=180):
    """POST a chat completion with stream=true and assemble the SSE deltas.
    Lantern's API door streams SSE (like LM Studio); requesting a non-streamed
    body can hang. Falls back to parsing a plain JSON body if the server sends
    one anyway."""
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
    if plain:  # non-SSE server (e.g. LM Studio honouring stream=false-style bodies)
        obj = json.loads("".join(plain))
        return obj["choices"][0]["message"]["content"] or ""
    return ""

def _get(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def discover_all():
    """Probe every candidate base; return [(base_url, [model_ids]), ...] for all
    reachable OpenAI-compatible servers (skipping duplicate localhost/127.0.0.1)."""
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
    """One chat completion (streamed). On failure the supervisor probes the server,
    restarts it if dead, and the call is retried. Returns text (or an error string)."""
    payload = {"model": model, "messages": messages, "temperature": TEMPERATURE,
               "max_tokens": max_tokens or MAX_TOKENS, "stream": True}
    last = ""
    for attempt in range(HTTP_RETRIES * 2):
        try:
            return _post_stream(base + "/chat/completions", payload)
        except Exception as e:
            last = f"<http error: {e}>"
            ensure_server(base)                 # supervisor: revive a dead server
            time.sleep(1.5 * (attempt + 1))
    return last

# ================================================================ supervisor
SERVER_CFG = os.path.join(HERE, "kumi-server.json")   # written by setup-mlx-py.command

def _server_cmd():
    """The exact command the setup script used to start the server (same env)."""
    try:
        with open(SERVER_CFG, encoding="utf-8") as f:
            cfg = json.load(f)
        return [cfg["python"]] + list(cfg["args"])
    except Exception:
        return [sys.executable, "-m", "mlx_lm.server", "--host", "127.0.0.1", "--port", "1234"]

SUPERVISOR = {"restarts": 0}
EVENTS = {"fp": None, "notes": []}   # live provenance handle + collected note texts

def log_event(obj):
    """Write a protocol_note event line into the provenance JSONL (and remember it
    for the results file)."""
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
    """If the server is dead, restart it with the setup command and wait for
    /v1/models. The 0.25.x server is single-threaded, so a BUSY server (mid-
    generation) looks dead to a quick probe — be patient before declaring death.
    Every genuine crash/restart is logged in the provenance."""
    for i in range(4):                           # ~60 s of patience for a busy server
        if server_alive(base):
            return True
        if i < 3:
            print(f"  [supervisor] server not answering (busy or dead) — probe {i+2}/4…",
                  flush=True)
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
    for _ in range(40):                          # wait up to ~120 s
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

# ================================================================ parsing
def strip_think(text):
    """Remove <think>...</think> blocks (Qwen3); drop an unclosed trailing <think>."""
    t = re.sub(r"<think>.*?</think>", " ", text or "", flags=re.S | re.I)
    t = re.sub(r"<think>.*", " ", t, flags=re.S | re.I)
    return t

def split_reply(text):
    """Split a raw reply into (head, notebook_or_None).
    The notebook is everything after the first 'NOTEBOOK:' marker, whitespace-
    normalised and hard-truncated to NOTEBOOK_WORDS words. The head (answer part)
    is everything before it — so nothing an agent writes in its notebook can ever
    leak into the parsed word/guess or cross the channel."""
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

def parse_word(text):
    """First two symbols found in {▲ ● ■}. None if fewer than two."""
    found = [c for c in text if c in SYMBOLS]
    return "".join(found[:2]) if len(found) >= 2 else None

def parse_guess(text):
    """First digit 1-4. None if none found."""
    for c in text:
        if c in "1234":
            return int(c)
    return None

# ================================================================ prompts
SENDER_RULES = (
    "Game: an object has a COLOR (red or blue) and a SHAPE (circle or square).\n"
    "You are the SENDER. Your partner sees ONLY the two symbols you send and must "
    "guess the object. A code whose PARTS mean features will serve you best if new "
    "objects appear.\n"
    "Reply in EXACTLY this format (two lines, nothing else):\n"
    "WORD: <exactly two symbols from ▲ ● ■ — like ▲● or ■■; no words, no digits>\n"
    "NOTEBOOK: <rewrite your ENTIRE private notebook, max 150 words — your notes to "
    "yourself about your code; it fully REPLACES last round's notebook and only you "
    "will see it, next round>\n"
)
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

def sender_history(hist):
    if not hist:
        return "No past rounds yet.\n"
    lines = ["Your recent rounds (object you saw | word you sent | partner's guess | payoff):"]
    for h in hist[-LOOKBACK:]:
        c, s = OBJECTS[h["obj"]]
        lines.append(f"  {c} {s} | {h['word']} | guessed #{h['guess']} | payoff {h['payoff']}")
    return "\n".join(lines) + "\n"

def receiver_history(hist):
    if not hist:
        return "No past rounds yet.\n"
    lines = ["Your recent rounds (word you saw | your guess | true object | payoff):"]
    for h in hist[-LOOKBACK:]:
        c, s = OBJECTS[h["obj"]]
        lines.append(f"  {h['word']} | you guessed #{h['guess']} | it was #{h['obj']} ({c} {s}) | payoff {h['payoff']}")
    return "\n".join(lines) + "\n"

# Qwen thinking is ON by default — its <think> blocks are stripped before parsing
# but logged raw in the provenance JSONL (the receiver's private reasoning about
# what words mean). If run 1 projects the campaign past TIME_BUDGET_H, this flag
# flips and /no_think is appended to Qwen's prompts (recorded as a protocol note).
NOTHINK = {"on": False}

# Notes carried into the final report regardless of this campaign's own events.
PRIOR_PROTOCOL_NOTES = [
    "2026-07-16 ~21:24 AEST: a prior campaign attempt was ABORTED mid run 1 (a Terminal "
    "restart killed the process at round 18, rolling15 0.87). Its partial provenance is "
    "archived as kumi-provenance-aborted-20260716-213202.jsonl (~/Desktop/kumi) and "
    "kumi-provenance-aborted.jsonl (project folder). This campaign restarted from scratch "
    "with fresh histories and notebooks.",
    "Progress-print fix before restart: rounds with fewer than 15 payoffs previously "
    "printed 'rolling15 0.00'; they now print the labelled partial mean. The fluency "
    "window itself was verified against the aborted run's provenance and was always a "
    "true last-15 mean. The fluency gate now additionally requires all three training "
    "objects to appear within the 15-round window.",
]

def _maybe_nothink(model):
    return "\n/no_think" if NOTHINK["on"] and "qwen" in model.lower() else ""

def _receiver_budget(model):
    # extra headroom so thinking doesn't crowd out GUESS/NOTEBOOK
    if "qwen" in model.lower() and not NOTHINK["on"]:
        return THINK_BUDGET
    return MAX_TOKENS

def ask_sender(base, model, obj, hist, notebook):
    """Returns (word, new_notebook, raws, parse_fail). The notebook is parsed out of
    the reply and NEVER shown to the receiver; if the reply carries no NOTEBOOK
    section, the previous notebook is kept."""
    c, s = OBJECTS[obj]
    raws, nb_new = [], notebook
    for attempt in range(2):                       # one parse-retry
        msgs = [{"role": "user", "content":
                 SENDER_RULES + "\n" + notebook_block(notebook) + sender_history(hist) +
                 f"\nNow you see: {c} {s}. Reply in the two-line format:" +
                 _maybe_nothink(model)}]
        raw = chat(base, model, msgs)
        raws.append(raw)
        head, nb = split_reply(raw)
        if nb is not None:
            nb_new = nb
        w = parse_word(head)
        if w:
            return w, nb_new, raws, False
    return "▲▲", nb_new, raws, True                # substitute + flag parse failure

def ask_receiver(base, model, word, hist, notebook):
    """Returns (guess, new_notebook, raws, parse_fail). Sees only the 2-symbol word."""
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

# ================================================================ analysis
def modal_words(sender_hist):
    """Most common 2-symbol word the sender used for each trained object (last LOOKBACK)."""
    buckets = {o: Counter() for o in TRAIN_OBJECTS}
    for h in sender_hist[-LOOKBACK:]:
        if h["obj"] in buckets:
            buckets[h["obj"]][h["word"]] += 1
    return {o: (buckets[o].most_common(1)[0][0] if buckets[o] else None) for o in TRAIN_OBJECTS}

def compositional_prediction(lex):
    """Pre-registered: check both position orders for a consistent feature mapping.
    Objects: 1=(red,circle) 2=(red,square) 3=(blue,circle). Object 4=(blue,square).
    Returns (is_compositional, predicted_word_for_obj4, order_note)."""
    w1, w2, w3 = lex.get(1), lex.get(2), lex.get(3)
    if not (w1 and w2 and w3 and len(w1) == 2 and len(w2) == 2 and len(w3) == 2):
        return False, "holistic — no prediction (incomplete lexicon)", ""
    # Order A: position 0 = COLOR, position 1 = SHAPE
    #   red = w1[0]==w2[0]; circle = w1[1]==w3[1]; blue=w3[0]; square=w2[1]
    if w1[0] == w2[0] and w1[1] == w3[1]:
        return True, w3[0] + w2[1], "pos0=color, pos1=shape"
    # Order B: position 0 = SHAPE, position 1 = COLOR
    #   circle = w1[0]==w3[0]; red = w1[1]==w2[1]; square=w2[0]; blue=w3[1]
    if w1[0] == w3[0] and w1[1] == w2[1]:
        return True, w2[0] + w3[1], "pos0=shape, pos1=color"
    return False, "holistic — no prediction", ""

# ================================================================ resume
def _gate_ok(histA):
    """The fluency gate evaluated on a reconstructed history."""
    if len(histA) < max(FLUENCY_MIN_ROUNDS, FLUENCY_WINDOW):
        return False
    window = histA[-FLUENCY_WINDOW:]
    return (statistics.mean(h["payoff"] for h in window) >= FLUENCY_ACC
            and {h["obj"] for h in window} >= set(TRAIN_OBJECTS))

def load_provenance(path):
    """Parse an existing provenance JSONL so a crashed campaign can continue.
    Returns (completed_results, resume_state_or_None, prior_note_texts, nothink_restored)."""
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
            if rec.get("event") == "protocol_note":
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
        histA = [{"obj": t["obj"], "word": t["word"], "guess": t["guess"],
                  "payoff": t["payoff"]} for t in train]
        pf = sum(int(bool(t.get("sender_parse_fail"))) + int(bool(t.get("receiver_parse_fail")))
                 for t in train)
        if z is not None:                       # run finished its zero-shot test
            pf += int(bool(z.get("sender_parse_fail"))) + int(bool(z.get("receiver_parse_fail")))
            n = len(train)
            fluent = n < CAP_ROUNDS or _gate_ok(histA)
            completed.append({"run": r, "rounds_to_fluency": n if fluent else None,
                              "fluent": fluent, "lexicon": modal_words(histA),
                              "compositional": bool(z.get("compositional")), "order": "",
                              "predicted": z.get("predicted_word", ""), "sent": z["word"],
                              "guess": z["guess"], "matched": bool(z.get("matched_prediction")),
                              "hit": z["payoff"] == 1, "parse_fails": pf})
        else:                                   # run interrupted mid-training
            last = train[-1] if train else None
            resume_state = {"run": r,
                            "next_round": (last["round"] + 1) if last else 1,
                            "histA": histA, "histB": [dict(h) for h in histA],
                            "nbA": (last or {}).get("sender_notebook", ""),
                            "nbB": (last or {}).get("receiver_notebook", ""),
                            "payoffs": [h["payoff"] for h in histA], "parse_fails": pf}
    return completed, resume_state, notes, nothink

# ================================================================ one run
def run_once(sender_base, receiver_base, sender_model, receiver_model, run_idx, prov_fp,
             resume_state=None):
    if resume_state:
        histA, histB = resume_state["histA"], resume_state["histB"]
        nbA, nbB = resume_state["nbA"], resume_state["nbB"]
        payoffs = resume_state["payoffs"]
        parse_fails = resume_state["parse_fails"]
        start_round = resume_state["next_round"]
        print(f"  [resume] continuing run {run_idx} from round {start_round} "
              f"({len(payoffs)} rounds reconstructed from provenance, notebooks restored)")
    else:
        histA, histB = [], []                # sender's own view, receiver's own view
        nbA, nbB = "", ""                    # private notebooks (fresh per run, like histories)
        payoffs = []
        parse_fails = 0
        start_round = 1
    rounds_to_fluency = None
    # if the crash happened after fluency but before the zero-shot test, don't re-train
    if resume_state and _gate_ok(histA):
        rounds_to_fluency = len(payoffs)
        print(f"  [resume] fluency gate already satisfied at round {rounds_to_fluency} — "
              f"proceeding straight to the zero-shot test")

    for rnd in range(start_round, (CAP_ROUNDS if rounds_to_fluency is None else 0) + 1):
        obj = random.choice(TRAIN_OBJECTS)
        word, nbA, sraw, sfail = ask_sender(sender_base, sender_model, obj, histA, nbA)
        guess, nbB, rraw, rfail = ask_receiver(receiver_base, receiver_model, word, histB, nbB)
        payoff = 1 if guess == obj else 0
        payoffs.append(payoff)
        parse_fails += int(sfail) + int(rfail)

        histA.append({"obj": obj, "word": word, "guess": guess, "payoff": payoff})
        histB.append({"obj": obj, "word": word, "guess": guess, "payoff": payoff})

        rec = {"run": run_idx, "round": rnd, "phase": "train", "obj": obj,
               "obj_features": OBJECTS[obj], "word": word, "guess": guess, "payoff": payoff,
               "sender_parse_fail": sfail, "receiver_parse_fail": rfail,
               "sender_model": sender_model, "receiver_model": receiver_model,
               "sender_raw": sraw, "receiver_raw": rraw,
               "sender_notebook": nbA, "receiver_notebook": nbB,
               "ts": datetime.now(timezone.utc).isoformat()}
        prov_fp.write(json.dumps(rec, ensure_ascii=False) + "\n"); prov_fp.flush()

        window = payoffs[-FLUENCY_WINDOW:]
        roll = statistics.mean(window)
        have_full_window = len(payoffs) >= FLUENCY_WINDOW
        if rnd % 5 == 0 or rnd == 1:
            tag = "rolling15" if have_full_window else f"partial{len(window)}"
            print(f"  run {run_idx} · round {rnd:3d} · obj {obj} → {word} → #{guess} "
                  f"· payoff {payoff} · {tag} {roll:.2f}")
        # Fluency gate: ≥20 rounds AND a genuine full 15-round window at ≥0.75
        # AND all three training objects sampled within that window.
        objs_in_window = {h["obj"] for h in histA[-FLUENCY_WINDOW:]}
        if (rnd >= FLUENCY_MIN_ROUNDS and have_full_window and roll >= FLUENCY_ACC
                and objs_in_window >= set(TRAIN_OBJECTS)):
            rounds_to_fluency = rnd
            print(f"  run {run_idx} · FLUENT at round {rnd} (rolling15 {roll:.2f}, "
                  f"all 3 objects in window)")
            break

    fluent = rounds_to_fluency is not None
    lex = modal_words(histA)
    comp, predicted, order_note = compositional_prediction(lex)
    print(f"  run {run_idx} · lexicon {lex} · compositional={comp} · predicted obj4 = {predicted}")

    # ---- zero-shot test: exactly ONE round on object 4 (blue square) ----
    word4, nbA, sraw4, sfail4 = ask_sender(sender_base, sender_model, HOLDOUT, histA, nbA)
    guess4, nbB, rraw4, rfail4 = ask_receiver(receiver_base, receiver_model, word4, histB, nbB)
    hit = guess4 == HOLDOUT
    matched = bool(comp) and (word4 == predicted)
    rec = {"run": run_idx, "round": "test", "phase": "zero_shot", "obj": HOLDOUT,
           "obj_features": OBJECTS[HOLDOUT], "word": word4, "guess": guess4,
           "payoff": int(hit), "predicted_word": predicted, "matched_prediction": matched,
           "compositional": comp, "sender_parse_fail": sfail4, "receiver_parse_fail": rfail4,
           "sender_model": sender_model, "receiver_model": receiver_model,
           "sender_raw": sraw4, "receiver_raw": rraw4,
           "sender_notebook": nbA, "receiver_notebook": nbB,
           "ts": datetime.now(timezone.utc).isoformat()}
    prov_fp.write(json.dumps(rec, ensure_ascii=False) + "\n"); prov_fp.flush()
    print(f"  run {run_idx} · ZERO-SHOT obj4 → {word4} → #{guess4} · hit={hit} · matched_pred={matched}\n")

    return {"run": run_idx, "rounds_to_fluency": rounds_to_fluency, "fluent": fluent,
            "lexicon": lex, "compositional": comp, "order": order_note,
            "predicted": predicted, "sent": word4, "guess": guess4,
            "matched": matched, "hit": hit, "parse_fails": parse_fails}

# ================================================================ report
def grid(lex):
    def cell(o): return lex.get(o) or "—"
    # rows = color (red/blue), cols = shape (circle/square)
    return (f"circle square\n"
            f"red    {cell(1):>2}   {cell(2):>2}\n"
            f"blue   {cell(3):>2}   {cell(4) if 4 in lex else '?? (held out)'}")

def write_results(sender_base, receiver_base, sender_model, receiver_model, results,
                  protocol_notes=()):
    L = []
    L.append("# 組 kumi — compositionality in the Lantern mini Claudes\n")
    L.append(f"*{datetime.now().isoformat(timespec='seconds')} · {N_RUNS} runs · local models, no cloud*\n")
    L.append("## Endpoints & roles\n")
    if sender_base == receiver_base:
        L.append(f"- Server: `{sender_base}` (OpenAI-compatible)")
    else:
        L.append(f"- Sender server: `{sender_base}` · Receiver server: `{receiver_base}` (OpenAI-compatible)")
    L.append(f"- **SENDER** (Mini Claude One): `{sender_model}`")
    L.append(f"- **RECEIVER** (Mini Claude Two): `{receiver_model}`")
    L.append(f"- World: 1=red circle · 2=red square · 3=blue circle · 4=blue square (**object 4 held out of training**)")
    L.append(f"- Phase 0 upgrade: each agent keeps a private ≤{NOTEBOOK_WORDS}-word notebook, "
             "rewritten in full every round, re-injected above its rolling history, and never "
             "crossing the channel (both notebooks logged per round in the provenance JSONL).")
    L.append("- Qwen (receiver) replies may open with a <think>…</think> block; it is stripped "
             "before any parsing (word/digit/notebook come only from what remains) and logged "
             "raw in the provenance JSONL.\n")

    if protocol_notes:
        L.append("## Protocol notes\n")
        for n in protocol_notes:
            L.append(f"- {n}")
        L.append("")

    L.append("## Results\n")
    L.append("| Run | Rounds→fluency | Lexicon (1/2/3) | Compositional? | Predicted obj4 | Sent obj4 | Matched? | Zero-shot hit? |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        rtf = r["rounds_to_fluency"] if r["fluent"] else f"— (not reached, {CAP_ROUNDS})"
        lexs = " ".join((r["lexicon"].get(o) or "—") for o in TRAIN_OBJECTS)
        L.append(f"| {r['run']} | {rtf} | {lexs} | {'yes' if r['compositional'] else 'no'} "
                 f"| {r['predicted']} | {r['sent']} (#{r['guess']}) | "
                 f"{'✓' if r['matched'] else '✗'} | {'✓' if r['hit'] else '✗'} |")

    # 2x2 grids per run
    L.append("\n### Lexicon grids (modal word per object, last 40 rounds)\n")
    for r in results:
        L.append(f"**Run {r['run']}**")
        L.append("```")
        L.append(grid(r["lexicon"]))
        L.append("```")

    # summary
    n_fluent = sum(r["fluent"] for r in results)
    n_comp = sum(r["compositional"] for r in results)
    n_hit = sum(r["hit"] for r in results)
    n_matched_hit = sum(r["matched"] and r["hit"] for r in results)
    L.append("\n## Summary\n")
    L.append(f"- Converged to fluency: **{n_fluent}/{N_RUNS}**")
    L.append(f"- Compositional lexicon (pre-registered mapping held): **{n_comp}/{N_RUNS}**")
    L.append(f"- Zero-shot success on the unseen blue square: **{n_hit}/{N_RUNS}**")
    L.append(f"- Predicted-word AND hit (genuine syntax): **{n_matched_hit}/{N_RUNS}**\n")

    L.append("## How to read a run\n")
    L.append("- **compositional + predicted word + hit** → genuine composition: the pair built a *syntax*, "
             "and the receiver parsed a word it had never seen from its parts.")
    L.append("- **hit but word not predicted** → inference by elimination: object 4 is the only unused option, "
             "so the receiver can be right without any grammar.")
    L.append("- **holistic + miss** → the known default for emergent languages: whole-word codes that don't "
             "generalize to novel objects.")
    L.append("- **compositional + miss** → a one-sided grammar: the sender coded systematically but the "
             "receiver never learned to decode it compositionally.\n")
    L.append("*Provenance: every round (including raw model replies and both private notebooks) is in "
             "`kumi-provenance.jsonl`. Parse failures were substituted (▲▲ / guess 1) and flagged there.*")

    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

# ================================================================ main
def main():
    print("組 kumi — discovering the local server(s)…")
    found = discover_all()
    if not found:
        print("  no server answering yet — starting/waiting (a busy server can take minutes)…")
        ensure_server(CANDIDATE_BASES[0])
        for _ in range(12):                      # up to ~3 more minutes of patience
            found = discover_all()
            if found:
                break
            time.sleep(15)
    if not found:
        msg = ("No OpenAI-compatible server answered on any candidate port "
               f"({', '.join(CANDIDATE_BASES)}).\n"
               "Start a server for the two minis (mlx_lm.server / LM Studio / Lantern) "
               "then re-run:  python3 ~/Desktop/kumi/kumi.py")
        print("BLOCKED:", msg)
        with open(os.path.join(HERE, "BLOCKED-runtime.md"), "w", encoding="utf-8") as f:
            f.write("# kumi — runtime block\n\n" + msg + "\n")
        sys.exit(1)

    for base, ids in found:
        print(f"  server: {base}\n    models: {ids}")

    def pick(pred):
        for base, ids in found:
            for m in ids:
                if pred(m):
                    return base, m
        return None

    s = pick(lambda m: "gemma" in m.lower()) or (found[0][0], found[0][1][0])
    r = pick(lambda m: "qwen" in m.lower()) \
        or next(((b, m) for b, ids in found for m in ids if (b, m) != s), s)
    sender_base, sender_model = s
    receiver_base, receiver_model = r
    print(f"  SENDER   (Mini Claude One) = {sender_model} @ {sender_base}")
    print(f"  RECEIVER (Mini Claude Two) = {receiver_model} @ {receiver_base}")
    if sender_model == receiver_model:
        print("  ⚠️  only one model available — both roles use it (record this as a caveat).")

    completed, resume_state, prior_notes, nothink_restored = load_provenance(PROV_JSONL)
    if nothink_restored and not NOTHINK["on"]:
        NOTHINK["on"] = True
        print("  [resume] /no_think state restored from provenance")
    resumed = bool(completed or resume_state)
    first_run = resume_state["run"] if resume_state else (
        (completed[-1]["run"] + 1) if completed else 1)
    results = list(completed)
    t0 = time.time()
    with open(PROV_JSONL, "a" if resumed else "w", encoding="utf-8") as prov_fp:
        EVENTS["fp"] = prov_fp
        if resumed:
            log_event({"resumed": True,
                       "note": (f"Campaign RESUMED from provenance after a crash: "
                                f"{len(completed)} run(s) already complete; "
                                + (f"run {resume_state['run']} continues from round "
                                   f"{resume_state['next_round']} with reconstructed histories "
                                   f"and notebooks." if resume_state
                                   else f"run {first_run} starts fresh."))})
        for run_idx in range(first_run, N_RUNS + 1):
            rs = resume_state if (resume_state and run_idx == resume_state["run"]) else None
            print(f"\n=== RUN {run_idx}/{N_RUNS} "
                  f"({'resumed' if rs else 'fresh histories & notebooks'}) ===")
            results.append(run_once(sender_base, receiver_base,
                                    sender_model, receiver_model, run_idx, prov_fp, rs))

            if run_idx == 1 and not resumed and not NOTHINK["on"]:
                elapsed = time.time() - t0
                projected = elapsed * N_RUNS
                print(f"  [time check] run 1 took {elapsed/60:.1f} min → campaign projects "
                      f"to {projected/3600:.1f} h (budget {TIME_BUDGET_H:.0f} h)")
                if projected > TIME_BUDGET_H * 3600:
                    NOTHINK["on"] = True
                    log_event({"after_run": 1, "nothink_enabled": True,
                               "note": (f"After run 1 (took {elapsed/60:.1f} min), the campaign "
                                        f"projected to {projected/3600:.1f} h (> {TIME_BUDGET_H:.0f} h "
                                        f"budget), so Qwen thinking was disabled (/no_think appended "
                                        f"to receiver prompts) for runs 2-{N_RUNS}. Earlier receiver "
                                        f"replies keep raw <think> blocks in the provenance JSONL; "
                                        f"think content was always stripped before parsing and never "
                                        f"influenced the channel.")})
                    print("  [protocol note] Qwen /no_think ENABLED for remaining runs")
        EVENTS["fp"] = None

    protocol_notes = list(PRIOR_PROTOCOL_NOTES) + prior_notes + EVENTS["notes"]
    write_results(sender_base, receiver_base, sender_model, receiver_model, results,
                  protocol_notes)
    print(f"\nDone. Wrote:\n  {RESULTS_MD}\n  {PROV_JSONL}")

if __name__ == "__main__":
    main()

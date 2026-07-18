#!/usr/bin/env python3
# 組 kumi — CAMPAIGN 2 (ROLE SWAP) with the two Lantern mini Claudes.
#
# Identical protocol to Campaign 1 (kumi.py), with the roles swapped:
#   SENDER   = Qwen3-4B-4bit          (spoke as receiver in Campaign 1)
#   RECEIVER = gemma-3-4b-it-qat-4bit (spoke as sender in Campaign 1)
# Everything else is unchanged: same world, holdout (object 4, blue square),
# fluency gate, pre-registration of the compositional prediction, ONE-trial
# zero-shot test, private notebooks, 5 runs with fresh histories, resumable
# from provenance, supervised server.
#
# Think-stripping now lives on the SENDER side: Qwen speaks, so the two symbols
# are parsed from the reply OUTSIDE any <think> block; raw replies (including
# think content) are logged in the provenance JSONL. The /no_think and
# think-budget machinery follows Qwen to the sender role.
#
# CAMPAIGN-LEVEL INTERPRETATIONS ARE PRE-REGISTERED in kumi2-results.md
# (written before any round of this campaign could run) and reproduced
# verbatim in the final report by this script.
#
# Python 3, stdlib only. Runs ON THE MAC (needs to reach Lantern's local server).
#   python3 ~/Desktop/kumi/kumi2.py
#
# Outputs (in this script's folder):
#   kumi2-results.md        — endpoints/roles, per-run table, pre-registered interpretation
#   kumi2-provenance.jsonl  — one JSON line per round, incl. raw model replies + notebooks
#
# NEVER touches Campaign 1 files (kumi-results.md / kumi-provenance.jsonl).

import json, os, random, re, statistics, subprocess, sys, time, urllib.request, urllib.error
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_MD = os.path.join(HERE, "kumi2-results.md")
PROV_JSONL = os.path.join(HERE, "kumi2-provenance.jsonl")

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
CAP_ROUNDS = 120               # AMENDED mid-campaign from 150 (see AMENDMENT_NOTE below)
LOOKBACK = 40                  # each player sees its own last 40 rounds
N_RUNS = 5
TEMPERATURE = 0.8
MAX_TOKENS = 300               # capped to cut memory pressure on the 8GB M1
THINK_BUDGET = 900             # SENDER headroom while Qwen thinking is enabled
                               # (dry-check 2026-07-17: at 500 Qwen exhausted the
                               # budget mid-think before emitting WORD; raised
                               # pre-launch, before any campaign round ran)
NOTEBOOK_WORDS = 150
HTTP_RETRIES = 3
TIME_BUDGET_H = 8.0            # if the campaign projects past this after run 1, disable thinking
RESULTS_DEADLINE_H = 2.75      # wall-clock deadline PER INVOCATION (2026-07-18 relaunch:
                               # results wanted within 3h; 0.25h margin for the zero-shot
                               # + report). At the deadline the current run stops training
                               # (still takes its zero-shot), remaining runs are skipped,
                               # and the report is written with completed runs. Set to
                               # None to disable. Skipped runs remain resumable later.
DEADLINE = {"t": None}         # set in main() at launch
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

# ---------------------------------------------------------------- pre-registration
# Written into kumi2-results.md BEFORE any round of Campaign 2 could run, and
# reproduced verbatim in the final report. Do not edit after launch.
PREREG_INTERPRETATION = [
    "- **Gemma-as-receiver decodes a composed novel word** → Campaign 1's deficit was "
    "receiver-specific (Qwen's listening).",
    "- **0 hits again** → listening-side decomposition fails in both models; hearing "
    "parts is intrinsically harder at 4B.",
    "- **Qwen-as-sender never produces a compositional lexicon** → composition may be "
    "Gemma-specific.",
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
                                    f"disabled (/no_think) mid-campaign to cut memory pressure "
                                    f"(Qwen is the SENDER in this campaign).")})
            print(f"  [supervisor] server back up (restart #{n})", flush=True)
            return True
    print("  [supervisor] could not revive the server after 120 s", flush=True)
    return False

# ================================================================ parsing
def strip_think(text):
    """Remove <think>...</think> blocks (Qwen3); drop an unclosed trailing <think>.
    In Campaign 2 Qwen is the SENDER, so this now guards the word parse: the two
    symbols are taken only from text OUTSIDE any think block."""
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

# Qwen thinking is ON by default. In Campaign 2 Qwen is the SENDER, so its
# <think> blocks are stripped before the word parse but logged raw in the
# provenance JSONL (the sender's private reasoning about its code). If run 1
# projects the campaign past TIME_BUDGET_H, this flag flips and /no_think is
# appended to Qwen's (sender) prompts (recorded as a protocol note).
NOTHINK = {"on": True}         # AMENDED mid-campaign: forced ON before runs 3-5
                               # (see AMENDMENT_NOTE_2); was False, flipped only by
                               # the run-1 time check in the original protocol

# Notes carried into the final report regardless of this campaign's own events.
PRIOR_PROTOCOL_NOTES = [
    "CAMPAIGN 2 — ROLE SWAP. Sender and receiver are exchanged relative to Campaign 1 "
    "(kumi.py): Qwen3-4B-4bit now SPEAKS, gemma-3-4b-it-qat-4bit now LISTENS. World, "
    "holdout, gate, pre-registration, one-trial zero-shot, notebooks, and run count are "
    "identical. Campaign 1 files (kumi-results.md, kumi-provenance.jsonl) are never touched.",
    "Think-stripping moved to the SENDER side: Qwen speaks, so the two symbols are parsed "
    "outside any <think> block; raw replies are logged. The /no_think fallback and think "
    "token budget follow Qwen into the sender role.",
    "Campaign-level interpretations were PRE-REGISTERED in kumi2-results.md before any "
    "round of this campaign ran (see 'Pre-registered interpretation' section).",
    "Pre-launch calibration (2026-07-17, dry-check only — no campaign rounds run): at the "
    "Campaign 1 think budget (500 tokens) Qwen-as-sender exhausted its budget mid-<think> "
    "before emitting a WORD line on both attempts. Sender think budget raised to 900, and "
    "the single parse-retry now appends /no_think so a parseable reply is always reachable. "
    "Raw truncated replies remain logged; think content never crosses the channel.",
]

# Post-hoc stopping amendment — decided AFTER seeing run 2's training data.
AMENDMENT_NOTE = (
    "AMENDMENT (2026-07-17T19:40Z / 2026-07-18 AEST, mid-campaign, after run 2 reached "
    "round 110 near chance-level rolling accuracy): CAP_ROUNDS reduced from 150 to 120. "
    "This is a post-hoc change to the stopping rule, NOT pre-registered. It only moves "
    "the point at which a non-fluent run stops training; the fluency gate, one-trial "
    "zero-shot test, and all pre-registered interpretations are unchanged. Caveat: any "
    "run that would have reached the gate between rounds 121-150 is now recorded as "
    "non-fluent (run 2 touched rolling15 0.73 at round 85 — two rounds shy of the gate — "
    "before collapsing back to chance).")
PRIOR_PROTOCOL_NOTES.append(AMENDMENT_NOTE)

AMENDMENT_NOTE_2 = (
    "AMENDMENT 2 (2026-07-17T20:30Z / 2026-07-18 AEST, mid-campaign, decided after "
    "inspecting run 2 provenance at round 116): Qwen thinking DISABLED (/no_think, "
    "sender budget drops to MAX_TOKENS) for the remainder of the campaign. Post-hoc, "
    "NOT pre-registered, though /no_think was the pre-registered time-budget response "
    "and the 8h budget is already exceeded. Motivation: in 116 rounds Qwen-as-sender "
    "encoded shape only (obj1 and obj3 both ▲● 34x/32x; position 0 was ▲ for all "
    "objects), capping accuracy near 0.67 — below the 0.75 gate. Its notebooks assert "
    "a color code (▲=red, ■=blue) it never emits and blame the receiver, i.e. its "
    "per-round reasoning re-confirms the broken code rather than repairing it. "
    "Runs completed with thinking ON: 1-2; runs 3-5 (and any remaining run-2 rounds) "
    "run with thinking OFF, so cross-run comparisons within Campaign 2 are exploratory. "
    "Parse fails were 1/116, so the think-parse machinery is not the issue.")
PRIOR_PROTOCOL_NOTES.append(AMENDMENT_NOTE_2)

def _maybe_nothink(model):
    return "\n/no_think" if NOTHINK["on"] and "qwen" in model.lower() else ""

def _sender_budget(model):
    # extra headroom so Qwen's thinking doesn't crowd out WORD/NOTEBOOK
    if "qwen" in model.lower() and not NOTHINK["on"]:
        return THINK_BUDGET
    return MAX_TOKENS

def _receiver_budget(model):
    # gemma does not emit think blocks; qwen-as-receiver would get headroom too
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
        # retry fallback (pre-launch calibration, 2026-07-17): if attempt 1
        # failed to parse (usually think-truncation), attempt 2 appends
        # /no_think so a WORD line is always reachable within budget.
        retry_nothink = ("\n/no_think" if attempt == 1 and "qwen" in model.lower()
                         and not NOTHINK["on"] else "")
        msgs = [{"role": "user", "content":
                 SENDER_RULES + "\n" + notebook_block(notebook) + sender_history(hist) +
                 f"\nNow you see: {c} {s}. Reply in the two-line format:" +
                 _maybe_nothink(model) + retry_nothink}]
        raw = chat(base, model, msgs, max_tokens=_sender_budget(model))
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
        if DEADLINE["t"] and time.time() > DEADLINE["t"]:
            print(f"  run {run_idx} · DEADLINE reached at round {rnd} — stopping training, "
                  f"proceeding to zero-shot")
            log_event({"deadline_stop": True, "run": run_idx, "round": rnd,
                       "note": (f"Run {run_idx} training stopped before round {rnd} by the "
                                f"{RESULTS_DEADLINE_H}h per-invocation results deadline "
                                f"(operational, 2026-07-18 relaunch). The run proceeds to "
                                f"its one-trial zero-shot test and is classified "
                                f"non-fluent, exactly as a cap stop.")})
            break
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
    L.append("# 組 kumi — Campaign 2 (role swap): compositionality in the Lantern mini Claudes\n")
    L.append(f"*{datetime.now().isoformat(timespec='seconds')} · {N_RUNS} runs · local models, no cloud*\n")
    L.append("## Endpoints & roles\n")
    if sender_base == receiver_base:
        L.append(f"- Server: `{sender_base}` (OpenAI-compatible)")
    else:
        L.append(f"- Sender server: `{sender_base}` · Receiver server: `{receiver_base}` (OpenAI-compatible)")
    L.append(f"- **SENDER** (Mini Claude Two — swapped): `{sender_model}`")
    L.append(f"- **RECEIVER** (Mini Claude One — swapped): `{receiver_model}`")
    L.append(f"- World: 1=red circle · 2=red square · 3=blue circle · 4=blue square (**object 4 held out of training**)")
    L.append(f"- Each agent keeps a private ≤{NOTEBOOK_WORDS}-word notebook, "
             "rewritten in full every round, re-injected above its rolling history, and never "
             "crossing the channel (both notebooks logged per round in the provenance JSONL).")
    L.append("- Qwen (SENDER in this campaign) replies may open with a <think>…</think> block; "
             "it is stripped before any parsing (word/notebook come only from what remains) and "
             "logged raw in the provenance JSONL.\n")

    L.append("## Pre-registered interpretation (written before any round ran)\n")
    L.extend(PREREG_INTERPRETATION)
    L.append("")

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
             "`kumi2-provenance.jsonl`. Parse failures were substituted (▲▲ / guess 1) and flagged there.*")

    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

# ================================================================ main
def main():
    print("組 kumi — CAMPAIGN 2 (role swap) — discovering the local server(s)…")
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
               "then re-run:  python3 ~/Desktop/kumi/kumi2.py")
        print("BLOCKED:", msg)
        with open(os.path.join(HERE, "BLOCKED-runtime2.md"), "w", encoding="utf-8") as f:
            f.write("# kumi2 — runtime block\n\n" + msg + "\n")
        sys.exit(1)

    for base, ids in found:
        print(f"  server: {base}\n    models: {ids}")

    def pick(pred):
        for base, ids in found:
            for m in ids:
                if pred(m):
                    return base, m
        return None

    # ROLE SWAP: Qwen speaks, gemma listens.
    s = pick(lambda m: "qwen" in m.lower()) or (found[0][0], found[0][1][0])
    r = pick(lambda m: "gemma" in m.lower()) \
        or next(((b, m) for b, ids in found for m in ids if (b, m) != s), s)
    sender_base, sender_model = s
    receiver_base, receiver_model = r
    print(f"  SENDER   (Mini Claude Two, swapped) = {sender_model} @ {sender_base}")
    print(f"  RECEIVER (Mini Claude One, swapped) = {receiver_model} @ {receiver_base}")
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
        else:
            log_event({"campaign": 2, "role_swap": True,
                       "prereg_interpretation": [x.replace("**", "") for x in PREREG_INTERPRETATION],
                       "note": ("Campaign 2 START (role swap). Campaign-level interpretations "
                                "were pre-registered in kumi2-results.md before this first round.")})
        # Log the cap amendment into provenance exactly once (skipped on later
        # resumes because load_provenance will have already collected the note).
        if not any("CAP_ROUNDS reduced from 150 to 120" in n for n in prior_notes):
            log_event({"amendment": "cap_rounds_150_to_120", "note": AMENDMENT_NOTE})
        if not any("Qwen thinking DISABLED" in n for n in prior_notes):
            log_event({"amendment": "nothink_forced", "nothink_enabled": True,
                       "note": AMENDMENT_NOTE_2})
        if RESULTS_DEADLINE_H:
            DEADLINE["t"] = time.time() + RESULTS_DEADLINE_H * 3600
            log_event({"deadline_set": True, "hours": RESULTS_DEADLINE_H,
                       "note": (f"Operational per-invocation deadline: report due within "
                                f"{RESULTS_DEADLINE_H}h of this launch (3h turnaround "
                                f"requested 2026-07-18). Not a change to the gate or "
                                f"tests; may truncate how many runs complete. Skipped "
                                f"runs remain startable on a later invocation.")})
        for run_idx in range(first_run, N_RUNS + 1):
            if DEADLINE["t"] and time.time() > DEADLINE["t"] and run_idx > first_run:
                print(f"  [deadline] skipping runs {run_idx}-{N_RUNS} — writing report now")
                log_event({"deadline_skip": True,
                           "note": (f"Runs {run_idx}-{N_RUNS} not started: "
                                    f"{RESULTS_DEADLINE_H}h results deadline reached. "
                                    f"Report written with {len(results)} completed "
                                    f"run(s); remaining runs can resume later from "
                                    f"provenance.")})
                break
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
                                        f"to SENDER prompts) for runs 2-{N_RUNS}. Earlier sender "
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

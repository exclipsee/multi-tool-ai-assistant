from pathlib import Path
import random
from utils import load_json, save_json
import os
import json
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

_LESSONS = Path(__file__).parent / "data" / "german_lessons.json"
_MEM = Path(__file__).parent / "memory.json"


def _load_lessons():
    return load_json(_LESSONS, {})


def generate_test(num_per_level=3):
    """Sample a few sentences per level and return a shuffled list of items.

    Each item: {"level": "A1", "sentence": "..."}
    """
    items = []
    for level, blocks in _load_lessons().get("levels", {}).items():
        pool = []
        for b in blocks:
            pool.extend(b.get("sentences", []))
        if not pool:
            continue
        picks = random.sample(pool, min(num_per_level, len(pool)))
        items.extend({"level": level, "sentence": s} for s in picks)
    random.shuffle(items)
    return items


def grade_test(responses, items, threshold=0.7):
    """Compute per-level averages from self-ratings and pick a recommended level."""
    scores = {}
    for r, it in zip(responses, items):
        scores.setdefault(it.get("level"), []).append(float(r))
    averages = {l: (sum(v) / len(v) if v else 0.0) for l, v in scores.items()}
    # choose highest level meeting threshold, else best average
    for lvl in sorted(averages.keys(), reverse=True):
        if averages.get(lvl, 0) >= threshold:
            return {"averages": averages, "recommended": lvl}
    if averages:
        best = max(averages.items(), key=lambda x: x[1])[0]
    else:
        best = None
    return {"averages": averages, "recommended": best}


def store_level(level):
    mem = load_json(_MEM, {})
    mem["learner_level"] = level
    return save_json(_MEM, mem)


def llm_grade_test(items, responses):
    """Use an LLM to grade user responses for placement.

    items: list of {"level":..., "sentence":...}
    responses: list of user strings (translations / short answers)

    Returns dict {averages, recommended, details: [{score, feedback}...]}
    Also stores `learner_level` using `store_level` if a recommendation is found.
    """
    # Try to use OpenAI Responses API if available
    client = None
    if OpenAI and os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI()
        except Exception:
            client = None

    details = []
    averages = {}

    if client:
        # Build a compact prompt listing items and responses
        entries = []
        for i, it in enumerate(items):
            entries.append({
                "index": i,
                "level": it.get("level"),
                "sentence": it.get("sentence"),
                "response": responses[i] if i < len(responses) else "",
            })

        system = (
            "You are a helpful grader. For each item (German sentence) and the user's provided English translation/answer, "
            "assign a score of 0.0 (incorrect), 0.5 (partially correct), or 1.0 (correct). Return JSON array of objects with "
            "fields: index, score (number), feedback (short string). Be concise."
        )

        user_text = json.dumps(entries, ensure_ascii=False)
        try:
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            resp = client.responses.create(model=model, input=f"{system}\n\nData:\n{user_text}")
            # extract text similar to patterns used elsewhere
            text = None
            try:
                text = getattr(resp, "output_text", None)
            except Exception:
                text = None
            if not text:
                try:
                    outv = getattr(resp, "output", None)
                    if outv and isinstance(outv, list) and outv:
                        first = outv[0]
                        if isinstance(first, dict):
                            cont = first.get("content") or first.get("data")
                            if isinstance(cont, list) and cont:
                                for c in cont:
                                    if isinstance(c, dict) and c.get("type") == "output_text":
                                        text = c.get("text")
                                        break
                                if not text:
                                    text = str(cont[0])
                except Exception:
                    text = None

            if text:
                try:
                    parsed = json.loads(text)
                    # parsed expected to be list
                    for obj in parsed:
                        idx = obj.get("index")
                        score = float(obj.get("score", 0.0))
                        fb = obj.get("feedback") or ""
                        details.append({"index": idx, "score": score, "feedback": fb})
                except Exception:
                    # fallback to naive per-item judgement if parsing fails
                    details = []
        except Exception:
            client = None

    if not details:
        # Heuristic fallback: compare word overlap between response and sentence (very rough)
        for i, it in enumerate(items):
            resp = responses[i] if i < len(responses) else ""
            s_words = [w.strip('.,!?').lower() for w in it.get("sentence", "").split() if w]
            r_words = [w.strip('.,!?').lower() for w in str(resp).split() if w]
            if not r_words:
                score = 0.0
                fb = "No answer provided."
            else:
                common = len(set(s_words) & set(r_words))
                denom = max(1, len(set(s_words)))
                ratio = common / denom
                if ratio > 0.6:
                    score = 1.0
                    fb = "Good comprehension/translation."
                elif ratio > 0.2:
                    score = 0.5
                    fb = "Partial understanding — some correct elements."
                else:
                    score = 0.0
                    fb = "Incorrect or unrelated."
            details.append({"index": i, "score": score, "feedback": fb})

    # compute per-level averages and recommended level
    by_level = {}
    for d in details:
        idx = d.get("index")
        lvl = items[idx].get("level")
        by_level.setdefault(lvl, []).append(d.get("score", 0.0))
    for l, vals in by_level.items():
        averages[l] = sum(vals) / len(vals) if vals else 0.0

    # choose highest level meeting threshold 0.7
    recommended = None
    for lvl in sorted(averages.keys(), reverse=True):
        if averages.get(lvl, 0) >= 0.7:
            recommended = lvl
            break
    if not recommended and averages:
        recommended = max(averages.items(), key=lambda x: x[1])[0]

    if recommended:
        try:
            store_level(recommended)
        except Exception:
            pass

    return {"averages": averages, "recommended": recommended, "details": details}

from pathlib import Path
import random
from .utils import load_json, save_json

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

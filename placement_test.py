from pathlib import Path
import random
from typing import List, Dict, Any
from .utils import load_json, save_json

PROJECT_ROOT = Path(__file__).resolve().parent
LESSONS_PATH = PROJECT_ROOT / "data" / "german_lessons.json"
MEMORY_PATH = PROJECT_ROOT / "memory.json"


def _load_lessons() -> Dict[str, Any]:
    return load_json(LESSONS_PATH, {})


def generate_test(num_per_level: int = 3) -> List[Dict[str, Any]]:
    """Return a list of test items drawn from lessons grouped by level.

    Each item is a dict:{"level": "A1", "title": ..., "sentence": ...}
    """
    lessons = _load_lessons().get("levels", {})
    items: List[Dict[str, Any]] = []
    for level, blocks in lessons.items():
        pool = []
        for b in blocks:
            pool.extend(b.get("sentences", []))
        if not pool:
            continue
        picks = random.sample(pool, min(num_per_level, len(pool)))
        for s in picks:
            items.append({"level": level, "sentence": s})

    # Shuffle so items are interleaved
    random.shuffle(items)
    return items


def grade_test(responses: List[float], items: List[Dict[str, Any]], threshold: float = 0.7) -> Dict[str, Any]:
    """Grade the placement test.

    `responses` should be parallel to `items` and contain scores in [0.0, 0.5, 1.0]
    representing "Don't understand", "Partly", "Understand well".

    Returns a dict with per-level averages and a recommended `level`.
    """
    scores_by_level: Dict[str, List[float]] = {}
    for resp, item in zip(responses, items):
        lvl = item.get("level")
        scores_by_level.setdefault(lvl, []).append(float(resp))

    averages: Dict[str, float] = {}
    for lvl, scores in scores_by_level.items():
        if scores:
            averages[lvl] = sum(scores) / len(scores)
        else:
            averages[lvl] = 0.0

    # Recommend the highest level where average >= threshold
    # Sort levels by name order (A1, A2, B1...)
    ordered = sorted(averages.items(), key=lambda x: x[0])
    recommended = None
    for lvl, avg in ordered[::-1]:  # from highest to lowest
        if avg >= threshold:
            recommended = lvl
            break

    # Fallback: if nothing meets threshold, pick highest with best avg
    if not recommended:
        best = max(averages.items(), key=lambda x: x[1], default=(None, 0.0))
        recommended = best[0]

    return {"averages": averages, "recommended": recommended}


def store_level(level: str) -> bool:
    mem = load_json(MEMORY_PATH, {})
    mem["learner_level"] = level
    return save_json(MEMORY_PATH, mem)

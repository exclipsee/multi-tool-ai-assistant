"""Simple SM-2 Spaced Repetition helper.

Provides basic card model stored inside `memory.json` under key `srs_cards`.
Functions:
- add_card(front, back)
- import_attempts(attempts_list)
- get_due_cards(now)
- schedule_card(card_id, quality)

This is intentionally small and dependency-free.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from pathlib import Path
import datetime
import json
import uuid

PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_PATH = PROJECT_ROOT / "memory.json"


def _load_memory() -> Dict[str, Any]:
    if MEMORY_PATH.exists():
        try:
            return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_memory(mem: Dict[str, Any]):
    try:
        MEMORY_PATH.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _mk_card(front: str, back: str) -> Dict[str, Any]:
    return {
        "id": f"c-{uuid.uuid4().hex[:8]}",
        "front": front,
        "back": back,
        "repetitions": 0,
        "interval": 0,
        "efactor": 2.5,
        "next_review": _now().isoformat(),
        "created": _now().isoformat(),
    }


def add_card(front: str, back: str) -> Dict[str, Any]:
    mem = _load_memory()
    cards = mem.get("srs_cards", [])
    # avoid exact duplicates by front text
    for c in cards:
        if c.get("front") == front:
            return c
    card = _mk_card(front, back)
    cards.append(card)
    mem["srs_cards"] = cards
    _save_memory(mem)
    return card


def import_attempts(attempts: List[Dict[str, Any]]) -> int:
    """Import `german_attempts` entries as cards. Returns number imported."""
    if not attempts:
        return 0
    mem = _load_memory()
    cards = mem.get("srs_cards", [])
    fronts = {c.get("front"): c for c in cards}
    added = 0
    for a in attempts:
        front = a.get("original") or a.get("sentence")
        back = a.get("correction") or ""
        if not front:
            continue
        if front in fronts:
            continue
        card = _mk_card(front, back)
        cards.append(card)
        added += 1
    if added:
        mem["srs_cards"] = cards
        _save_memory(mem)
    return added


def get_due_cards(now: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    now = now or _now()
    mem = _load_memory()
    cards = mem.get("srs_cards", [])
    due = []
    for c in cards:
        try:
            nr = datetime.datetime.fromisoformat(c.get("next_review"))
        except Exception:
            nr = _now()
        if nr <= now:
            due.append(c)
    # sort by next_review asc
    due.sort(key=lambda x: x.get("next_review"))
    return due


def _update_card_in_memory(card: Dict[str, Any]):
    mem = _load_memory()
    cards = mem.get("srs_cards", [])
    for i, c in enumerate(cards):
        if c.get("id") == card.get("id"):
            cards[i] = card
            mem["srs_cards"] = cards
            _save_memory(mem)
            return True
    return False


def schedule_card(card_id: str, quality: int) -> Optional[Dict[str, Any]]:
    """Schedule card using SM-2 algorithm.

    quality: 0-5 (5 perfect). Returns updated card or None.
    """
    mem = _load_memory()
    cards = mem.get("srs_cards", [])
    card = None
    for c in cards:
        if c.get("id") == card_id:
            card = c
            break
    if not card:
        return None

    q = max(0, min(5, int(quality)))

    # SM-2 core
    if q < 3:
        card["repetitions"] = 0
        card["interval"] = 1
        # next review in 1 day
        card["next_review"] = (_now() + datetime.timedelta(days=1)).isoformat()
    else:
        ef = float(card.get("efactor", 2.5))
        reps = int(card.get("repetitions", 0)) + 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = int(round(card.get("interval", 1) * ef))

        # update efactor
        ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if ef < 1.3:
            ef = 1.3

        card["efactor"] = round(ef, 4)
        card["repetitions"] = reps
        card["interval"] = int(interval)
        card["next_review"] = (_now() + datetime.timedelta(days=int(interval))).isoformat()

    _update_card_in_memory(card)
    return card


if __name__ == "__main__":
    # simple smoke test
    print("SRS helper — adding sample card")
    c = add_card("ich habe ein haus", "Ich habe ein Haus.")
    print(c)
    print("Due now:", get_due_cards())

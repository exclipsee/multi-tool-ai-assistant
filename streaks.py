from pathlib import Path
import json
import datetime
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_PATH = PROJECT_ROOT / "memory.json"


def _load_memory() -> Dict[str, Any]:
    if MEMORY_PATH.exists():
        try:
            return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_memory(data: Dict[str, Any]):
    try:
        MEMORY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _today_str() -> str:
    return datetime.date.today().isoformat()


def _compute_streak(days: Dict[str, Any], today: str) -> int:
    # days: mapping date->data; compute consecutive days up to today
    if not days:
        return 0
    # collect dates that have any activity
    active_dates = sorted([d for d in days.keys()])
    # starting from today, walk backwards
    streak = 0
    cur = datetime.date.fromisoformat(today)
    while True:
        key = cur.isoformat()
        if key in days and (days[key].get("visits", 0) + days[key].get("assessments", 0)) > 0:
            streak += 1
            cur = cur - datetime.timedelta(days=1)
        else:
            break
    return streak


def record_visit():
    """Record that the user opened the German Tutor (a visit for today)."""
    today = _today_str()
    mem = _load_memory()
    activity = mem.setdefault("study_activity", {})
    days = activity.setdefault("days", {})
    day = days.setdefault(today, {"visits": 0, "assessments": 0})
    day["visits"] = day.get("visits", 0) + 1
    activity["days"] = days
    activity["last_active"] = today
    mem["study_activity"] = activity
    _save_memory(mem)
    # Possibly update badges later (lazy via get_streak_info)


def record_assessment():
    """Record that the user completed an assessment (increment counters)."""
    today = _today_str()
    mem = _load_memory()
    activity = mem.setdefault("study_activity", {})
    days = activity.setdefault("days", {})
    day = days.setdefault(today, {"visits": 0, "assessments": 0})
    day["assessments"] = day.get("assessments", 0) + 1
    activity["days"] = days
    # update totals
    total = activity.get("total_assessments", 0) + 1
    activity["total_assessments"] = total
    activity["last_active"] = today
    mem["study_activity"] = activity
    _save_memory(mem)


def get_streak_info() -> Dict[str, Any]:
    """Return a dict with streak metrics and badge names earned."""
    mem = _load_memory()
    activity = mem.get("study_activity", {})
    days = activity.get("days", {})
    today = _today_str()
    streak = _compute_streak(days, today)
    total_assessments = activity.get("total_assessments", 0)
    total_days_active = len([d for d in days.keys() if (days[d].get("visits", 0) + days[d].get("assessments", 0)) > 0])

    # Badges (simple set)
    badges = activity.get("badges", {})
    earned = set(badges.keys())
    newly_earned = []

    # Define badge conditions
    conditions = [
        ("First Activity", lambda s, t: total_days_active >= 1),
        ("3-Day Streak", lambda s, t: s >= 3),
        ("7-Day Streak", lambda s, t: s >= 7),
        ("30-Day Streak", lambda s, t: s >= 30),
        ("10 Assessments", lambda s, t: t >= 10),
    ]

    for name, cond in conditions:
        if cond(streak, total_assessments) and name not in earned:
            # award badge
            badges[name] = datetime.datetime.now().isoformat()
            newly_earned.append(name)
            earned.add(name)

    # persist any new badges
    activity["badges"] = badges
    mem["study_activity"] = activity
    _save_memory(mem)

    return {
        "streak": streak,
        "total_assessments": total_assessments,
        "total_days_active": total_days_active,
        "badges": list(earned),
        "newly_earned": newly_earned,
        "last_active": activity.get("last_active"),
    }

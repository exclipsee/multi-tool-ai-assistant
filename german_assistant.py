"""Lightweight German learning helper.

Provides: assess_sentence(sentence, level='A1') and generate_tasks(...)

This module is intentionally dependency-free and uses simple heuristics
to provide quick feedback and exercises. It's a starting point you can
expand with models or third-party NLP libraries later.
"""
from typing import List, Dict, Any, Optional
import random
from pathlib import Path
import json
import datetime

# memory file (store attempts/preferences)
PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_PATH = PROJECT_ROOT / "memory.json"
PERSONA_PATH = PROJECT_ROOT / "german_persona.json"

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

def _load_persona() -> Dict[str, Any]:
    # defaults
    persona = {"default_level": "A1", "strictness": "balanced", "save_attempts": True}
    if PERSONA_PATH.exists():
        try:
            p = json.loads(PERSONA_PATH.read_text(encoding="utf-8"))
            persona.update(p)
        except Exception:
            pass
    return persona

# Small lexicons and heuristics for basic checks
COMMON_NOUNS = {
    "Haus": "das",
    "Auto": "das",
    "Mann": "der",
    "Frau": "die",
    "Tag": "der",
    "Kind": "das",
    "Tisch": "der",
    "Stuhl": "der",
    "Buch": "das",
    "Freund": "der",
}

COMMON_VERBS = {"ist", "hat", "geht", "kommt", "macht", "sehen", "sieht", "isst", "lernt", "arbeitet", "spielt", "sprechen", "spricht"}

def _capitalize_nouns_check(words: List[str]) -> List[Dict[str, str]]:
    issues = []
    for i, w in enumerate(words):
        bare = w.strip('.,!?')
        if not bare:
            continue
        # naive: if lowercased form matches a known noun but original isn't capitalized
        for noun in COMMON_NOUNS:
            if bare.lower() == noun.lower() and not bare[0].isupper():
                issues.append({
                    "word": bare,
                    "suggestion": noun,
                    "explanation": "German nouns must be capitalized (Nomen werden großgeschrieben).",
                })
    return issues

def _verb_second_position_check(words: List[str]) -> Dict[str, Any]:
    # Very naive check: if a known verb is not in second position, flag it.
    res = {"ok": True, "detail": None}
    if len(words) < 2:
        return res
    # find index of first known verb
    for idx, w in enumerate(words):
        bare = w.strip('.,!?').lower()
        if bare in COMMON_VERBS:
            # verb should often be at index 1 (second position) in main clauses
            if idx != 1:
                res["ok"] = False
                res["detail"] = {
                    "verb": bare,
                    "found_index": idx,
                    "suggestion": "Place the conjugated verb in second position in main clauses (Verb-Zweitstellung)."
                }
            return res
    return res

def assess_sentence(sentence: str, level: Optional[str] = None, persona: Optional[Dict[str, Any]] = None, save_attempt: Optional[bool] = None) -> Dict[str, Any]:
    """Assess a German sentence with simple heuristics.

    Returns a dict with a numeric `score` (0-100), list of `errors`, a
    `correction` suggestion, and short `explanations`.
    """
    # Use persona/defaults
    p = persona or _load_persona()
    if level is None:
        level = p.get("default_level", "A1")
    if save_attempt is None:
        save_attempt = bool(p.get("save_attempts", True))

    original = sentence.strip()
    words = original.split()
    errors = []

    # Basic punctuation
    if not original.endswith('.') and not original.endswith('!') and not original.endswith('?'):
        errors.append({"type": "punctuation", "message": "Sentence should end with a punctuation mark (., !, ?)."})

    # Capitalization of first letter
    if original and not original[0].isupper():
        errors.append({"type": "capitalization_first", "message": "Sentence should start with a capital letter."})

    # Noun capitalization
    noun_issues = _capitalize_nouns_check(words)
    for n in noun_issues:
        errors.append({"type": "noun_capitalization", "word": n["word"], "message": n["explanation"], "suggestion": n["suggestion"]})

    # Verb position
    verb_check = _verb_second_position_check(words)
    if not verb_check["ok"]:
        errors.append({"type": "verb_position", "detail": verb_check["detail"], "message": "In main clauses, the conjugated verb often appears in second position."})

    # Article-noun agreement (naive)
    for i, w in enumerate(words[:-1]):
        bare = w.strip('.,!?')
        next_word = words[i+1].strip('.,!?')
        if bare.lower() in {"der","die","das"}:
            # check next_word against COMMON_NOUNS if present
            for noun, correct_article in COMMON_NOUNS.items():
                if next_word.lower() == noun.lower() and bare.lower() != correct_article:
                    errors.append({"type": "article_agreement", "message": f"Article '{bare}' may not agree with noun '{next_word}'. Suggested: '{correct_article} {noun}'.", "suggestion": f"{correct_article} {noun}"})

    # Compute a simple score
    deduction = len(errors) * 15
    score = max(0, 100 - deduction)

    # Formulate a simple correction: try to apply noun capitalization fixes and punctuation
    corrected = original
    for e in noun_issues:
        # replace lowercase noun with capitalized suggestion
        corrected = corrected.replace(e["word"], e["suggestion"])
    if not corrected.endswith(('.', '!', '?')):
        corrected = corrected + '.'
    if corrected and not corrected[0].isupper():
        corrected = corrected[0].upper() + corrected[1:]

    result = {
        "original": original,
        "score": score,
        "errors": errors,
        "correction": corrected,
        "explanations": [e.get("message") for e in errors],
        "level": level,
        "strictness": p.get("strictness") if isinstance(p, dict) else None,
    }

    # Persist attempt if requested
    try:
        if save_attempt:
            mem = _load_memory()
            attempts = mem.get("german_attempts", [])
            attempts.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "original": original,
                "correction": corrected,
                "score": score,
                "errors": [e.get("message") for e in errors],
                "level": level,
            })
            mem["german_attempts"] = attempts
            _save_memory(mem)
    except Exception:
        pass

    return result


def generate_tasks(sentence: str, level: str = "A1", num_tasks: int = 3, task_types: List[str] = None) -> List[Dict[str, Any]]:
    """Generate simple learning tasks based on the given sentence.

    Task types supported: 'correction', 'fill_blank', 'multiple_choice', 'translation', 'roleplay'
    """
    if task_types is None:
        task_types = ["correction", "fill_blank", "translation"]
    tasks = []

    words = sentence.strip().split()
    # choose words to mask (not too small)
    candidate_indices = [i for i,w in enumerate(words) if len(w.strip('.,!?')) > 3]
    for i in range(min(num_tasks, len(task_types))):
        ttype = task_types[i]
        if ttype == "correction":
            tasks.append({
                "type": "correction",
                "prompt": f"Correct the sentence and explain your changes: {sentence}",
                "answer_example": assess_sentence(sentence, level)
            })
        elif ttype == "fill_blank":
            if candidate_indices:
                idx = random.choice(candidate_indices)
                masked = words.copy()
                masked[idx] = '_____'
                prompt = "Fill in the blank: " + " ".join(masked)
                answer = words[idx].strip('.,!?')
                tasks.append({"type": "fill_blank", "prompt": prompt, "answer": answer})
        elif ttype == "multiple_choice":
            if candidate_indices:
                idx = random.choice(candidate_indices)
                correct = words[idx].strip('.,!?')
                # create three distractors by simple modifications
                distractors = [correct.capitalize(), correct.lower(), correct + 'en']
                options = list(dict.fromkeys([correct] + distractors))[:4]
                random.shuffle(options)
                prompt = f"Choose the correct word for the blank in: {' '.join(words[:idx] + ['_____'] + words[idx+1:])}"
                tasks.append({"type":"multiple_choice","prompt":prompt,"options":options,"answer":correct})
        elif ttype == "translation":
            tasks.append({"type":"translation","prompt":f"Translate to English: {sentence}","answer_example":"(user to provide)"})
        elif ttype == "roleplay":
            tasks.append({"type":"roleplay","prompt":f"Roleplay: respond in German as a native speaker to: '{sentence}'","note":"Encourage a short reply of 1-3 sentences."})

    return tasks


def generate_followup(assessment: Dict[str, Any]) -> Dict[str, Any]:
    """Create a short targeted follow-up prompt based on the assessment result.

    Returns a dict {role: 'assistant', prompt: str, intent: str}
    """
    # Default follow-up
    intent = "general_practice"
    prompt = "Good. Try to write another short sentence using the same idea."

    errors = assessment.get("errors", []) or []
    msgs = [e.get("message") if isinstance(e, dict) else str(e) for e in errors]

    # Heuristic routing based on common error types
    if any((e.get("type") == "noun_capitalization" or "Nomen" in (e.get("message") or "")) for e in errors if isinstance(e, dict)):
        intent = "capitalize_nouns"
        prompt = "Focus on capitalizing nouns. Rewrite the sentence with correct noun capitalization."
    elif any((e.get("type") == "verb_position" ) for e in errors if isinstance(e, dict)):
        intent = "verb_position"
        prompt = "Pay attention to verb position. Try forming a short main clause where the conjugated verb is in second position."
    elif any((e.get("type") == "article_agreement") for e in errors if isinstance(e, dict)):
        intent = "article_agreement"
        prompt = "Check article and noun agreement. Rewrite the sentence using the correct article for the noun."
    elif any("punctuation" in (m or "") for m in msgs):
        intent = "punctuation"
        prompt = "Add correct punctuation. Write the sentence with appropriate punctuation (., !, ?)."
    else:
        # If score low, ask to try a simplified repetition
        score = assessment.get("score", 100)
        if score < 70:
            intent = "simplify_and_repeat"
            prompt = "Try to rewrite the sentence more simply and correctly (short sentence, present tense)."
        else:
            intent = "expand"
            prompt = "Nice! Now write a follow-up sentence that expands the idea (1-2 short sentences)."

    return {"role": "assistant", "prompt": prompt, "intent": intent}


def track_mistakes(assessment: Dict[str, Any]):
    """Record mistake types and counts to `memory.json` under key `german_mistakes`.

    This helps the Conversational Tutor adapt over time.
    """
    try:
        mem_path = PROJECT_ROOT / "memory.json"
        mem = {}
        if mem_path.exists():
            try:
                mem = json.loads(mem_path.read_text(encoding="utf-8"))
            except Exception:
                mem = {}
        mistakes = mem.get("german_mistakes", {})
        for e in assessment.get("errors", []):
            if isinstance(e, dict):
                key = e.get("type") or e.get("message") or "unknown"
            else:
                key = str(e)
            mistakes[key] = mistakes.get(key, 0) + 1
        mem["german_mistakes"] = mistakes
        try:
            mem_path.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    except Exception:
        pass


if __name__ == '__main__':
    example = "ich habe ein haus"
    print("Assessing:", example)
    res = assess_sentence(example)
    print(res)
    print('\nGenerated tasks:')
    for t in generate_tasks(example, num_tasks=3):
        print(t)

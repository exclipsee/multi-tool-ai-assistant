"""Lightweight German learning helper.

Provides: assess_sentence(sentence, level='A1') and generate_tasks(...)

This module is intentionally dependency-free and uses simple heuristics
to provide quick feedback and exercises. It's a starting point you can
expand with models or third-party NLP libraries later.
"""
from typing import List, Dict, Any
import random

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

def assess_sentence(sentence: str, level: str = "A1") -> Dict[str, Any]:
    """Assess a German sentence with simple heuristics.

    Returns a dict with a numeric `score` (0-100), list of `errors`, a
    `correction` suggestion, and short `explanations`.
    """
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

    return {
        "original": original,
        "score": score,
        "errors": errors,
        "correction": corrected,
        "explanations": [e.get("message") for e in errors]
    }

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


if __name__ == '__main__':
    example = "ich habe ein haus"
    print("Assessing:", example)
    res = assess_sentence(example)
    print(res)
    print('\nGenerated tasks:')
    for t in generate_tasks(example, num_tasks=3):
        print(t)

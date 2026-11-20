"""
Eligibility pre-screener: compares a patient's answers with a trial's eligibility_rules.
Pure logic, no database, so it is easy to test. Nothing a patient enters here is stored.
"""
from typing import Any, Dict, List, Optional

MET, NOT_MET, UNKNOWN = "met", "not_met", "unknown"


def _check(criterion: str, outcome: str, detail: str) -> Dict[str, str]:
    return {"criterion": criterion, "status": outcome, "detail": detail}


def screen(rules: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    rules:   {min_age, max_age, gender, conditions, inclusion_list, exclusion_list} (all optional)
    answers: {age, gender, conditions, inclusion_answers: {text: bool}, exclusion_answers: {text: bool}}
    Returns {result, score, breakdown}. result is eligible, not_eligible or possibly_eligible
    (nothing failed but some criteria were not answered).
    """
    checks: List[Dict[str, str]] = []
    age: Optional[int] = answers.get("age")

    if rules.get("min_age") is not None:
        if age is None:
            checks.append(_check("Minimum age", UNKNOWN, f"Must be {rules['min_age']} or older"))
        else:
            ok = age >= rules["min_age"]
            checks.append(_check("Minimum age", MET if ok else NOT_MET, f"Must be {rules['min_age']} or older"))

    if rules.get("max_age") is not None:
        if age is None:
            checks.append(_check("Maximum age", UNKNOWN, f"Must be {rules['max_age']} or younger"))
        else:
            ok = age <= rules["max_age"]
            checks.append(_check("Maximum age", MET if ok else NOT_MET, f"Must be {rules['max_age']} or younger"))

    required_gender = (rules.get("gender") or "all").lower()
    if required_gender != "all":
        given = (answers.get("gender") or "").lower()
        outcome = UNKNOWN if not given else (MET if given == required_gender else NOT_MET)
        checks.append(_check("Gender", outcome, f"Open to {required_gender} participants"))

    trial_conditions = [c.lower() for c in rules.get("conditions") or []]
    if trial_conditions:
        given = [c.lower() for c in answers.get("conditions") or []]
        if not given:
            outcome = UNKNOWN
        else:
            # "Type 2 Diabetes" matches "diabetes" and the other way round
            outcome = MET if any(t in g or g in t for t in trial_conditions for g in given) else NOT_MET
        checks.append(_check("Condition", outcome, "Has: " + ", ".join(rules["conditions"])))

    inclusion_answers = answers.get("inclusion_answers") or {}
    for item in rules.get("inclusion_list") or []:
        value = inclusion_answers.get(item)
        outcome = UNKNOWN if value is None else (MET if value else NOT_MET)
        checks.append(_check(item, outcome, "Required"))

    exclusion_answers = answers.get("exclusion_answers") or {}
    for item in rules.get("exclusion_list") or []:
        value = exclusion_answers.get(item)
        outcome = UNKNOWN if value is None else (NOT_MET if value else MET)
        checks.append(_check(item, outcome, "Must not apply"))

    met = sum(c["status"] == MET for c in checks)
    score = round(100 * met / len(checks)) if checks else 100
    if any(c["status"] == NOT_MET for c in checks):
        result = "not_eligible"
    elif any(c["status"] == UNKNOWN for c in checks):
        result = "possibly_eligible"
    else:
        result = "eligible"
    return {"result": result, "score": score, "breakdown": checks}

"""
Rules for the automatic community filter (English only for now).

Every new or edited post and comment is checked against these rules. Each rule is a
regular expression (matched without regard to case) with a weight between 0 and 1.
A text's score is the sum of the weights of the rules it matches, capped at 1:

    score < FLAG_THRESHOLD                   published as usual
    FLAG_THRESHOLD <= score < HOLD_THRESHOLD published, and a report goes to the moderation queue
    score >= HOLD_THRESHOLD                  held as "pending" until a moderator approves it

The medical team can add, remove or re-weight rules in this file; no other code needs to change.
Tips:
  - \b marks a word boundary, so r"\bcure\b" does not match "secure".
  - Keep weights for single words low: a patient asking "is it true that X cures Y?" must not be held.
  - A rule's category is the reason shown in the moderation queue.
"""

from dataclasses import dataclass

FLAG_THRESHOLD = 0.3
HOLD_THRESHOLD = 0.7

# Self-harm language is never enough on its own to hold a post: the person may need support,
# not silence. It is sent to the top of the queue instead (see SELF_HARM below).
CATEGORY_MAX_WEIGHT = {"self_harm": FLAG_THRESHOLD}


@dataclass(frozen=True)
class Rule:
    pattern: str
    weight: float
    label: str


# Categories use the report reasons stored in content_reports.reason.

MISINFORMATION = [
    Rule(r"\bvaccines?\s+(cause|causes|caused)\s+autism\b", 0.7, "vaccines cause autism"),
    Rule(r"\b(drink|drinking|take|taking)\s+(bleach|mms|chlorine dioxide|turpentine)\b", 0.8, "drinking harmful substances"),
    Rule(r"\b(miracle|secret|guaranteed)\s+cure\b", 0.4, "miracle cure"),
    Rule(r"\b100\s*%\s*(cure|cured|effective)\b", 0.4, "100% cure"),
    Rule(r"\b(cures?|cured|reverses?)\s+(cancer|diabetes|hiv|aids|autism|alzheimer'?s)\b", 0.4, "claims to cure a serious disease"),
    Rule(r"\bstop\s+taking\s+(your|their)\s+(medication|medicine|meds|insulin|chemo|treatment)\b", 0.5, "telling others to stop treatment"),
    Rule(r"\b(chemo|chemotherapy|vaccines?)\s+(is|are)\s+(poison|a scam|useless)\b", 0.5, "treatment is poison or a scam"),
    Rule(r"\bdoctors\s+(don'?t|do not)\s+want\s+you\s+to\s+know\b", 0.3, "doctors don't want you to know"),
    Rule(r"\bbig\s+pharma\s+(is\s+)?(hiding|hides|covering up)\b", 0.3, "big pharma is hiding a cure"),
]

HARASSMENT = [
    Rule(r"\b(kill\s+yourself|kys)\b", 0.8, "telling someone to kill themselves"),
    Rule(r"\bi\s*('ll|will|am going to|'m going to)\s+(find|hurt|kill|beat)\s+you\b", 0.9, "threat of violence"),
    Rule(r"\byou\s*(are|'re|r)\s+(an?\s+)?(idiot|moron|stupid|loser|pathetic|worthless|disgusting)\b", 0.5, "insulting another member"),
    Rule(r"\bnobody\s+cares\s+about\s+you\b", 0.4, "demeaning another member"),
    Rule(r"\b(idiot|moron|imbecile)s?\b", 0.2, "insult"),
    Rule(r"\bshut\s+up\b", 0.2, "hostile language"),
]

INAPPROPRIATE_CONTENT = [
    Rule(r"\bf+u+c+k+(ing|er|ed)?\b", 0.3, "profanity"),
    Rule(r"\bs+h+i+t+(ty)?\b", 0.3, "profanity"),
    Rule(r"\b(bitch|bastard|asshole|dickhead)s?\b", 0.3, "profanity"),
]

SELF_HARM = [
    Rule(r"\b(kill|hurt|harm)\s+myself\b", 0.3, "self-harm"),
    Rule(r"\bend\s+my\s+(own\s+)?life\b", 0.3, "self-harm"),
    Rule(r"\b(want|wanted)\s+to\s+die\b", 0.3, "self-harm"),
    Rule(r"\bsuicid(e|al)\b", 0.3, "suicide"),
    Rule(r"\bno\s+reason\s+to\s+live\b", 0.3, "self-harm"),
]

SPAM = [
    Rule(r"\b(buy|order)\s+now\b", 0.3, "sales language"),
    Rule(r"\bclick\s+(here|the\s+link|this\s+link)\b", 0.3, "click here"),
    Rule(r"\blimited\s+(time\s+)?offer\b", 0.3, "limited offer"),
    Rule(r"\bearn\s+\$?\d+[\d,]*\s*(per|a|every)\s+(day|week|hour)\b", 0.5, "earn money fast"),
    Rule(r"\b(contact|message|text|dm)\s+me\s+(on|via)\s+(whatsapp|telegram|signal)\b", 0.4, "move the conversation off the platform"),
    Rule(r"\b(cheap|discount)\s+(meds|pills|medication|viagra)\b", 0.6, "selling medication"),
]

RULES = {
    "misinformation": MISINFORMATION,
    "harassment": HARASSMENT,
    "inappropriate_content": INAPPROPRIATE_CONTENT,
    "self_harm": SELF_HARM,
    "spam": SPAM,
}

# Spam signals that are counted rather than matched
LINKS_TO_FLAG = 3   # this many links or more: weight LINKS_FLAG_WEIGHT
LINKS_TO_HOLD = 6   # this many links or more: weight LINKS_HOLD_WEIGHT
LINKS_FLAG_WEIGHT = 0.4
LINKS_HOLD_WEIGHT = 0.7
SHOUTING_MIN_LETTERS = 30   # only check texts with at least this many letters
SHOUTING_RATIO = 0.7        # share of capital letters counted as shouting
SHOUTING_WEIGHT = 0.2
REPEATED_CHARACTERS = 10    # the same character this many times in a row, e.g. "!!!!!!!!!!"
REPEATED_WEIGHT = 0.2

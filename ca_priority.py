# ca_priority.py

import re
from typing import Tuple, Optional


CALIFORNIA_KEYWORDS = [
    "california",
    ", ca",
    " ca ",
    " los angeles",
    " san francisco",
    " san diego",
    " sacramento",
    " san jose",
    " oakland",
    " fresno",
    " long beach",
    " bay area",
    " palm springs",
    " santa barbara",
    " orange county",
    " san mateo",
    " san rafael",
    " san luis obispo",
]


def normalise_location(location: Optional[str]) -> str:
    """
    Normalise a location string to lowercase for matching.
    """
    if not location:
        return ""
    return str(location).strip().lower()


def is_california_location(location: Optional[str]) -> bool:
    """
    Decide whether a free-text location looks like it's in California.

    Rules:
    - Match common CA keywords and city names.
    - Treat any US ZIP starting with 9xxxx as CA-priority by default.
      (This is a heuristic and can be tightened later.)
    """
    loc = normalise_location(location)
    if not loc:
        return False

    for kw in CALIFORNIA_KEYWORDS:
        if kw in loc:
            return True

    # Heuristic: any 9xxxx ZIP is treated as CA-priority for business purposes.
    zip_matches = re.findall(r"\b9\d{4}\b", loc)
    if zip_matches:
        return True

    return False


def apply_ca_priority(
    base_score: Optional[float],
    location: Optional[str],
    ca_boost: float = 2.0,
) -> Tuple[float, bool]:
    """
    Apply California priority without excluding non-CA leads.

    - If base_score is None, treat it as 0.0.
    - If location looks Californian, add ca_boost to the score and mark is_ca_priority=True.
    - Otherwise, leave the score unchanged and mark is_ca_priority=False.

    Returns:
        priority_score, is_ca_priority
    """
    if base_score is None:
        base_value = 0.0
    else:
        try:
            base_value = float(base_score)
        except (TypeError, ValueError):
            base_value = 0.0

    is_ca = is_california_location(location)
    if is_ca:
        return base_value + float(ca_boost), True
    return base_value, False

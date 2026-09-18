"""
ROLEX AI — Answer Verification / Hallucination Detection
Cross-checks provider answers, flags low-confidence or contradictory output.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from modules.logger import get_logger
from modules.providers import AIResponse

log = get_logger("rolex.verification")

_HEDGE_PHRASES = (
    "i'm not sure", "i am not sure", "i don't know", "i cannot", "i can't",
    "as an ai", "i think maybe", "possibly", "not certain", "unclear",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def detect_hedging(text: str) -> bool:
    low = _normalize(text)
    return any(p in low for p in _HEDGE_PHRASES)


def verify(responses: List[AIResponse], threshold: float = 0.55) -> Dict:
    """
    Verify a set of provider responses.
    Returns a report with confidence, agreement and flags.
    """
    ok = [r for r in responses if r.ok and r.text.strip()]
    report = {
        "num_responses": len(responses),
        "num_valid": len(ok),
        "confidence": 0.0,
        "agreement": 0.0,
        "flags": [],
        "consensus": None,
    }
    if not ok:
        report["flags"].append("no_valid_response")
        return report

    if len(ok) == 1:
        r = ok[0]
        report["consensus"] = r.text
        report["confidence"] = 0.5 if r.provider == "local" else 0.7
        if detect_hedging(r.text):
            report["flags"].append("hedging_language")
            report["confidence"] -= 0.2
        return report

    # Pairwise agreement
    sims = []
    for i in range(len(ok)):
        for j in range(i + 1, len(ok)):
            sims.append(similarity(ok[i].text, ok[j].text))
    agreement = sum(sims) / len(sims) if sims else 0.0
    report["agreement"] = round(agreement, 3)

    # Consensus = longest response (usually most complete)
    consensus = max(ok, key=lambda r: len(r.text))
    report["consensus"] = consensus.text

    confidence = 0.4 + 0.5 * agreement
    if any(detect_hedging(r.text) for r in ok):
        report["flags"].append("hedging_language")
        confidence -= 0.1
    if agreement < threshold:
        report["flags"].append("low_agreement")
    report["confidence"] = round(max(0.0, min(1.0, confidence)), 3)
    return report


def is_reliable(report: Dict, min_confidence: float = 0.5) -> bool:
    return report.get("confidence", 0.0) >= min_confidence and "no_valid_response" not in report.get("flags", [])

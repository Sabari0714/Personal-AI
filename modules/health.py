"""
ROLEX AI — Health Information Support
General, educational health information and simple wellness calculators.

IMPORTANT: This module provides general information only. It is NOT a
substitute for professional medical advice, diagnosis or treatment. Every
response includes a clear disclaimer, and red-flag symptoms are escalated to
"seek emergency care" guidance.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.health")

DISCLAIMER = ("This is general health information, not medical advice. "
              "Please consult a qualified doctor for diagnosis or treatment.")

# Emergency red-flag symptoms -> escalate immediately.
_RED_FLAGS = [
    "chest pain", "heart attack", "can't breathe", "cannot breathe",
    "severe bleeding", "unconscious", "stroke", "face drooping",
    "slurred speech", "suicidal", "seizure", "severe head injury",
    "marana", "moochu vidala", "nenju vali",
]

# A small, curated knowledge base of common topics (educational).
_TOPICS: Dict[str, Dict] = {
    "fever": {
        "summary": "Fever is a temporary rise in body temperature, usually a sign "
                   "the body is fighting an infection.",
        "self_care": ["Rest and drink plenty of fluids", "Use a light blanket",
                      "Paracetamol may help (follow label/doctor advice)"],
        "see_doctor": ["Fever above 39°C / 102°F", "Lasts more than 3 days",
                       "With rash, stiff neck, or confusion"],
    },
    "cold": {
        "summary": "The common cold is a viral infection of the nose and throat.",
        "self_care": ["Warm fluids", "Steam inhalation", "Rest"],
        "see_doctor": ["Symptoms last > 10 days", "High fever", "Difficulty breathing"],
    },
    "diabetes": {
        "summary": "Diabetes is a chronic condition where blood sugar is too high.",
        "self_care": ["Balanced diet", "Regular exercise", "Monitor sugar as advised"],
        "see_doctor": ["Very high/low sugar readings", "Frequent urination + thirst",
                       "Wounds that don't heal"],
    },
    "blood pressure": {
        "summary": "Blood pressure is the force of blood against artery walls. "
                   "Normal is around 120/80 mmHg.",
        "self_care": ["Reduce salt", "Exercise", "Manage stress", "Avoid smoking"],
        "see_doctor": ["Readings consistently above 140/90", "Severe headache",
                       "Vision changes"],
    },
    "headache": {
        "summary": "Headaches range from tension-type to migraine.",
        "self_care": ["Rest in a quiet, dark room", "Hydrate", "Cold compress"],
        "see_doctor": ["Sudden severe 'worst ever' headache", "With fever/stiff neck",
                       "After head injury"],
    },
    "covid": {
        "summary": "COVID-19 is a respiratory illness caused by the SARS-CoV-2 virus.",
        "self_care": ["Isolate", "Hydrate", "Monitor oxygen if available"],
        "see_doctor": ["Difficulty breathing", "Chest pain", "Oxygen below 94%"],
    },
}


class HealthAdvisor:
    def check_emergency(self, text: str) -> Optional[str]:
        low = (text or "").lower()
        for flag in _RED_FLAGS:
            if flag in low:
                return ("⚠️ This may be a medical emergency. Please call your local "
                        "emergency number (e.g. 108 / 112 in India) or go to the "
                        "nearest hospital immediately.")
        return None

    def lookup(self, topic: str) -> Dict:
        topic = (topic or "").lower().strip()
        for key, info in _TOPICS.items():
            if key in topic or topic in key:
                return {"ok": True, "topic": key, **info, "disclaimer": DISCLAIMER}
        return {"ok": False, "error": f"No information found for '{topic}'.",
                "disclaimer": DISCLAIMER}

    def topics(self) -> List[str]:
        return list(_TOPICS.keys())

    # -- calculators --------------------------------------------------------
    def bmi(self, weight_kg: float, height_m: float) -> Dict:
        if height_m <= 0:
            return {"ok": False, "error": "Height must be positive."}
        value = weight_kg / (height_m ** 2)
        if value < 18.5:
            cat = "Underweight"
        elif value < 25:
            cat = "Normal"
        elif value < 30:
            cat = "Overweight"
        else:
            cat = "Obese"
        return {"ok": True, "bmi": round(value, 1), "category": cat,
                "disclaimer": DISCLAIMER}

    def bmr(self, weight_kg: float, height_cm: float, age: int,
            sex: str = "male") -> Dict:
        # Mifflin-St Jeor equation.
        base = 10 * weight_kg + 6.25 * height_cm - 5 * age
        bmr = base + (5 if sex.lower().startswith("m") else -161)
        return {"ok": True, "bmr": round(bmr, 1), "disclaimer": DISCLAIMER}

    def water_intake(self, weight_kg: float) -> Dict:
        litres = weight_kg * 0.033
        return {"ok": True, "litres_per_day": round(litres, 2),
                "disclaimer": DISCLAIMER}


_health: Optional[HealthAdvisor] = None


def get_health() -> HealthAdvisor:
    global _health
    if _health is None:
        _health = HealthAdvisor()
    return _health

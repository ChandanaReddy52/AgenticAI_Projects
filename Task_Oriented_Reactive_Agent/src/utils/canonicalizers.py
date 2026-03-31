# canonicalizers.py
# Define canonicalizers for standardizing input values
# the application layer canonicalizes LLM's intent values to enforce consistency with downstream data and schemas.”
# current canonicalize_specialty is fine for MVP correctness:
SPECIALTY_MAP = {
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
    "cardiologist": "Cardiology",
    "cardiology": "Cardiology",
    "neurologist": "Neurology",
    "neurology": "Neurology",
    "ent": "ENT",
    "orthopedic": "Orthopedics",
    "pediatrician": "Pediatrics",
    "gynecologist": "Gynecology",
    "general": "General Medicine"
}

from difflib import get_close_matches

# preventing fuzzy matching errors by limiting to known specialties
def canonicalize_specialty(value):
    if not value:
        return None

    value = value.lower()
    if value in SPECIALTY_MAP:
        return SPECIALTY_MAP[value]

    matches = get_close_matches(value, SPECIALTY_MAP.keys(), n=1, cutoff=0.75)
    if matches:
        return SPECIALTY_MAP[matches[0]]

    return None


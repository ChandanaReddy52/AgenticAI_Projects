#normalizers.py
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

def normalize_specialty(text: str):
    t = text.lower()
    for k, v in SPECIALTY_MAP.items():
        if k in t:
            return v
    return None

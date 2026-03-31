# schemas.py
from pydantic import BaseModel

class BookingRequest(BaseModel):
    doctor_id: str
    slot_id: str
    patient_name: str
    specialty: str